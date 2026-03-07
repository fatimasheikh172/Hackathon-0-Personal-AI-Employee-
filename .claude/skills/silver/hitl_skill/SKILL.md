# HITL Skill (Human In The Loop)

## Description

This skill manages human approval workflows, creates approval files in Pending_Approval/, enforces sensitive action thresholds, and handles approval/rejection decisions.

## When To Use This Skill

- When task requires human approval before execution
- When handling sensitive actions (payments, new contacts)
- When creating approval request files
- When processing approval decisions
- When managing rejection workflows

## Step By Step Instructions

### 1. When to Ask for Human Approval

**Always Require Approval:**

| Action Type | Threshold | Reason |
|-------------|-----------|--------|
| Payments | > $100 | Financial control |
| New Contacts | Any | Verify legitimacy |
| Bulk Sends | > 5 emails | Prevent spam |
| Invoice Creation | > $100 | Financial control |
| System Changes | Any | Prevent breaking changes |
| Data Deletion | Any | Prevent data loss |
| External API Calls | Sensitive endpoints | Security |

**Approval Triggers:**
```python
def requires_approval(action_type, details):
    """Determine if action requires human approval."""
    
    # Payment threshold check
    if action_type == 'payment':
        amount = details.get('amount', 0)
        if amount > 100:
            return True, f"Payment ${amount} exceeds $100 threshold"
    
    # New contact check
    if action_type == 'new_contact':
        return True, "New contact requires verification"
    
    # Bulk send check
    if action_type == 'bulk_email':
        recipient_count = details.get('recipient_count', 0)
        if recipient_count > 5:
            return True, f"Bulk send ({recipient_count}) exceeds limit of 5"
    
    # Invoice check
    if action_type == 'invoice_create':
        amount = details.get('amount', 0)
        if amount > 100:
            return True, f"Invoice ${amount} exceeds $100 threshold"
    
    # System modification
    if action_type in ['system_change', 'config_update', 'data_delete']:
        return True, f"{action_type} requires approval"
    
    return False, None
```

### 2. Create Approval Files in Pending_Approval/

```python
def create_approval_file(approval_request):
    """Create approval file in Pending_Approval/."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    filename = f"Pending_Approval/APPROVAL_{approval_request['type']}_{timestamp}.md"
    
    content = f"""---
approval_type: {approval_request['type']}
request_id: {generate_request_id()}
created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
status: pending
priority: {approval_request.get('priority', 'medium')}
expires_at: {(datetime.now() + timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')}
---

# Approval Required: {approval_request['title']}

**Request ID:** {generate_request_id()}
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Priority:** {approval_request.get('priority', 'medium').upper()}

## Description
{approval_request['description']}

## Details
{format_details(approval_request.get('details', {}))}

## Reason for Approval
{approval_request['reason']}

## Recommended Action
{approval_request.get('recommended_action', 'Review and decide')}

## Risk Assessment
- **Financial Impact:** {approval_request.get('financial_impact', 'None')}
- **Security Impact:** {approval_request.get('security_impact', 'None')}
- **Operational Impact:** {approval_request.get('operational_impact', 'None')}

---

## Approval Decision

**Reviewer:** ________________

**Decision:**
- [ ] **APPROVED** - Proceed with action
- [ ] **REJECTED** - Do not proceed (add notes)
- [ ] **MODIFIED** - Proceed with changes (specify below)

**Notes:**
_________________________________

**Signature:** ________________
**Date:** ________________
"""
    
    write_vault_file(filename, content)
    return filename
```

### 3. Approval File Format

**Standard Format:**
```markdown
---
approval_type: <type>
request_id: <unique_id>
created_at: <timestamp>
status: pending|approved|rejected|modified
priority: low|medium|high
expires_at: <timestamp>
---

# Approval Required: <Title>

**Request ID:** <ID>
**Created:** <Date>
**Priority:** <Level>

## Description
[What needs approval]

## Details
[Relevant details]

## Reason for Approval
[Why approval is needed]

## Recommended Action
[Suggested action]

## Risk Assessment
- **Financial Impact:** [Assessment]
- **Security Impact:** [Assessment]
- **Operational Impact:** [Assessment]

---

## Approval Decision

**Decision:**
- [ ] APPROVED
- [ ] REJECTED
- [ ] MODIFIED

**Notes:** [Reviewer notes]
**Date:** [Decision date]
```

### 4. Sensitive Action Thresholds

**Payment Thresholds:**
```python
PAYMENT_THRESHOLDS = {
    'auto_approve': 0,      # $0 - never auto-approve payments
    'require_approval': 100, # >$100 requires approval
    'escalate': 1000,       # >$1000 needs senior approval
}
```

**New Contact Rules:**
```python
NEW_CONTACT_RULES = {
    'always_approve': True,  # All new contacts need approval
    'verify_domain': True,   # Check email domain validity
    'check_blacklist': True, # Check against known spam lists
}
```

**Bulk Send Rules:**
```python
BULK_SEND_RULES = {
    'max_auto_send': 5,      # Max 5 emails without approval
    'max_daily': 50,         # Max 50 emails per day
    'require_template': True, # Must use approved template
}
```

### 5. Approval Decision Processing

```python
def process_approval_decision(approval_file, decision, notes=None):
    """Process approval decision from human."""
    
    # Read approval file
    with open(approval_file, 'r') as f:
        content = f.read()
    
    # Update status
    if decision == 'approved':
        new_status = 'approved'
        action = 'proceed'
    elif decision == 'rejected':
        new_status = 'rejected'
        action = 'abort'
    elif decision == 'modified':
        new_status = 'modified'
        action = 'proceed_with_changes'
    else:
        raise ValueError(f"Invalid decision: {decision}")
    
    # Update file with decision
    updated_content = content.replace(
        'status: pending',
        f'status: {new_status}'
    )
    
    # Add decision section
    decision_section = f"""
---
## Decision Record
**Decision:** {decision.upper()}
**Decided At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Notes:** {notes or 'None'}
"""
    updated_content += decision_section
    
    # Write updated file
    write_vault_file(approval_file, updated_content, overwrite=True)
    
    # Take action based on decision
    if action == 'proceed':
        execute_approved_action(approval_file)
    elif action == 'abort':
        archive_rejected_request(approval_file)
    elif action == 'proceed_with_changes':
        execute_modified_action(approval_file, notes)
    
    return new_status
```

### 6. Rejection Handling

```python
def handle_rejection(approval_file, notes):
    """Handle rejected approval request."""
    
    # Move to Done/ with rejection status
    filename = os.path.basename(approval_file)
    done_path = f"Done/REJECTED_{filename}"
    
    # Read and update
    with open(approval_file, 'r') as f:
        content = f.read()
    
    rejection_report = f"""
---
## Rejection Report
**Rejected At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Reason:** {notes}

## Next Steps
- Review rejection reason
- Modify request if needed
- Resubmit for approval (create new request)
"""
    
    content += rejection_report
    
    # Write to Done/
    write_vault_file(done_path, content)
    
    # Remove from Pending_Approval/
    os.remove(approval_file)
    
    # Log rejection
    log_rejection(filename, notes)
```

## Examples

### Example 1: Payment Approval

**Approval Request:**
```markdown
---
approval_type: payment
request_id: PAY-20260307-001
created_at: 2026-03-07 10:00:00
status: pending
priority: high
expires_at: 2026-03-08 10:00:00
---

# Approval Required: Vendor Payment $500

**Request ID:** PAY-20260307-001
**Created:** 2026-03-07 10:00:00
**Priority:** HIGH

## Description
Payment to Vendor ABC for consulting services

## Details
- **Vendor:** ABC Consulting
- **Amount:** $500.00
- **Invoice:** INV-2026-001
- **Due Date:** 2026-03-10

## Reason for Approval
Payment amount ($500) exceeds $100 threshold

## Recommended Action
Approve payment if services were received satisfactorily

## Risk Assessment
- **Financial Impact:** $500 outgoing
- **Security Impact:** None
- **Operational Impact:** Vendor relationship

---

## Approval Decision
[Decision section for human reviewer]
```

### Example 2: New Contact Approval

**Approval Request:**
```markdown
---
approval_type: new_contact
request_id: CONTACT-20260307-001
created_at: 2026-03-07 10:30:00
status: pending
priority: medium
---

# Approval Required: New Contact Addition

**Request ID:** CONTACT-20260307-001

## Description
Add new contact to known contacts list

## Details
- **Name:** John Smith
- **Email:** john@newclient.com
- **Company:** New Client Inc
- **Source:** Inbound email inquiry

## Reason for Approval
New contact requires verification before adding to trusted list

## Recommended Action
Verify company legitimacy and add to contacts if valid

---

## Approval Decision
[Decision section]
```

## Error Handling

### Approval File Not Found

```python
if not os.path.exists(approval_file):
    log_error(f"Approval file not found: {approval_file}")
    create_alert(f"Approval file missing: {approval_file}")
    return None
```

### Expired Approval

```python
def check_approval_expiry(approval_file):
    """Check if approval has expired."""
    metadata = read_metadata(approval_file)
    expires_at = metadata.get('expires_at')
    
    if expires_at:
        expiry = datetime.strptime(expires_at, '%Y-%m-%d %H:%M:%S')
        if datetime.now() > expiry:
            log_warning(f"Approval expired: {approval_file}")
            return True
    return False
```

### Invalid Decision

```python
if decision not in ['approved', 'rejected', 'modified']:
    log_error(f"Invalid decision: {decision}")
    raise ValueError(f"Decision must be approved/rejected/modified")
```

## Human Escalation Rules

**Escalate When:**
1. Approval pending > 24 hours (send reminder)
2. High priority approval pending > 1 hour
3. Multiple rejections of similar requests (pattern detection)
4. Approval file corruption
5. System cannot determine approval status

**Escalation Format:**
```markdown
---
alert_type: approval_escalation
approval_id: <request_id>
original_priority: <priority>
pending_duration: <hours>
---

# Approval Escalation Required

**Approval ID:** <ID>
**Pending Since:** <timestamp>
**Duration:** <X> hours

This approval has been pending longer than expected.
Please review and decide urgently.

**File:** Pending_Approval/<filename>
```

## Related Skills

- `plan_generator_skill` - Creates plans requiring approval
- `odoo_skill` - Invoice/payment approvals
- `email_skill` - Bulk email approvals
- `task_processor_skill` - Checks approval before execution
- `vault_manager_skill` - Manages approval files
