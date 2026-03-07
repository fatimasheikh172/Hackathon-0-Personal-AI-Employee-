# Plan Generator Skill

## Description

This skill creates structured Plan.md files with checkbox-based task lists, step-by-step planning, and approval request generation. It breaks down complex tasks into actionable steps.

## When To Use This Skill

- When starting a new complex task
- When breaking down large projects into steps
- When creating task checklists
- When planning requires human approval
- When documenting task execution strategy

## Step By Step Instructions

### 1. Create Plan.md Files

```python
def create_plan(task_name, task_details, steps=None):
    """Create a structured Plan.md file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    plan_file = f"Drafts/PLAN_{task_name.replace(' ', '_')}_{timestamp}.md"
    
    # Generate steps if not provided
    if not steps:
        steps = generate_steps(task_details)
    
    plan_content = f"""---
plan_type: task_execution
task_name: {task_name}
created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
status: draft
total_steps: {len(steps)}
estimated_duration: {estimate_duration(steps)}
---

# Plan: {task_name}

**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Status:** Draft - Pending Review

## Objective
{task_details.get('objective', 'Complete the task successfully')}

## Steps

"""
    
    # Add checkbox steps
    for i, step in enumerate(steps, 1):
        plan_content += f"- [ ] Step {i}: {step['name']}\n"
        if step.get('details'):
            plan_content += f"  - {step['details']}\n"
        if step.get('requires_approval'):
            plan_content += f"  - ⚠️ **Requires Approval**\n"
        if step.get('estimated_time'):
            plan_content += f"  - ⏱️ ~{step['estimated_time']}\n"
        plan_content += "\n"
    
    plan_content += """
## Notes
- Complete steps in order
- Mark each step as done before proceeding
- Escalate any issues immediately

## Approval
"""
    
    if any(s.get('requires_approval') for s in steps):
        plan_content += "- [ ] Human approval required before execution\n"
    else:
        plan_content += "- [ ] Self-approved - can proceed\n"
    
    write_vault_file(plan_file, plan_content)
    return plan_file
```

### 2. Checkbox Format Rules

**Format Standard:**
```markdown
- [ ] Step N: Step name
  - Additional details (optional)
  - ⚠️ Requires approval (if applicable)
  - ⏱️ Time estimate (if applicable)
```

**Checkbox States:**
- `- [ ]` = Not started
- `- [x]` = Completed
- `- [-]` = In progress
- `[~]` = Blocked/Waiting

**Step Structure:**
```python
step = {
    'name': 'Clear, action-oriented step name',
    'details': 'Optional additional context',
    'requires_approval': False,  # Set True if HITL needed
    'estimated_time': '5 minutes',  # Time estimate
    'dependencies': [],  # Other step numbers this depends on
    'outputs': []  # Files/artifacts this step produces
}
```

### 3. Step by Step Planning

**Planning Algorithm:**
```python
def generate_steps(task_details):
    """Generate step-by-step plan from task details."""
    steps = []
    
    # Standard workflow steps
    steps.append({
        'name': 'Review task requirements',
        'details': 'Understand what needs to be done',
        'estimated_time': '5 minutes'
    })
    
    # Add task-specific steps based on type
    task_type = task_details.get('type', 'general')
    
    if task_type == 'email_campaign':
        steps.extend([
            {'name': 'Draft email content', 'estimated_time': '15 minutes'},
            {'name': 'Review recipient list', 'estimated_time': '5 minutes'},
            {'name': 'Submit for approval', 'requires_approval': True, 'estimated_time': 'N/A'},
            {'name': 'Send emails', 'estimated_time': '10 minutes'},
            {'name': 'Log results', 'estimated_time': '5 minutes'}
        ])
    
    elif task_type == 'invoice_creation':
        steps.extend([
            {'name': 'Gather invoice details', 'estimated_time': '10 minutes'},
            {'name': 'Create draft invoice in Odoo', 'estimated_time': '5 minutes'},
            {'name': 'Review invoice amounts', 'estimated_time': '5 minutes'},
            {'name': 'Submit for approval', 'requires_approval': True, 'estimated_time': 'N/A'},
            {'name': 'Send invoice to client', 'estimated_time': '5 minutes'}
        ])
    
    elif task_type == 'social_media_post':
        steps.extend([
            {'name': 'Generate post content', 'estimated_time': '10 minutes'},
            {'name': 'Review tone and length', 'estimated_time': '5 minutes'},
            {'name': 'Submit for approval', 'requires_approval': True, 'estimated_time': 'N/A'},
            {'name': 'Schedule/post content', 'estimated_time': '5 minutes'}
        ])
    
    else:
        # Generic steps
        steps.extend([
            {'name': 'Execute task', 'estimated_time': '30 minutes'},
            {'name': 'Review results', 'estimated_time': '10 minutes'},
            {'name': 'Document completion', 'estimated_time': '5 minutes'}
        ])
    
    # Always end with completion step
    steps.append({
        'name': 'Mark task complete and archive',
        'details': 'Move files to Done/, update Dashboard',
        'estimated_time': '5 minutes'
    })
    
    return steps
```

**Duration Estimation:**
```python
def estimate_duration(steps):
    """Estimate total duration from steps."""
    total_minutes = 0
    
    for step in steps:
        time_str = step.get('estimated_time', '0 minutes')
        if isinstance(time_str, str):
            try:
                minutes = int(time_str.split()[0])
                total_minutes += minutes
            except (ValueError, IndexError):
                pass  # Skip non-numeric estimates
    
    if total_minutes < 60:
        return f"{total_minutes} minutes"
    else:
        hours = total_minutes / 60
        return f"{hours:.1f} hours"
```

### 4. Approval Request Creation

```python
def create_approval_request(plan_file, reason):
    """Create approval request for plan."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    approval_file = f"Pending_Approval/PLAN_APPROVAL_{timestamp}.md"
    
    # Read plan content
    with open(plan_file, 'r') as f:
        plan_content = f.read()
    
    approval_content = f"""---
approval_type: plan_review
plan_file: {plan_file}
reason: {reason}
created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
status: pending_approval
---

# Plan Approval Required

**Plan:** {os.path.basename(plan_file)}
**Reason:** {reason}

## Plan Summary
{plan_content[:500]}...

## Steps Requiring Approval
"""
    
    # Extract steps needing approval
    for line in plan_content.split('\n'):
        if 'Requires Approval' in line:
            approval_content += f"\n{line.strip()}"
    
    approval_content += """

## Approval Decision
- [ ] **Approve** - Plan is approved, proceed with execution
- [ ] **Reject** - Plan needs revision (add notes below)
- [ ] **Modify** - Approve with changes (specify below)

## Reviewer Notes
[Add notes here if needed]

---
**Reviewer:** ________________
**Date:** ________________
**Decision:** ________________
"""
    
    write_vault_file(approval_file, approval_content)
    return approval_file
```

## Examples

### Example 1: Email Campaign Plan

**Input:**
```python
task_details = {
    'type': 'email_campaign',
    'objective': 'Send product announcement to 50 clients',
    'details': 'New AI Employee launch announcement'
}
```

**Generated Plan:**
```markdown
---
plan_type: task_execution
task_name: Email Campaign - Product Launch
created_at: 2026-03-07 10:00:00
status: draft
total_steps: 7
estimated_duration: 45 minutes
---

# Plan: Email Campaign - Product Launch

**Created:** 2026-03-07 10:00:00
**Status:** Draft - Pending Review

## Objective
Send product announcement to 50 clients

## Steps

- [ ] Step 1: Review task requirements
  - Understand what needs to be done
  - ⏱️ ~5 minutes

- [ ] Step 2: Draft email content
  - ⏱️ ~15 minutes

- [ ] Step 3: Review recipient list
  - ⏱️ ~5 minutes

- [ ] Step 4: Submit for approval
  - ⚠️ **Requires Approval**
  - ⏱️ ~N/A

- [ ] Step 5: Send emails
  - ⏱️ ~10 minutes

- [ ] Step 6: Log results
  - ⏱️ ~5 minutes

- [ ] Step 7: Mark task complete and archive
  - Move files to Done/, update Dashboard
  - ⏱️ ~5 minutes

## Notes
- Complete steps in order
- Mark each step as done before proceeding
- Escalate any issues immediately

## Approval
- [ ] Human approval required before execution
```

### Example 2: Invoice Creation Plan

**Generated Plan:**
```markdown
---
plan_type: task_execution
task_name: Create Invoice for Client ABC
created_at: 2026-03-07 10:30:00
status: draft
total_steps: 7
estimated_duration: 30 minutes
---

# Plan: Create Invoice for Client ABC

## Objective
Create and send invoice for consulting services

## Steps

- [ ] Step 1: Review task requirements
  - ⏱️ ~5 minutes

- [ ] Step 2: Gather invoice details
  - Client info, services, amounts
  - ⏱️ ~10 minutes

- [ ] Step 3: Create draft invoice in Odoo
  - Use odoo_skill to create DRAFT invoice
  - ⏱️ ~5 minutes

- [ ] Step 4: Review invoice amounts
  - Verify accuracy before approval
  - ⏱️ ~5 minutes

- [ ] Step 5: Submit for approval
  - Amount > $100 requires human approval
  - ⚠️ **Requires Approval**
  - ⏱️ ~N/A

- [ ] Step 6: Send invoice to client
  - After approval, send via email
  - ⏱️ ~5 minutes

- [ ] Step 7: Mark task complete and archive
  - ⏱️ ~5 minutes

## Approval
- [ ] Human approval required before execution
```

## Error Handling

### Step Generation Failure

```python
try:
    steps = generate_steps(task_details)
except Exception as e:
    log_error(f"Step generation failed: {e}")
    # Use minimal fallback steps
    steps = [
        {'name': 'Review task', 'estimated_time': '10 minutes'},
        {'name': 'Execute task', 'estimated_time': '30 minutes'},
        {'name': 'Complete and document', 'estimated_time': '10 minutes'}
    ]
```

### Invalid Plan Format

```python
def validate_plan(plan_content):
    """Validate plan has required elements."""
    required = ['plan_type', 'task_name', 'Steps']
    issues = []
    
    for req in required:
        if req not in plan_content:
            issues.append(f"Missing: {req}")
    
    # Check for at least one checkbox
    if '- [ ]' not in plan_content:
        issues.append("No checkbox steps found")
    
    return len(issues) == 0, issues
```

## Human Escalation Rules

**Always Create Approval Request:**
1. Plans with steps affecting finances (invoices, payments)
2. Plans involving external communications (emails, social posts)
3. Plans that modify system configuration
4. Plans with potential data deletion
5. Plans affecting multiple departments
6. Any plan where total estimated duration > 2 hours

**Approval Request Format:**
```markdown
---
approval_type: plan_review
plan_file: Drafts/PLAN_example.md
reason: Financial impact - invoice creation
timestamp: 2026-03-07 10:00:00
---

# Plan Approval Required

**Plan:** Create Invoice for Client ABC
**Reason:** Invoice amount exceeds $100 threshold

Please review and approve before execution.
```

## Related Skills

- `hitl_skill` - For approval workflows
- `task_processor_skill` - Executes planned tasks
- `odoo_skill` - For invoice-related plans
- `mcp_email_skill` - For email-related plans
