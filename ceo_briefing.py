#!/usr/bin/env python3
"""
CEO Briefing Generator - Creates Monday Morning Executive Briefings
Analyzes business data from Odoo and generates comprehensive CEO briefing
Gold Tier - Integrated with Odoo ERP for real financial data
"""

import os
import sys
import re
import json
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
BRIEFINGS_FOLDER = VAULT_PATH / "Briefings"
DONE_FOLDER = VAULT_PATH / "Done"
PLANS_FOLDER = VAULT_PATH / "Plans"
PENDING_APPROVAL_FOLDER = VAULT_PATH / "Pending_Approval"
LOGS_FOLDER = VAULT_PATH / "Logs"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
BUSINESS_GOALS_FILE = VAULT_PATH / "Business_Goals.md"
BANK_TRANSACTIONS_FILE = VAULT_PATH / "Accounting" / "Bank_Transactions.md"

# Briefing statistics
briefing_stats = {
    "last_generated": None,
    "total_generated": 0,
    "last_revenue": 0,
    "last_expenses": 0,
    "last_profit": 0
}


def get_log_file_path():
    """Get JSON log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"ceo_briefing_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"ceo_briefing_activity_{date_str}.txt"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, BRIEFINGS_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True):
    """Log a CEO briefing action to log files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Text log entry
    status = "[OK]" if success else "[ERROR]"
    log_entry = f"[{timestamp}] {status} {action_type}: {details}\n"

    try:
        with open(get_text_log_file_path(), "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"ERROR writing text log: {e}")

    # JSON log entry
    json_entry = {
        "timestamp": timestamp,
        "type": action_type,
        "details": details,
        "success": success
    }

    try:
        log_data = load_json_log()
        log_data["actions"].append(json_entry)
        save_json_log(log_data)
    except Exception as e:
        print(f"ERROR writing JSON log: {e}")

    # Print to console
    print(f"[{timestamp}] {status} {action_type}: {details}")


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
            "total_briefings": 0
        }
    }


def save_json_log(log_data):
    """Save log data to JSON file"""
    try:
        log_data["summary"]["total_briefings"] = briefing_stats["total_generated"]

        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR saving JSON log: {e}")
        return False


def get_odoo_financial_data():
    """
    Get real financial data from Odoo ERP
    
    Returns:
        dict: Financial summary from Odoo or fallback data
    """
    print("\n[Odoo Integration] Fetching real financial data...")
    
    try:
        # Import Odoo MCP functions
        from odoo_mcp_server import get_financial_summary, get_invoices, get_odoo_stats
        
        # Get financial summary
        fin_result = get_financial_summary()
        
        if fin_result.get("success"):
            summary = fin_result.get("summary", {})
            print(f"  Revenue (Odoo): ${summary.get('revenue', 0):.2f}")
            print(f"  Expenses (Odoo): ${summary.get('expenses', 0):.2f}")
            print(f"  Profit (Odoo): ${summary.get('profit', 0):.2f}")
            
            return {
                "source": "odoo",
                "revenue": summary.get("revenue", 0),
                "expenses": summary.get("expenses", 0),
                "profit": summary.get("profit", 0),
                "currency": summary.get("currency", "USD")
            }
        else:
            print(f"  [WARN] Odoo financial summary failed: {fin_result.get('error', 'Unknown error')}")
            
    except ImportError as e:
        print(f"  [WARN] Could not import odoo_mcp_server: {e}")
    except Exception as e:
        print(f"  [WARN] Odoo integration error: {e}")
    
    # Fallback to local data
    print("  [INFO] Using local Bank_Transactions.md as fallback")
    return None


def get_odoo_pending_invoices():
    """
    Get pending (draft) invoices from Odoo
    
    Returns:
        list: List of pending invoices or empty list
    """
    print("\n[Odoo Integration] Fetching pending invoices...")
    
    try:
        from odoo_mcp_server import get_invoices
        
        result = get_invoices(status="draft", limit=10)
        
        if result.get("success"):
            invoices = result.get("invoices", [])
            print(f"  Found {len(invoices)} pending invoices")
            return invoices
        else:
            print(f"  [WARN] Failed to get pending invoices: {result.get('error', 'Unknown error')}")
            
    except Exception as e:
        print(f"  [WARN] Odoo pending invoices error: {e}")
    
    return []


def parse_yaml_frontmatter(content):
    """Extract YAML frontmatter from markdown content"""
    frontmatter = {}

    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if match:
        yaml_content = match.group(1)
        for line in yaml_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                value = value.strip().strip('"').strip("'")
                frontmatter[key.strip()] = value

    return frontmatter


def parse_business_goals():
    """Parse Business_Goals.md and extract targets"""
    goals = {
        "monthly_revenue_goal": 10000,
        "current_mtd": 4500,
        "metrics": {},
        "projects": [],
        "subscription_rules": []
    }

    if not BUSINESS_GOALS_FILE.exists():
        log_action("goals_warning", "Business_Goals.md not found, using defaults")
        return goals

    try:
        with open(BUSINESS_GOALS_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract revenue goal
        goal_match = re.search(r'Monthly goal:.*?\$?([\d,]+)', content)
        if goal_match:
            goals["monthly_revenue_goal"] = float(goal_match.group(1).replace(",", ""))

        # Extract MTD
        mtd_match = re.search(r'Current MTD:.*?\$?([\d,]+)', content)
        if mtd_match:
            goals["current_mtd"] = float(mtd_match.group(1).replace(",", ""))

        # Extract projects
        project_matches = re.findall(r'(\d+)\. (Project \w+) - Due ([\w\s]+) - Budget \$?([\d,]+)', content)
        for match in project_matches:
            goals["projects"].append({
                "name": match[1],
                "due": match[2],
                "budget": float(match[3].replace(",", ""))
            })

        log_action("goals_parsed", f"Loaded {len(goals['projects'])} projects")

    except Exception as e:
        log_action("goals_error", f"Failed to parse Business_Goals.md: {e}", success=False)

    return goals


def parse_bank_transactions():
    """Parse Bank_Transactions.md and extract transactions (fallback)"""
    transactions = {
        "income": [],
        "expenses": [],
        "subscriptions": [],
        "total_income": 0,
        "total_expenses": 0
    }

    if not BANK_TRANSACTIONS_FILE.exists():
        log_action("transactions_warning", "Bank_Transactions.md not found")
        return transactions

    try:
        with open(BANK_TRANSACTIONS_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        # Find table rows
        table_match = re.search(r'\| Date.*?\n\|[-| ]+\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
        if not table_match:
            return transactions

        table_content = table_match.group(1)

        # Parse each row
        for line in table_content.strip().split("\n"):
            if not line.strip() or not line.startswith("|"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 6:
                continue

            date_str = parts[1]
            description = parts[2]
            amount_str = parts[3]
            trans_type = parts[4].lower() if len(parts) > 4 else ""
            category = parts[5].lower() if len(parts) > 5 else ""

            # Parse amount
            amount_str = amount_str.replace("$", "").replace(",", "")
            if amount_str.startswith("+"):
                amount = float(amount_str[1:])
            elif amount_str.startswith("-"):
                amount = -float(amount_str[1:])
            else:
                amount = float(amount_str)

            transaction = {
                "date": date_str,
                "description": description,
                "amount": abs(amount),
                "type": trans_type,
                "category": category
            }

            if trans_type == "income" or amount > 0:
                transactions["income"].append(transaction)
                transactions["total_income"] += abs(amount)
            else:
                transactions["expenses"].append(transaction)
                transactions["total_expenses"] += abs(amount)

                if category == "subscription":
                    transactions["subscriptions"].append(transaction)

        log_action("transactions_parsed",
                   f"Income: ${transactions['total_income']:.2f}, "
                   f"Expenses: ${transactions['total_expenses']:.2f}")

    except Exception as e:
        log_action("transactions_error", f"Failed to parse Bank_Transactions.md: {e}", success=False)

    return transactions


def count_completed_tasks():
    """Count completed tasks from Done folder"""
    if not DONE_FOLDER.exists():
        return 0, []

    # Count files modified in last 7 days
    now = datetime.now()
    week_ago = now - timedelta(days=7)

    completed = []
    for file_path in DONE_FOLDER.glob("*.md"):
        try:
            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            if mtime >= week_ago:
                completed.append({
                    "name": file_path.name,
                    "date": mtime.strftime("%Y-%m-%d")
                })
        except Exception:
            continue

    return len(completed), completed


def find_bottlenecks():
    """Find high priority pending plans"""
    bottlenecks = []

    if not PLANS_FOLDER.exists():
        return bottlenecks

    for plan_file in PLANS_FOLDER.glob("*.md"):
        try:
            with open(plan_file, "r", encoding="utf-8") as f:
                content = f.read()

            frontmatter = parse_yaml_frontmatter(content)
            priority = frontmatter.get("priority", "").lower()

            if priority == "high":
                bottlenecks.append({
                    "name": plan_file.name,
                    "priority": priority,
                    "title": frontmatter.get("title", plan_file.name)
                })
        except Exception:
            continue

    return bottlenecks


def count_pending_approvals():
    """Count pending approval files"""
    if not PENDING_APPROVAL_FOLDER.exists():
        return 0
    return len(list(PENDING_APPROVAL_FOLDER.glob("*.md")))


def generate_executive_summary(revenue, expenses, tasks_completed, bottlenecks, goals):
    """Generate one paragraph executive summary"""
    net = revenue - expenses
    goal_pct = (revenue / goals["monthly_revenue_goal"] * 100) if goals["monthly_revenue_goal"] > 0 else 0

    summary_parts = []

    # Revenue status
    if net > 0:
        summary_parts.append(f"This week showed positive momentum with ${net:.2f} net profit")
    else:
        summary_parts.append(f"This week had ${abs(net):.2f} net loss")

    # Goal progress
    summary_parts.append(f"reaching {goal_pct:.1f}% of monthly revenue goal")

    # Tasks
    if tasks_completed > 0:
        summary_parts.append(f"with {tasks_completed} tasks completed")

    # Bottlenecks warning
    if bottlenecks:
        summary_parts.append(f"however, {len(bottlenecks)} high-priority items remain pending")

    return ". ".join(summary_parts) + "."


def generate_income_sources(transactions, odoo_invoices):
    """Generate income sources list"""
    lines = []
    
    # Show Odoo invoices if available
    if odoo_invoices:
        lines.append("**From Odoo ERP:**")
        for inv in odoo_invoices[:5]:
            lines.append(f"- {inv.get('customer', 'Unknown')}: ${inv.get('amount', 0):.2f} ({inv.get('status', 'draft')})")
        lines.append("")
    
    # Show local transactions
    if transactions["income"]:
        lines.append("**From Local Records:**")
        for tx in sorted(transactions["income"], key=lambda x: x["amount"], reverse=True)[:5]:
            lines.append(f"- {tx['description']}: ${tx['amount']:.2f}")
    
    if not lines:
        return "- No income recorded this period"

    return "\n".join(lines)


def generate_expense_breakdown(transactions):
    """Generate expense breakdown by category"""
    if not transactions["expenses"]:
        return "- No expenses recorded this period"

    # Group by category
    by_category = {}
    for tx in transactions["expenses"]:
        cat = tx["category"] or "other"
        if cat not in by_category:
            by_category[cat] = 0
        by_category[cat] += tx["amount"]

    lines = []
    for cat, total in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
        lines.append(f"- {cat.title()}: ${total:.2f}")

    return "\n".join(lines)


def generate_subscription_audit(transactions):
    """Generate subscription audit with flags"""
    if not transactions["subscriptions"]:
        return "- No subscriptions found"

    lines = []
    total_subs = 0

    for sub in transactions["subscriptions"]:
        amount = sub["amount"]
        total_subs += amount
        flag = ""

        # Flag expensive subscriptions
        if amount > 50:
            flag = " ⚠️ HIGH COST"
        elif amount > 20:
            flag = " ⚠️ REVIEW"

        lines.append(f"- {sub['description']}: ${amount:.2f}{flag}")

    lines.append(f"\n**Total Subscriptions: ${total_subs:.2f}/month**")

    # Add suggestion if total is high
    if total_subs > 100:
        lines.append("\n💡 **Suggestion**: Review subscriptions for potential savings")

    return "\n".join(lines)


def generate_proactive_suggestions(revenue, expenses, bottlenecks, goals):
    """Generate 3-5 actionable suggestions"""
    suggestions = []

    # Subscription suggestion
    if expenses > revenue * 0.5:
        suggestions.append(f"💸 **Expense Watch**: Expenses are ${expenses:.2f} ({expenses/max(1,revenue)*100:.1f}% of revenue) - review for optimization")

    # Bottleneck suggestion
    if bottlenecks:
        suggestions.append(f"⚠️ **Priority Alert**: {len(bottlenecks)} high-priority tasks need immediate attention")

    # Revenue suggestion
    goal_pct = (revenue / goals["monthly_revenue_goal"] * 100) if goals["monthly_revenue_goal"] > 0 else 0
    if goal_pct < 50:
        remaining = goals["monthly_revenue_goal"] - revenue
        suggestions.append(f"📈 **Revenue Focus**: ${remaining:.2f} remaining to reach monthly goal")

    # Default suggestion
    if len(suggestions) < 3:
        suggestions.append("📋 **Weekly Review**: Schedule time to review pending approvals and upcoming deadlines")

    return "\n".join(suggestions[:5])


def generate_next_week_priorities(goals, bottlenecks):
    """Generate top 3 priorities for next week"""
    priorities = []

    # Add bottlenecks as priorities
    for bottleneck in bottlenecks[:2]:
        priorities.append(f"1. Complete: {bottleneck['title']}")

    # Add revenue focus
    priorities.append(f"2. Revenue Focus: Work towards ${goals['monthly_revenue_goal']:.2f} monthly goal")

    # Add review task
    priorities.append("3. Weekly Review: Process pending approvals and update project status")

    return "\n".join(priorities[:3])


def generate_odoo_accounting_section(odoo_data, pending_invoices):
    """Generate Odoo Accounting Summary section"""
    if not odoo_data or odoo_data.get("source") != "odoo":
        return """## Odoo Accounting Summary

*Odoo integration not available - showing local data only*
"""
    
    lines = ["""## Odoo Accounting Summary

**Data Source:** Odoo ERP (Live)
"""]
    
    lines.append(f"| Metric | Amount |")
    lines.append(f"|--------|--------|")
    lines.append(f"| Revenue | ${odoo_data.get('revenue', 0):.2f} |")
    lines.append(f"| Expenses | ${odoo_data.get('expenses', 0):.2f} |")
    lines.append(f"| Net Profit | ${odoo_data.get('profit', 0):.2f} |")
    lines.append(f"| Currency | {odoo_data.get('currency', 'USD')} |")
    lines.append("")
    
    if pending_invoices:
        lines.append("**Pending Invoices:**")
        for inv in pending_invoices[:5]:
            lines.append(f"- {inv.get('number', 'N/A')}: {inv.get('customer', 'Unknown')} - ${inv.get('amount', 0):.2f} ({inv.get('status', 'draft')})")
    else:
        lines.append("**Pending Invoices:** None")
    
    return "\n".join(lines)


def generate_ceo_briefing():
    """Generate the complete CEO briefing with Odoo integration"""
    print("\n" + "=" * 60)
    print("CEO BRIEFING GENERATOR (Gold Tier - Odoo Integrated)")
    print("=" * 60)

    # Get Odoo financial data
    print("\n[1/8] Fetching Odoo Financial Data...")
    odoo_data = get_odoo_financial_data()
    
    # Get pending invoices from Odoo
    print("[2/8] Fetching Pending Invoices from Odoo...")
    pending_invoices = get_odoo_pending_invoices()
    
    # Parse local data as fallback/supplement
    print("[3/8] Loading Business Goals...")
    goals = parse_business_goals()

    print("[4/8] Parsing Bank Transactions (fallback)...")
    transactions = parse_bank_transactions()
    
    # Use Odoo data if available, otherwise use local
    if odoo_data and odoo_data.get("source") == "odoo":
        revenue = odoo_data.get("revenue", 0)
        expenses = odoo_data.get("expenses", 0)
    else:
        revenue = transactions.get("total_income", 0)
        expenses = transactions.get("total_expenses", 0)

    print("[5/8] Counting Completed Tasks...")
    tasks_count, tasks_list = count_completed_tasks()

    print("[6/8] Finding Bottlenecks...")
    bottlenecks = find_bottlenecks()

    print("[7/8] Counting Pending Approvals...")
    pending_count = count_pending_approvals()

    # Calculate metrics
    net_profit = revenue - expenses
    goal_percentage = (revenue / goals["monthly_revenue_goal"] * 100) if goals["monthly_revenue_goal"] > 0 else 0

    print("[8/8] Generating Briefing Content...")

    # Generate briefing
    today = datetime.now()
    briefing_date = today.strftime("%Y-%m-%d")
    briefing_filename = f"CEO_BRIEFING_{briefing_date}.md"
    briefing_path = BRIEFINGS_FOLDER / briefing_filename

    # Generate all sections
    executive_summary = generate_executive_summary(revenue, expenses, tasks_count, bottlenecks, goals)
    income_sources = generate_income_sources(transactions, pending_invoices)
    expense_breakdown = generate_expense_breakdown(transactions)
    subscription_audit = generate_subscription_audit(transactions)
    proactive_suggestions = generate_proactive_suggestions(revenue, expenses, bottlenecks, goals)
    next_week_priorities = generate_next_week_priorities(goals, bottlenecks)
    odoo_section = generate_odoo_accounting_section(odoo_data, pending_invoices)

    # Tasks completed section
    if tasks_list:
        tasks_completed_section = f"- Total Completed: {tasks_count}\n\n"
        for task in tasks_list[:5]:
            tasks_completed_section += f"- [{task['date']}] {task['name']}\n"
    else:
        tasks_completed_section = "- Total Completed: 0\n\n- No tasks completed this week"

    # Bottlenecks section
    if bottlenecks:
        bottlenecks_section = ""
        for b in bottlenecks:
            bottlenecks_section += f"- ⚠️ HIGH PRIORITY: {b['name']}\n"
    else:
        bottlenecks_section = "- No critical bottlenecks identified"

    briefing_content = f"""# Monday Morning CEO Briefing - {today.strftime("%B %d, %Y")}

Generated: {today.strftime("%Y-%m-%d %H:%M:%S")}

---

## Executive Summary

{executive_summary}

---

{odoo_section}

---

## Revenue This Week

- **Total Income**: ${revenue:.2f}
- **Total Expenses**: ${expenses:.2f}
- **Net Profit**: ${net_profit:.2f}
- **Progress to Monthly Goal**: {goal_percentage:.1f}%

---

## Top Income Sources

{income_sources}

---

## Expense Breakdown

{expense_breakdown}

---

## Subscription Audit

{subscription_audit}

---

## Tasks Completed This Week

{tasks_completed_section}

---

## Bottlenecks

{bottlenecks_section}

---

## Proactive Suggestions

{proactive_suggestions}

---

## Next Week Priorities

{next_week_priorities}

---

## Quick Stats

| Metric | Value |
|--------|-------|
| Pending Approvals | {pending_count} |
| Subscriptions | ${sum(s["amount"] for s in transactions["subscriptions"]):.2f}/mo |
| High Priority Tasks | {len(bottlenecks)} |
| Weekly Revenue | ${revenue:.2f} |
| Data Source | {odoo_data.get('source', 'local') if odoo_data else 'local'} |

---

*Generated by AI Employee v2.0 (Gold Tier) - {today.strftime("%Y-%m-%d %H:%M:%S")}*
*Odoo ERP Integration: {"Enabled" if odoo_data and odoo_data.get("source") == "odoo" else "Fallback Mode"}*
"""

    # Write briefing file
    BRIEFINGS_FOLDER.mkdir(parents=True, exist_ok=True)
    with open(briefing_path, "w", encoding="utf-8") as f:
        f.write(briefing_content)

    print(f"\n[Briefing saved to: {briefing_path}]")

    # Update stats
    briefing_stats["last_generated"] = today.strftime("%Y-%m-%d %H:%M:%S")
    briefing_stats["total_generated"] += 1
    briefing_stats["last_revenue"] = revenue
    briefing_stats["last_expenses"] = expenses
    briefing_stats["last_profit"] = net_profit

    # Log success
    log_action("briefing_generated", f"Created {briefing_filename} - Revenue: ${revenue:.2f}, Profit: ${net_profit:.2f}")

    # Update dashboard
    update_dashboard()

    # Print summary
    print("\n" + "=" * 60)
    print("BRIEFING GENERATED SUCCESSFULLY")
    print("=" * 60)
    print(f"\nFile: {briefing_filename}")
    print(f"Revenue: ${revenue:.2f}")
    print(f"Expenses: ${expenses:.2f}")
    print(f"Net Profit: ${net_profit:.2f}")
    print(f"Goal Progress: {goal_percentage:.1f}%")
    print(f"Tasks Completed: {tasks_count}")
    print(f"Bottlenecks: {len(bottlenecks)}")
    print(f"Data Source: {odoo_data.get('source', 'local') if odoo_data else 'local'}")
    print("=" * 60)

    return briefing_path


def update_dashboard():
    """Update Dashboard.md with CEO briefing status"""
    try:
        if not DASHBOARD_FILE.exists():
            return False

        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        briefing_section = f"""## CEO Briefing Status
- Last Briefing Generated: {briefing_stats['last_generated'] or 'Never'}
- Next Scheduled Briefing: Monday 8:00 AM
- Total Briefings Generated: {briefing_stats['total_generated']}
- Last Revenue Reported: ${briefing_stats['last_revenue']:.2f}
"""

        if "## CEO Briefing Status" in content:
            pattern = r"## CEO Briefing Status.*?(?=## |\Z)"
            content = re.sub(pattern, briefing_section, content, flags=re.DOTALL)
        else:
            if "---" in content:
                parts = content.rsplit("---", 1)
                content = parts[0] + briefing_section + "\n---" + parts[1] if len(parts) > 1 else content + "\n" + briefing_section
            else:
                content = content + "\n" + briefing_section

        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(content)

        return True
    except Exception as e:
        log_action("dashboard_error", f"Failed to update dashboard: {e}", success=False)
        return False


def main():
    """Main function - generate CEO briefing"""
    print("=" * 60)
    print("CEO Briefing Generator - AI Employee System (Gold Tier)")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Briefings Folder: {BRIEFINGS_FOLDER}")
    print("=" * 60)

    # Ensure folders exist
    ensure_folders_exist()

    try:
        # Generate briefing
        briefing_path = generate_ceo_briefing()

        print("\n[OK] CEO Briefing generation complete!")
        print(f"\nView briefing: {briefing_path}")

        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to generate briefing: {e}")
        log_action("generation_error", str(e), success=False)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nBriefing generation stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
