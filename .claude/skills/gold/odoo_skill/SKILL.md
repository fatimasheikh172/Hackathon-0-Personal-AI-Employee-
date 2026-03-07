# Odoo Skill

## Description

This skill connects to Odoo via MCP, creates DRAFT invoices only, checks financial summaries, creates customers, enforces HITL rules for payments > $100, never auto-posts invoices, and maintains audit logs.

## When To Use This Skill

- When creating invoices in Odoo
- When checking financial data
- When creating customer records
- When processing payments
- When requiring financial approval workflows

## Step By Step Instructions

### 1. Connect to Odoo via MCP

```python
# Odoo MCP Configuration
ODOO_CONFIG = {
    'url': 'https://your-company.odoo.com',
    'db': 'your_database',
    'username': 'api_user',
    'api_key': 'your_api_key',
    'timeout': 30,
}

def get_odoo_client():
    """Initialize Odoo MCP client."""
    return OdooMCPClient(config=ODOO_CONFIG)
```

**MCP Odoo Tools Available:**
- `odoo_invoice_create` - Create invoice in DRAFT status
- `odoo_invoice_read` - Read invoice details
- `odoo_customer_create` - Create new customer
- `odoo_customer_read` - Read customer details
- `odoo_financial_summary` - Get financial overview
- `odoo_payment_register` - Register payment (requires approval)

### 2. Create DRAFT Invoices Only

**CRITICAL RULE: Never create posted invoices directly**

```python
def create_odoo_invoice(invoice_details):
    """Create invoice in DRAFT status only."""
    
    # Validate invoice data
    validation_result = validate_invoice_data(invoice_details)
    if not validation_result['valid']:
        return {
            'success': False,
            'error': validation_result['error']
        }
    
    # ALWAYS create as draft
    invoice_data = {
        'move_type': 'out_invoice',
        'partner_id': invoice_details['customer_id'],
        'invoice_line_ids': invoice_details['line_items'],
        'state': 'draft',  # CRITICAL: Always draft
        'invoice_date': invoice_details.get('date', datetime.now().strftime('%Y-%m-%d')),
        'narration': invoice_details.get('notes', ''),
    }
    
    try:
        client = get_odoo_client()
        result = client.create_invoice(invoice_data)
        
        # Log creation
        log_invoice_creation(result['invoice_id'], invoice_details)
        
        return {
            'success': True,
            'invoice_id': result['invoice_id'],
            'name': result['invoice_name'],
            'state': 'draft',
            'message': 'Invoice created in DRAFT status - requires approval before posting'
        }
        
    except Exception as e:
        log_error(f"Odoo invoice creation failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
```

**Invoice Data Validation:**
```python
def validate_invoice_data(invoice_details):
    """Validate invoice data before creation."""
    errors = []
    
    # Required fields
    if not invoice_details.get('customer_id'):
        errors.append("Customer ID required")
    
    if not invoice_details.get('line_items'):
        errors.append("Line items required")
    
    # Validate amounts
    total = sum(item.get('price', 0) * item.get('quantity', 1) 
                for item in invoice_details.get('line_items', []))
    
    if total <= 0:
        errors.append("Total must be greater than 0")
    
    if total > 1000000:
        errors.append("Amount exceeds maximum limit")
    
    # Check for approval requirement
    if total > 100:
        invoice_details['requires_approval'] = True
    
    if errors:
        return {'valid': False, 'error': '; '.join(errors)}
    
    return {'valid': True}
```

### 3. Check Financial Summary

```python
def get_financial_summary():
    """Get financial summary from Odoo."""
    try:
        client = get_odoo_client()
        summary = client.get_financial_summary()
        
        return {
            'success': True,
            'data': {
                'total_receivable': summary.get('total_receivable', 0),
                'total_payable': summary.get('total_payable', 0),
                'outstanding_invoices': summary.get('outstanding_invoices', 0),
                'paid_invoices': summary.get('paid_invoices', 0),
                'draft_invoices': summary.get('draft_invoices', 0),
                'revenue_this_month': summary.get('revenue_this_month', 0),
                'revenue_this_year': summary.get('revenue_this_year', 0),
            }
        }
    except Exception as e:
        log_error(f"Financial summary fetch failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
```

**Financial Summary Format:**
```markdown
## Odoo Financial Summary
**Generated:** 2026-03-07 10:00:00

| Metric | Value |
|--------|-------|
| Total Receivable | $XX,XXX.XX |
| Total Payable | $XX,XXX.XX |
| Outstanding Invoices | XX |
| Draft Invoices | XX |
| Revenue (This Month) | $XX,XXX.XX |
| Revenue (This Year) | $XX,XXX.XX |
```

### 4. Create Customers

```python
def create_odoo_customer(customer_details):
    """Create new customer in Odoo."""
    
    # Validate customer data
    validation_result = validate_customer_data(customer_details)
    if not validation_result['valid']:
        return {
            'success': False,
            'error': validation_result['error']
        }
    
    customer_data = {
        'name': customer_details['name'],
        'email': customer_details.get('email', ''),
        'phone': customer_details.get('phone', ''),
        'company': customer_details.get('company', ''),
        'street': customer_details.get('street', ''),
        'city': customer_details.get('city', ''),
        'country_id': customer_details.get('country_id'),
        'customer_rank': 1,  # Mark as customer
    }
    
    try:
        client = get_odoo_client()
        result = client.create_customer(customer_data)
        
        log_customer_creation(result['customer_id'], customer_details)
        
        return {
            'success': True,
            'customer_id': result['customer_id'],
            'message': 'Customer created - requires approval before use'
        }
        
    except Exception as e:
        log_error(f"Odoo customer creation failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
```

**Customer Validation:**
```python
def validate_customer_data(customer_details):
    """Validate customer data."""
    errors = []
    
    if not customer_details.get('name'):
        errors.append("Customer name required")
    
    # Check for existing customer (prevent duplicates)
    if customer_details.get('email'):
        existing = find_customer_by_email(customer_details['email'])
        if existing:
            return {
                'valid': False,
                'error': f"Customer already exists: {existing['id']}"
            }
    
    if errors:
        return {'valid': False, 'error': '; '.join(errors)}
    
    return {'valid': True}
```

### 5. HITL Rules: Payments > $100 Need Approval

```python
def check_payment_approval(invoice_details):
    """Check if payment requires human approval."""
    total = calculate_invoice_total(invoice_details)
    
    if total > 100:
        return {
            'requires_approval': True,
            'reason': f'Invoice amount ${total} exceeds $100 threshold',
            'threshold': 100
        }
    
    return {
        'requires_approval': False,
        'reason': None
    }
```

**Approval Workflow:**
```python
def process_invoice_with_approval(invoice_details):
    """Process invoice with approval check."""
    
    # Create draft invoice
    result = create_odoo_invoice(invoice_details)
    if not result['success']:
        return result
    
    # Check if approval needed
    approval_check = check_payment_approval(invoice_details)
    
    if approval_check['requires_approval']:
        # Create approval request
        approval_file = create_approval_file({
            'type': 'invoice_post',
            'invoice_id': result['invoice_id'],
            'amount': calculate_invoice_total(invoice_details),
            'reason': approval_check['reason']
        })
        
        return {
            'success': True,
            'invoice_id': result['invoice_id'],
            'state': 'draft_pending_approval',
            'approval_file': approval_file,
            'message': 'Invoice created - awaiting approval to post'
        }
    
    return result
```

### 6. Never Auto-Post Invoices

**CRITICAL RULE:**
```python
# NEVER DO THIS:
# client.post_invoice(invoice_id)  # ❌ WRONG

# ALWAYS leave in draft and require human to post:
# Invoice stays in draft until human reviews and posts manually  # ✅ CORRECT
```

**Post Invoice Function (Human Only):**
```python
def request_invoice_post(invoice_id):
    """Request human to post invoice - DO NOT POST AUTOMATICALLY."""
    
    # Create notification for human
    notification = f"""
Invoice {invoice_id} is ready for posting.

**IMPORTANT:** This invoice is in DRAFT status.
A human must review and post it manually.

To post:
1. Open Odoo
2. Navigate to Invoices
3. Find invoice {invoice_id}
4. Review line items and amounts
5. Click 'Post' to confirm
"""
    
    log_notification(notification)
    return {'message': 'Posting request sent to human'}
```

### 7. Audit Logging Rules

```python
def log_invoice_creation(invoice_id, invoice_details):
    """Log invoice creation for audit trail."""
    log_entry = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'action': 'invoice_create',
        'invoice_id': invoice_id,
        'customer_id': invoice_details.get('customer_id'),
        'amount': calculate_invoice_total(invoice_details),
        'status': 'draft',
        'user': 'ai_employee',
        'requires_approval': invoice_details.get('requires_approval', False),
    }
    
    # Append to audit log
    append_to_audit_log(log_entry)
    
    # Also create markdown record
    create_audit_record(log_entry)
```

**Audit Log Format:**
```markdown
---
audit_type: invoice_creation
invoice_id: INV-2026-001
created_at: 2026-03-07 10:00:00
---

# Audit Record: Invoice Creation

**Invoice ID:** INV-2026-001
**Customer:** Customer Name
**Amount:** $500.00
**Status:** Draft
**Created By:** AI Employee
**Requires Approval:** Yes
**Approval Status:** Pending

## Line Items
| Description | Quantity | Price | Total |
|-------------|----------|-------|-------|
| Service A | 1 | $500 | $500 |

## Timeline
- 2026-03-07 10:00:00 - Invoice created in draft
- 2026-03-07 10:00:00 - Approval request created
- Pending human approval
```

## Examples

### Example 1: Create Invoice Under $100

**Input:**
```python
invoice_details = {
    'customer_id': 123,
    'line_items': [
        {'name': 'Consulting', 'quantity': 1, 'price': 75}
    ],
    'notes': 'Monthly consulting'
}
```

**Result:**
```python
{
    'success': True,
    'invoice_id': 'INV-2026-001',
    'state': 'draft',
    'message': 'Invoice created in DRAFT status'
}
```

### Example 2: Create Invoice Over $100 (Requires Approval)

**Input:**
```python
invoice_details = {
    'customer_id': 456,
    'line_items': [
        {'name': 'Project Work', 'quantity': 1, 'price': 500}
    ],
    'notes': 'Project completion'
}
```

**Result:**
```python
{
    'success': True,
    'invoice_id': 'INV-2026-002',
    'state': 'draft_pending_approval',
    'approval_file': 'Pending_Approval/APPROVAL_invoice_post_20260307_100000.md',
    'message': 'Invoice created - awaiting approval to post'
}
```

## Error Handling

### Odoo Connection Error

```python
try:
    client = get_odoo_client()
except OdooConnectionError as e:
    log_error(f"Odoo connection failed: {e}")
    create_alert("Odoo connection unavailable - financial operations paused")
    return {'success': False, 'error': 'Odoo unavailable'}
```

### Validation Error

```python
if not validation_result['valid']:
    log_warning(f"Invoice validation failed: {validation_result['error']}")
    return {
        'success': False,
        'error': validation_result['error'],
        'action': 'fix_and_resubmit'
    }
```

### Duplicate Customer

```python
if existing:
    log_info(f"Customer already exists: {existing['id']}")
    return {
        'success': False,
        'error': 'Customer exists',
        'existing_id': existing['id'],
        'action': 'use_existing'
    }
```

## Human Escalation Rules

**Always Escalate:**
1. All invoices > $100 (for posting approval)
2. All new customer creations (for verification)
3. Invoice creation failures (for manual review)
4. Duplicate detection conflicts
5. Financial summary anomalies (large discrepancies)
6. Payment registration requests

**Escalation Format:**
```markdown
---
approval_type: odoo_invoice_post
invoice_id: INV-2026-001
amount: 500
timestamp: 2026-03-07 10:00:00
---

# Invoice Posting Approval Required

**Invoice:** INV-2026-001
**Amount:** $500.00
**Customer:** Client Name

This invoice is in DRAFT status. Please review and post manually in Odoo.

**Reason for Approval:** Amount exceeds $100 threshold
```

## Related Skills

- `hitl_skill` - For approval workflows
- `ceo_briefing_skill` - Uses financial summary
- `accounting_audit_skill` - Audits financial data
- `error_recovery_skill` - Handles Odoo errors
