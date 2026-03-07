# Vault Manager Skill

## Description

This skill manages reading from and writing to the vault storage system. It handles all file operations within the AI_Employee_Vault, maintains folder structure integrity, and updates the Dashboard.md file.

## When To Use This Skill

- When reading configuration or reference files from the vault
- When writing reports, logs, or completed task files
- When updating Dashboard.md with system status
- When organizing files according to vault structure rules

## Step By Step Instructions

### 1. Vault Folder Structure

The vault follows this structure:

```
F:/AI_Employee_Vault/
├── Inbox/              # Incoming files (monitored by file_watcher)
├── Needs_Action/       # Pending tasks requiring action
├── Done/               # Completed tasks (archived)
├── Pending_Approval/   # Tasks awaiting human approval
├── Drafts/             # Work in progress
├── Briefings/          # CEO briefings and reports
├── Logs/               # System logs
├── Quarantine/         # Suspicious/problematic files
├── Templates/          # Reusable templates
├── .claude/            # Claude-specific configuration
│   └── skills/         # Skill definitions
├── Business_Goals.md   # Company goals and targets
├── Dashboard.md        # System status dashboard
└── ARCHITECTURE.md     # System architecture docs
```

### 2. Reading Files from Vault

```python
import os
from datetime import datetime

VAULT_ROOT = "F:/AI_Employee_Vault"

def read_vault_file(relative_path):
    """Read a file from the vault."""
    full_path = os.path.join(VAULT_ROOT, relative_path)
    
    # Security check: ensure path is within vault
    if not full_path.startswith(VAULT_ROOT):
        raise SecurityError("Path traversal detected")
    
    if not os.path.exists(full_path):
        raise FileNotFoundError(f"File not found: {relative_path}")
    
    with open(full_path, 'r', encoding='utf-8') as f:
        return f.read()
```

**Reading Rules:**
- Always validate path is within vault (prevent path traversal)
- Use UTF-8 encoding for all text files
- Handle FileNotFoundError gracefully
- Log all read operations to `Logs/vault_access.log`

### 3. Writing Reports to Vault

```python
def write_vault_file(relative_path, content, overwrite=False):
    """Write a file to the vault."""
    full_path = os.path.join(VAULT_ROOT, relative_path)
    
    # Security check
    if not full_path.startswith(VAULT_ROOT):
        raise SecurityError("Path traversal detected")
    
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    # Check if file exists
    if os.path.exists(full_path) and not overwrite:
        raise FileExistsError(f"File exists: {relative_path}. Use overwrite=True")
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    log_access(f"Wrote: {relative_path}")
    return full_path
```

**Writing Rules:**
- Never overwrite without explicit `overwrite=True` flag
- Always create parent directories if missing
- Log all write operations
- Use atomic writes when possible (write to temp, then rename)

### 4. Dashboard.md Update Rules

**Dashboard Location:** `F:/AI_Employee_Vault/Dashboard.md`

**Update Frequency:** Every 5 minutes or after significant events

**Dashboard Format:**
```markdown
# AI Employee System Dashboard

Last Updated: 2026-03-07 09:30:00

## System Status
- Status: OPERATIONAL
- Uptime: 99.8%

## Queue Status
| Folder | Count |
|--------|-------|
| Inbox | 3 |
| Needs_Action | 12 |
| Pending_Approval | 2 |
| Drafts | 5 |

## Today's Activity
- Tasks Completed: 15
- Emails Processed: 23
- Errors: 0

## Recent Completions
- [2026-03-07 09:15] Created invoice #INV-2026-001
- [2026-03-07 09:00] Replied to client email
- [2026-03-07 08:45] Generated LinkedIn post

## Pending Approvals
- Invoice approval: $500 (Client ABC)
- New contact request: john@newclient.com

## Alerts
- None
```

**Update Function:**
```python
def update_dashboard():
    """Update Dashboard.md with current system status."""
    dashboard_data = {
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'inbox_count': count_files('Inbox'),
        'needs_action_count': count_files('Needs_Action'),
        'pending_approval_count': count_files('Pending_Approval'),
        'drafts_count': count_files('Drafts'),
        'done_today': count_files_today('Done'),
        'errors_today': count_errors_today(),
    }
    
    content = generate_dashboard_content(dashboard_data)
    write_vault_file('Dashboard.md', content, overwrite=True)
```

## Examples

### Example 1: Reading Business Goals

```python
# Read business goals for context
goals_content = read_vault_file('Business_Goals.md')
print(goals_content)
```

### Example 2: Writing Completed Task

```python
# Archive completed task
task_report = """
# Task Completion Report

**Task:** Email reply to client
**Completed:** 2026-03-07 09:30:00
**Duration:** 5 minutes
**Result:** Reply sent successfully

## Actions Taken
1. Read incoming email
2. Drafted response
3. Sent via MCP email server
4. Logged to Done/

## Files Generated
- Done/email_reply_20260307_093000.md
"""

write_vault_file('Done/email_reply_20260307_093000.md', task_report)
```

### Example 3: Updating Dashboard

```python
# After completing a task, update dashboard
update_dashboard()
```

## Error Handling

### File Not Found

```python
try:
    content = read_vault_file('nonexistent.md')
except FileNotFoundError as e:
    log_error(f"File not found: {e}")
    # Create alert if critical file
    if relative_path in ['Business_Goals.md', 'Dashboard.md']:
        create_alert(f"Critical file missing: {relative_path}")
```

### Permission Denied

```python
try:
    write_vault_file('Done/report.md', content)
except PermissionError as e:
    log_error(f"Permission denied: {e}")
    create_alert("Cannot write to vault - check permissions")
```

### Disk Space Issues

```python
import shutil

def check_disk_space():
    """Ensure sufficient disk space before writing."""
    total, used, free = shutil.disk_usage("F:/")
    if free < 100 * 1024 * 1024:  # Less than 100MB
        create_alert("Low disk space - less than 100MB free")
        return False
    return True
```

## Human Escalation Rules

**Escalate to Human When:**
1. Critical files missing (Business_Goals.md, Dashboard.md)
2. Disk space below 100MB
3. Permission errors persist after retry
4. Dashboard shows Needs_Action count > 100 (backlog)
5. Any file in Quarantine/ folder (requires review)

**Escalation File Format:**
```markdown
---
alert_type: vault_error
severity: high
timestamp: 2026-03-07 09:30:00
---

# Vault Access Error

**Issue:** Cannot write to Done/ folder
**Error:** Permission denied
**Impact:** Tasks cannot be archived
**Required Action:** Check folder permissions
```

## Related Skills

- `file_watcher_skill` - Monitors Inbox folder
- `task_processor_skill` - Moves files to Done/
- `ceo_briefing_skill` - Reads from vault for reports
- `error_recovery_skill` - Handles vault errors
