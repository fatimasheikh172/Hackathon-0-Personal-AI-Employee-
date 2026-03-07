# Task Processor Skill

## Description

This skill processes files in the `Needs_Action/` folder, executes the required actions, moves completed files to `Done/`, and maintains basic logging. It is the core execution engine of the AI Employee system.

## When To Use This Skill

- When processing pending tasks in Needs_Action/
- When executing automated workflows
- When archiving completed tasks to Done/
- When logging task execution results

## Step By Step Instructions

### 1. Scan Needs_Action Folder

```python
import os
import glob
from datetime import datetime

NEEDS_ACTION = "F:/AI_Employee_Vault/Needs_Action"
DONE = "F:/AI_Employee_Vault/Done"

def get_pending_tasks():
    """Get all pending action files."""
    pattern = os.path.join(NEEDS_ACTION, "ACTION_*.md")
    return sorted(glob.glob(pattern))
```

**Processing Order:**
1. High priority tasks first (check metadata)
2. Then by creation timestamp (oldest first)
3. Process maximum 10 tasks per batch (prevent overload)

### 2. Read and Parse Action File

```python
import yaml

def parse_action_file(filepath):
    """Parse action file and extract metadata."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract YAML front matter
    if content.startswith('---'):
        parts = content.split('---', 2)
        metadata = yaml.safe_load(parts[1])
        body = parts[2].strip() if len(parts) > 2 else ""
    else:
        metadata = {}
        body = content
    
    return metadata, body
```

**Expected Metadata:**
```yaml
action_type: email_reply
source_file: Inbox/email_request.md
created_at: 2026-03-07 09:30:00
priority: high
status: pending
```

### 3. Execute Task Based on Action Type

```python
def execute_task(filepath):
    """Execute task based on action_type."""
    metadata, body = parse_action_file(filepath)
    action_type = metadata.get('action_type', 'unknown')
    
    if action_type == 'email_reply':
        result = process_email_reply(body, metadata)
    elif action_type == 'social_media':
        result = process_social_media(body, metadata)
    elif action_type == 'invoice_create':
        result = process_invoice(body, metadata)
    elif action_type == 'task_process':
        result = process_general_task(body, metadata)
    else:
        result = {'success': False, 'error': f'Unknown action type: {action_type}'}
    
    return result
```

### 4. Task Completion Rules

**Before Marking Complete:**
1. Verify all checkboxes in task are completed
2. Ensure output files are created in correct location
3. Log completion with timestamp
4. Update Dashboard.md

**Completion Checklist:**
- [ ] Task executed successfully
- [ ] Output files created
- [ ] Logs updated
- [ ] Dashboard updated
- [ ] Source file referenced in completion report

### 5. Move File to Done/

```python
import shutil

def archive_task(filepath, result):
    """Move completed task to Done/ folder."""
    filename = os.path.basename(filepath)
    
    # Create completion report
    done_path = os.path.join(DONE, filename)
    
    # Read original content
    with open(filepath, 'r', encoding='utf-8') as f:
        original_content = f.read()
    
    # Append completion info
    completion_report = f"""
{original_content}

---
## Completion Report

**Completed At:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Result:** {'SUCCESS' if result.get('success') else 'FAILED'}
**Notes:** {result.get('notes', 'None')}
**Output Files:** {result.get('output_files', [])}
"""
    
    # Write to Done/
    with open(done_path, 'w', encoding='utf-8') as f:
        f.write(completion_report)
    
    # Remove from Needs_Action/
    os.remove(filepath)
    
    log_completion(filename, result)
```

### 6. Basic Logging

```python
import logging

# Configure logging
logging.basicConfig(
    filename='F:/AI_Employee_Vault/Logs/task_processor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_task_start(filepath):
    logging.info(f"Starting task: {os.path.basename(filepath)}")

def log_task_complete(filepath, result):
    status = 'SUCCESS' if result.get('success') else 'FAILED'
    logging.info(f"Task {os.path.basename(filepath)}: {status}")

def log_error(filepath, error):
    logging.error(f"Task {os.path.basename(filepath)} failed: {error}")
```

## Examples

### Example 1: Processing Email Reply Task

**Input File:**
```
Needs_Action/ACTION_email_request_20260307_093000.md

---
action_type: email_reply
source_file: Inbox/email_request.md
created_at: 2026-03-07 09:30:00
priority: high
status: pending
---

# Action Required: Email Reply

**Original Subject:** Urgent: Invoice needed

**Content:**
Please send invoice ASAP for project completion.
```

**Processing:**
```python
result = {
    'success': True,
    'notes': 'Draft email created, awaiting approval',
    'output_files': ['Drafts/email_draft_20260307_093500.md'],
    'requires_approval': True
}
archive_task(filepath, result)
```

**Output in Done/:**
```
Done/ACTION_email_request_20260307_093000.md

[Original content...]

---
## Completion Report

**Completed At:** 2026-03-07 09:35:00
**Result:** SUCCESS
**Notes:** Draft email created, awaiting approval
**Output Files:** ['Drafts/email_draft_20260307_093500.md']
```

### Example 2: Processing Social Media Task

**Input File:**
```
Needs_Action/ACTION_social_media_20260307_100000.md

---
action_type: social_media
source_file: Inbox/post_request.md
created_at: 2026-03-07 10:00:00
priority: medium
status: pending
---

# Action Required: LinkedIn Post

**Topic:** New product launch
**Platform:** LinkedIn
```

**Processing:**
```python
# Generate post using linkedin_skill
post_content = generate_linkedin_post("New product launch")

result = {
    'success': True,
    'notes': 'Post generated, submitted for approval',
    'output_files': ['Pending_Approval/linkedin_post_20260307_100500.md']
}
```

## Error Handling

### Unknown Action Type

```python
if action_type not in KNOWN_TYPES:
    result = {
        'success': False,
        'error': f'Unknown action type: {action_type}',
        'notes': 'Requires manual review'
    }
    # Move to Quarantine for human review
    move_to_quarantine(filepath)
```

### Task Execution Failure

```python
try:
    result = execute_action(action_type, body)
except Exception as e:
    result = {
        'success': False,
        'error': str(e),
        'notes': 'Task execution failed'
    }
    log_error(filepath, e)
    
    # Retry logic (max 3 attempts)
    if retry_count < 3:
        schedule_retry(filepath)
    else:
        create_alert(filepath, e)
```

### Missing Source File

```python
source_file = metadata.get('source_file')
if source_file and not os.path.exists(source_file):
    result = {
        'success': False,
        'error': f'Source file missing: {source_file}',
        'notes': 'Cannot process without source'
    }
    log_error(filepath, "Source file missing")
```

## Human Escalation Rules

**Escalate to Human When:**
1. Unknown action type encountered
2. Task fails after 3 retry attempts
3. Source file is missing or corrupted
4. Task requires approval (see hitl_skill)
5. Payment/invoice tasks over $100
6. New contact creation requests

**Escalation Process:**
1. Create file in `Pending_Approval/` with details
2. Update Dashboard.md with pending count
3. Log escalation in task completion report
4. Do NOT move original file to Done/ until approved

**Escalation File Format:**
```markdown
---
approval_type: task_review
task_file: ACTION_email_request_20260307_093000.md
reason: Unknown action type
timestamp: 2026-03-07 09:35:00
---

# Approval Required

**Task:** ACTION_email_request_20260307_093000.md
**Issue:** Unknown action type: custom_action
**Recommended Action:** Review and categorize manually
**Priority:** Medium
```

## Related Skills

- `file_watcher_skill` - Creates action files in Needs_Action/
- `vault_manager_skill` - Manages file operations
- `hitl_skill` - For approval workflows
- `email_skill` / `mcp_email_skill` - For email actions
- `linkedin_skill` - For social media actions
- `odoo_skill` - For invoice actions
