# File Watcher Skill

## Description

This skill monitors the `Inbox/` folder for new incoming files and creates corresponding action files in `Needs_Action/`. It is the entry point for all automated tasks in the AI Employee system.

## When To Use This Skill

- When monitoring for new incoming files in the Inbox folder
- When setting up automated file processing workflows
- When implementing the first stage of the task pipeline
- During system initialization to check for pending files

## Step By Step Instructions

### 1. Monitor Inbox Folder

```python
import os
import time
from datetime import datetime

INBOX_FOLDER = "F:/AI_Employee_Vault/Inbox"
NEEDS_ACTION_FOLDER = "F:/AI_Employee_Vault/Needs_Action"

def monitor_inbox():
    """Check Inbox for new files every 5 seconds."""
    while True:
        files = os.listdir(INBOX_FOLDER)
        for filename in files:
            if filename.endswith('.md') or filename.endswith('.txt'):
                create_action_file(filename)
        time.sleep(5)
```

### 2. Create Action File in Needs_Action/

When a new file is detected:

1. Read the original file content
2. Extract metadata (filename, timestamp, file type)
3. Create a new action file with prefix `ACTION_`
4. Include original file reference

**File Naming Convention:**
```
ACTION_<original_filename>_<YYYYMMDD_HHMMSS>.md
```

**Example:**
```
Original: client_request.md
Action File: ACTION_client_request_20260307_093000.md
```

### 3. Metadata Creation Rules

Every action file MUST include this metadata header:

```markdown
---
action_type: <type>
source_file: <original_filename>
created_at: <YYYY-MM-DD HH:MM:SS>
priority: <high|medium|low>
status: pending
---
```

**Metadata Fields:**
- `action_type`: Type of action needed (email_reply, task_process, invoice_create, etc.)
- `source_file`: Path to original file in Inbox/
- `created_at`: Timestamp when action file was created
- `priority`: Determined by file content keywords (see Priority Detection)
- `status`: Always starts as "pending"

### 4. Priority Detection

Scan file content for priority keywords:

**High Priority Keywords:**
- urgent, asap, emergency, critical, immediately, today, deadline

**Medium Priority Keywords:**
- soon, this week, priority, important, reminder

**Low Priority:**
- Default if no keywords found

## Examples

### Example 1: New Email Request File

**Inbox/email_request.md:**
```
From: john@client.com
Subject: Urgent: Invoice needed
Body: Please send invoice ASAP for project completion.
```

**Created Action File:**
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

**Next Steps:**
- [ ] Draft email reply
- [ ] Create invoice if needed (see odoo_skill)
- [ ] Move to Done/ when complete
```

### Example 2: Task Request File

**Inbox/task_request.md:**
```
Task: Create LinkedIn post about new product launch
Details: Product launches next Monday, need promotional content
```

**Created Action File:**
```
Needs_Action/ACTION_task_request_20260307_100000.md

---
action_type: social_media
source_file: Inbox/task_request.md
created_at: 2026-03-07 10:00:00
priority: medium
status: pending
---

# Action Required: Social Media Content

**Task:** Create LinkedIn post about new product launch

**Details:** Product launches next Monday, need promotional content

**Next Steps:**
- [ ] Generate LinkedIn post (see linkedin_skill)
- [ ] Submit for approval if needed (see hitl_skill)
- [ ] Move to Done/ when complete
```

## Error Handling

### File Already Exists in Needs_Action/

If an action file with the same source already exists:
- Skip creation
- Log warning: "Action file already exists for <filename>"
- Continue monitoring

### Inbox Folder Not Accessible

- Log error to `Logs/file_watcher_errors.log`
- Create alert file: `Needs_Action/ALERT_inbox_unavailable_<timestamp>.md`
- Continue monitoring (may be temporary)

### Invalid File Format

- If file cannot be read (binary, corrupted):
- Create alert: `Needs_Action/ALERT_invalid_file_<filename>.md`
- Move original to `Quarantine/` folder

## Human Escalation Rules

**Escalate to Human When:**
1. More than 50 files accumulate in Needs_Action/ (system overload)
2. Same file triggers repeated errors (3+ times)
3. Alert files are created (ALERT_*.md)
4. Inbox folder contains non-standard file types

**Escalation Format:**
```markdown
---
alert_type: escalation
severity: high
requires_human: true
---

# Human Review Required

**Issue:** <description>
**Files Affected:** <list>
**Recommended Action:** <suggestion>
```

## Related Skills

- `task_processor_skill` - Processes files created in Needs_Action/
- `hitl_skill` - For approval workflows
- `error_recovery_skill` - For handling failures
