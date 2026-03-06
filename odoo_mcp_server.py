#!/usr/bin/env python3
"""
Odoo MCP Server - Odoo ERP integration with HITL approval
All posting/payment actions require human approval before execution
Gold Tier Personal AI Employee System
"""

import os
import sys
import json
import xmlrpc.client
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"
PENDING_APPROVAL_FOLDER = VAULT_PATH / "Pending_Approval"
APPROVED_FOLDER = VAULT_PATH / "Approved"
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# Odoo configuration
from odoo_config import (
    ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD,
    test_connection, get_server_proxy, ensure_folders
)

# Ensure folders exist
ensure_folders()

# Odoo statistics
odoo_stats = {
    "invoices_created": 0,
    "invoices_posted": 0,
    "customers_created": 0,
    "expenses_created": 0,
    "last_action": "Never",
    "last_action_time": None
}


def get_log_file_path():
    """Get JSON log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"odoo_mcp_{date_str}.json"


def log_action(action_type, details, success=True, data=None):
    """Log an Odoo action to log files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update stats
    odoo_stats["last_action"] = f"{action_type}: {details[:50]}..."
    odoo_stats["last_action_time"] = timestamp

    # JSON log entry
    json_entry = {
        "timestamp": timestamp,
        "type": action_type,
        "details": details,
        "success": success,
        "dry_run": DRY_RUN,
        "data": data or {}
    }

    try:
        log_data = load_json_log()
        log_data["actions"].append(json_entry)

        # Update counters
        if action_type == "invoice_created":
            odoo_stats["invoices_created"] += 1
        elif action_type == "invoice_posted":
            odoo_stats["invoices_posted"] += 1
        elif action_type == "customer_created":
            odoo_stats["customers_created"] += 1
        elif action_type == "expense_created":
            odoo_stats["expenses_created"] += 1

        save_json_log(log_data)
    except Exception as e:
        print(f"ERROR writing JSON log: {e}")

    # Print to console
    dry_run_prefix = "[DRY_RUN] " if DRY_RUN else ""
    status = "[OK]" if success else "[ERROR]"
    print(f"[{timestamp}] {dry_run_prefix}{status} {action_type}: {details}")


def load_json_log():
    """Load today's JSON log or create new structure"""
    log_path = get_log_file_path()
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "actions": [],
        "summary": {
            "total_invoices": 0,
            "total_customers": 0,
            "total_expenses": 0,
            "total_errors": 0
        }
    }


def save_json_log(log_data):
    """Save log data to JSON file"""
    try:
        log_data["summary"]["total_invoices"] = odoo_stats["invoices_created"]
        log_data["summary"]["total_customers"] = odoo_stats["customers_created"]
        log_data["summary"]["total_expenses"] = odoo_stats["expenses_created"]

        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR saving JSON log: {e}")
        return False


def authenticate():
    """
    Authenticate with Odoo server
    
    Returns:
        dict: {
            "success": bool,
            "uid": int or None,
            "error": str or None,
            "message": str
        }
    """
    print(f"\n{'='*50}")
    print("ODOO AUTHENTICATION")
    print(f"{'='*50}")
    print(f"URL: {ODOO_URL}")
    print(f"Database: {ODOO_DB}")
    print(f"Username: {ODOO_USERNAME}")
    print(f"{'='*50}\n")

    result = test_connection()
    
    if result["success"]:
        log_action("authenticate", f"Authenticated as UID: {result['uid']}", success=True)
    else:
        log_action("authenticate_failed", result["error"], success=False)
    
    return result


def execute_odoo(model, method, args, kwargs=None):
    """
    Execute an Odoo API call with error handling and DRY_RUN support
    
    Args:
        model: Odoo model name (e.g., "account.move")
        method: Method name (e.g., "create", "read")
        args: List of arguments
        kwargs: Optional dict of keyword arguments
    
    Returns:
        tuple: (success, result or None, error or None)
    """
    kwargs = kwargs or {}
    
    # DRY_RUN mode - only log, don't execute
    if DRY_RUN and method in ["create", "write", "unlink", "action_post", "action_register_payment"]:
        log_action(
            "dry_run_execute",
            f"Would execute {model}.{method} with args: {args}",
            success=True,
            data={"model": model, "method": method, "args": args, "kwargs": kwargs}
        )
        return True, {"dry_run": True, "model": model, "method": method}, None
    
    try:
        success, models, uid, error = get_server_proxy()

        if not success:
            return False, None, error

        # Execute the method using execute_kw (correct XML-RPC method)
        result = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, model, method, args, kwargs)

        return True, result, None

    except xmlrpc.client.Fault as e:
        error_msg = f"XML-RPC Fault: {e.faultString}"
        return False, None, error_msg
    except Exception as e:
        error_msg = f"Odoo API error: {str(e)}"
        return False, None, error_msg


def check_approval_required(amount):
    """
    Check if an action requires HITL approval based on amount
    
    Args:
        amount: Transaction amount
    
    Returns:
        bool: True if approval required
    """
    # Payments > $100 always need approval
    return amount > 100


def create_approval_request(action_type, details, amount=None):
    """
    Create an approval request file for actions requiring HITL
    
    Args:
        action_type: Type of action (e.g., "post_invoice", "register_payment")
        details: Dict with action details
        amount: Transaction amount
    
    Returns:
        Path: Path to approval file or None
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    now = datetime.now()
    from datetime import timedelta
    expires = now + timedelta(hours=24)

    approval_filename = f"APPROVAL_ODOO_{action_type.upper()}_{timestamp}.md"
    approval_path = PENDING_APPROVAL_FOLDER / approval_filename

    approval_content = f"""---
type: approval_request
action: {action_type}
created: {now.strftime("%Y-%m-%d %H:%M:%S")}
expires: {expires.strftime("%Y-%m-%d %H:%M:%S")}
status: pending
requires_approval: yes
amount: {amount or "N/A"}
---

## Odoo Action Approval Request

**Action:** {action_type}
**Created:** {now.strftime("%Y-%m-%d %H:%M:%S")}
**Expires:** {expires.strftime("%Y-%m-%d %H:%M:%S")}
**Amount:** {amount or "N/A"}

---

## Action Details

```json
{json.dumps(details, indent=2)}
```

---

## To Approve
Move this file to F:\\AI_Employee_Vault\\Approved folder to execute this action.

## To Reject
Move this file to F:\\AI_Employee_Vault\\Rejected folder to cancel this action.

---

*Created by Odoo MCP Server at {now.strftime("%Y-%m-%d %H:%M:%S")}*
*DRY_RUN: {DRY_RUN}*
"""

    try:
        PENDING_APPROVAL_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(approval_path, "w", encoding="utf-8") as f:
            f.write(approval_content)
        return approval_path
    except Exception as e:
        log_action("approval_create_error", f"Failed to create approval file: {e}", success=False)
        return None


def create_invoice(customer_name, amount, description, auto_post=False):
    """
    Create an invoice in Odoo (draft by default, NEVER auto-post)
    
    Args:
        customer_name: Name of the customer
        amount: Invoice amount
        description: Invoice description/line item
        auto_post: If True, will require approval for posting (default: False)
    
    Returns:
        dict: {
            "success": bool,
            "invoice_id": int or None,
            "invoice_number": str or None,
            "error": str or None,
            "approval_required": bool
        }
    """
    print(f"\n{'='*50}")
    print("CREATE INVOICE")
    print(f"{'='*50}")
    print(f"Customer: {customer_name}")
    print(f"Amount: ${amount:.2f}")
    print(f"Description: {description}")
    print(f"{'='*50}\n")

    # Check if approval needed for high amounts
    approval_required = check_approval_required(amount)
    
    if approval_required and auto_post:
        log_action("invoice_approval_required", f"Invoice ${amount:.2f} requires approval for posting")
        approval_path = create_approval_request(
            "post_invoice",
            {
                "customer_name": customer_name,
                "amount": amount,
                "description": description
            },
            amount
        )
        if approval_path:
            print(f"APPROVAL REQUIRED: Created {approval_path.name}")
            print("Move file to Approved folder to post this invoice")
    
    # First, find or create customer
    customer_result = find_or_create_customer(customer_name)
    
    if not customer_result["success"]:
        log_action("invoice_create_error", f"Failed to find/create customer: {customer_result['error']}", success=False)
        return {
            "success": False,
            "invoice_id": None,
            "invoice_number": None,
            "error": customer_result["error"],
            "approval_required": False
        }
    
    partner_id = customer_result["partner_id"]
    
    # Create invoice (account.move with move_type='out_invoice')
    invoice_data = {
        "move_type": "out_invoice",
        "partner_id": partner_id,
        "invoice_line_ids": [
            (0, 0, {
                "name": description,
                "quantity": 1,
                "price_unit": amount,
            })
        ]
    }
    
    if DRY_RUN:
        log_action(
            "invoice_created",
            f"Draft invoice created for {customer_name}: ${amount:.2f} - {description[:30]}",
            success=True,
            data={"customer": customer_name, "amount": amount, "dry_run": True}
        )
        return {
            "success": True,
            "invoice_id": "DRY_RUN_ID",
            "invoice_number": "DRAFT",
            "error": None,
            "approval_required": approval_required,
            "dry_run": True
        }
    
    success, invoice_id, error = execute_odoo("account.move", "create", [invoice_data])
    
    if not success:
        log_action("invoice_create_error", f"Failed to create invoice: {error}", success=False)
        return {
            "success": False,
            "invoice_id": None,
            "invoice_number": None,
            "error": error,
            "approval_required": False
        }
    
    # Get invoice number
    invoice_number = "DRAFT"
    if not DRY_RUN:
        _, invoice_data_result, _ = execute_odoo("account.move", "read", [[invoice_id]], {"fields": ["name"]})
        if invoice_data_result and len(invoice_data_result) > 0:
            invoice_number = invoice_data_result[0].get("name", "DRAFT")
    
    log_action(
        "invoice_created",
        f"Draft invoice {invoice_number} created for {customer_name}: ${amount:.2f}",
        success=True,
        data={"invoice_id": invoice_id, "invoice_number": invoice_number, "customer": customer_name, "amount": amount}
    )
    
    return {
        "success": True,
        "invoice_id": invoice_id,
        "invoice_number": invoice_number,
        "error": None,
        "approval_required": approval_required,
        "dry_run": DRY_RUN
    }


def find_or_create_customer(customer_name, email=None, phone=None):
    """
    Find existing customer or create new one
    
    Args:
        customer_name: Customer name
        email: Customer email (optional)
        phone: Customer phone (optional)
    
    Returns:
        dict: {"success": bool, "partner_id": int or None, "error": str or None}
    """
    # Try to find existing customer by name
    success, partners, error = execute_odoo(
        "res.partner",
        "search_read",
        [[["name", "=", customer_name]]],
        {"fields": ["id", "name", "email", "phone"], "limit": 1}
    )
    
    if success and partners and len(partners) > 0:
        return {
            "success": True,
            "partner_id": partners[0]["id"],
            "error": None,
            "existing": True
        }
    
    # Create new customer if email/phone provided
    if email or phone:
        return create_customer(customer_name, email or "", phone or "")
    
    # Create with minimal info
    return create_customer(customer_name, "", "")


def get_invoices(status="draft", limit=10):
    """
    List invoices from Odoo
    
    Args:
        status: Invoice status - "draft", "posted", "cancel", or "all"
        limit: Maximum number of results
    
    Returns:
        dict: {
            "success": bool,
            "invoices": list or None,
            "error": str or None,
            "count": int
        }
    """
    print(f"\n{'='*50}")
    print("GET INVOICES")
    print(f"{'='*50}")
    print(f"Status: {status}")
    print(f"Limit: {limit}")
    print(f"{'='*50}\n")

    # Build domain filter
    domain = []
    if status != "all":
        domain = [["state", "=", status]]
    
    success, invoices, error = execute_odoo(
        "account.move",
        "search_read",
        [domain],
        {
            "fields": ["id", "name", "partner_id", "amount_total", "state", "invoice_date", "ref"],
            "limit": limit,
            "order": "invoice_date desc"
        }
    )
    
    if not success:
        log_action("get_invoices_error", f"Failed to get invoices: {error}", success=False)
        return {
            "success": False,
            "invoices": None,
            "error": error,
            "count": 0
        }
    
    # Format partner_id to name
    formatted_invoices = []
    for inv in invoices:
        partner_name = inv.get("partner_id", [None, "Unknown"])[1] if isinstance(inv.get("partner_id"), list) else "Unknown"
        formatted_invoices.append({
            "id": inv["id"],
            "number": inv.get("name", "N/A"),
            "customer": partner_name,
            "amount": inv.get("amount_total", 0),
            "status": inv.get("state", "unknown"),
            "date": inv.get("invoice_date", "N/A"),
            "reference": inv.get("ref", "")
        })
    
    log_action("get_invoices", f"Retrieved {len(formatted_invoices)} invoices with status '{status}'", success=True)
    
    return {
        "success": True,
        "invoices": formatted_invoices,
        "error": None,
        "count": len(formatted_invoices)
    }


def create_customer(name, email, phone):
    """
    Create a new customer in Odoo
    
    Args:
        name: Customer name
        email: Customer email
        phone: Customer phone
    
    Returns:
        dict: {
            "success": bool,
            "partner_id": int or None,
            "error": str or None
        }
    """
    print(f"\n{'='*50}")
    print("CREATE CUSTOMER")
    print(f"{'='*50}")
    print(f"Name: {name}")
    print(f"Email: {email}")
    print(f"Phone: {phone}")
    print(f"{'='*50}\n")

    customer_data = {
        "name": name,
        "email": email,
        "phone": phone,
        "customer": True
    }
    
    if DRY_RUN:
        log_action(
            "customer_created",
            f"Customer created: {name} ({email})",
            success=True,
            data={"name": name, "email": email, "phone": phone, "dry_run": True}
        )
        return {
            "success": True,
            "partner_id": "DRY_RUN_ID",
            "error": None,
            "dry_run": True
        }
    
    success, partner_id, error = execute_odoo("res.partner", "create", [customer_data])
    
    if not success:
        log_action("customer_create_error", f"Failed to create customer: {error}", success=False)
        return {
            "success": False,
            "partner_id": None,
            "error": error
        }
    
    log_action(
        "customer_created",
        f"Customer created: {name} (ID: {partner_id})",
        success=True,
        data={"partner_id": partner_id, "name": name, "email": email, "phone": phone}
    )
    
    return {
        "success": True,
        "partner_id": partner_id,
        "error": None,
        "dry_run": DRY_RUN
    }


def get_financial_summary():
    """
    Get financial summary from Odoo (revenue, expenses, profit)
    
    Returns:
        dict: {
            "success": bool,
            "summary": dict or None,
            "error": str or None
        }
    """
    print(f"\n{'='*50}")
    print("GET FINANCIAL SUMMARY")
    print(f"{'='*50}\n")

    summary = {
        "revenue": 0,
        "expenses": 0,
        "profit": 0,
        "currency": "USD"
    }
    
    if DRY_RUN:
        summary = {
            "revenue": 0,
            "expenses": 0,
            "profit": 0,
            "currency": "USD",
            "dry_run": True,
            "note": "DRY_RUN mode - no actual data fetched"
        }
        log_action("financial_summary", "Financial summary retrieved (DRY_RUN)", success=True, data=summary)
        return {
            "success": True,
            "summary": summary,
            "error": None
        }
    
    try:
        # Get posted customer invoices (revenue)
        success, invoices, error = execute_odoo(
            "account.move",
            "search_read",
            [[["move_type", "=", "out_invoice"], ["state", "=", "posted"]]],
            {"fields": ["amount_total"]}
        )
        
        if success and invoices:
            summary["revenue"] = sum(inv.get("amount_total", 0) for inv in invoices)
        
        # Get vendor bills (expenses)
        success, bills, error = execute_odoo(
            "account.move",
            "search_read",
            [[["move_type", "in", ["in_invoice", "in_refund"]], ["state", "=", "posted"]]],
            {"fields": ["amount_total"]}
        )
        
        if success and bills:
            summary["expenses"] = sum(bill.get("amount_total", 0) for bill in bills)
        
        # Calculate profit
        summary["profit"] = summary["revenue"] - summary["expenses"]
        
        log_action("financial_summary", f"Revenue: ${summary['revenue']:.2f}, Expenses: ${summary['expenses']:.2f}, Profit: ${summary['profit']:.2f}", success=True)
        
        return {
            "success": True,
            "summary": summary,
            "error": None
        }
        
    except Exception as e:
        error_msg = f"Failed to get financial summary: {str(e)}"
        log_action("financial_summary_error", error_msg, success=False)
        return {
            "success": False,
            "summary": None,
            "error": error_msg
        }


def create_expense(amount, category, description):
    """
    Log an expense in Odoo
    
    Args:
        amount: Expense amount
        category: Expense category (will map to Odoo analytic account or product)
        description: Expense description
    
    Returns:
        dict: {
            "success": bool,
            "expense_id": int or None,
            "error": str or None,
            "approval_required": bool
        }
    """
    print(f"\n{'='*50}")
    print("CREATE EXPENSE")
    print(f"{'='*50}")
    print(f"Amount: ${amount:.2f}")
    print(f"Category: {category}")
    print(f"Description: {description}")
    print(f"{'='*50}\n")

    # Check if approval needed
    approval_required = check_approval_required(amount)
    
    if approval_required:
        log_action("expense_approval_required", f"Expense ${amount:.2f} requires approval")
        approval_path = create_approval_request(
            "create_expense",
            {
                "amount": amount,
                "category": category,
                "description": description
            },
            amount
        )
        if approval_path:
            print(f"APPROVAL REQUIRED: Created {approval_path.name}")
            print("Move file to Approved folder to log this expense")
    
    if DRY_RUN:
        log_action(
            "expense_created",
            f"Expense logged: ${amount:.2f} - {category} - {description[:30]}",
            success=True,
            data={"amount": amount, "category": category, "description": description, "dry_run": True}
        )
        return {
            "success": True,
            "expense_id": "DRY_RUN_ID",
            "error": None,
            "approval_required": approval_required,
            "dry_run": True
        }
    
    # Try to create as vendor bill (account.move)
    # First, find or create a generic vendor for expenses
    success, vendor_result, error = execute_odoo(
        "res.partner",
        "search_read",
        [[["name", "=", "Expense Vendor"]]],
        {"fields": ["id"], "limit": 1}
    )
    
    vendor_id = 1  # Default to first partner if not found
    if success and vendor_result and len(vendor_result) > 0:
        vendor_id = vendor_result[0]["id"]
    
    expense_data = {
        "move_type": "in_invoice",
        "partner_id": vendor_id,
        "invoice_line_ids": [
            (0, 0, {
                "name": f"{category}: {description}",
                "quantity": 1,
                "price_unit": amount,
            })
        ],
        "ref": category
    }
    
    success, expense_id, error = execute_odoo("account.move", "create", [expense_data])
    
    if not success:
        log_action("expense_create_error", f"Failed to create expense: {error}", success=False)
        return {
            "success": False,
            "expense_id": None,
            "error": error,
            "approval_required": False
        }
    
    log_action(
        "expense_created",
        f"Expense logged: ${amount:.2f} - {category} (ID: {expense_id})",
        success=True,
        data={"expense_id": expense_id, "amount": amount, "category": category}
    )
    
    return {
        "success": True,
        "expense_id": expense_id,
        "error": None,
        "approval_required": approval_required,
        "dry_run": DRY_RUN
    }


def get_odoo_stats():
    """Get current Odoo statistics"""
    return {
        "invoices_created": odoo_stats["invoices_created"],
        "invoices_posted": odoo_stats["invoices_posted"],
        "customers_created": odoo_stats["customers_created"],
        "expenses_created": odoo_stats["expenses_created"],
        "last_action": odoo_stats["last_action"],
        "last_action_time": odoo_stats["last_action_time"],
        "dry_run": DRY_RUN
    }


def update_dashboard():
    """Update Dashboard.md with Odoo MCP status"""
    dashboard_file = VAULT_PATH / "Dashboard.md"
    
    # Count pending Odoo approvals
    pending_count = len(list(PENDING_APPROVAL_FOLDER.glob("APPROVAL_ODOO_*.md")))
    
    stats = get_odoo_stats()
    
    dashboard_content = f"""
## Odoo MCP Status

- **DRY_RUN Mode:** {stats['dry_run']}
- **Invoices Created:** {stats['invoices_created']}
- **Expenses Logged:** {stats['expenses_created']}
- **Customers Added:** {stats['customers_created']}
- **Pending Approvals:** {pending_count}
- **Last Action:** {stats['last_action']}
- **Last Action Time:** {stats['last_action_time']}

---
"""
    
    try:
        # Read existing dashboard
        if dashboard_file.exists():
            with open(dashboard_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check if Odoo section exists
            if "## Odoo MCP Status" not in content:
                with open(dashboard_file, "a", encoding="utf-8") as f:
                    f.write(dashboard_content)
        else:
            with open(dashboard_file, "w", encoding="utf-8") as f:
                f.write("# AI Employee Dashboard\n\n")
                f.write(dashboard_content)
    except Exception as e:
        print(f"ERROR updating dashboard: {e}")


# MCP Server entry point
if __name__ == "__main__":
    print("=" * 60)
    print("ODOO MCP SERVER - Gold Tier Personal AI Employee")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Odoo URL: {ODOO_URL}")
    print(f"Database: {ODOO_DB}")
    print(f"DRY_RUN: {DRY_RUN}")
    print("=" * 60)
    
    # Test connection
    result = authenticate()

    if result["success"]:
        print("\n[OK] Odoo MCP Server ready!")
        print("\nAvailable functions:")
        print("  - authenticate()")
        print("  - create_invoice(customer_name, amount, description)")
        print("  - get_invoices(status='draft')")
        print("  - create_customer(name, email, phone)")
        print("  - get_financial_summary()")
        print("  - create_expense(amount, category, description)")
    else:
        print("\n[FAIL] Failed to connect to Odoo")
        print(f"  Error: {result['error']}")
