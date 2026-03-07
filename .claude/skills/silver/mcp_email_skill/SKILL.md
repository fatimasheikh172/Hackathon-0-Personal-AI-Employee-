# MCP Email Skill

## Description

This skill uses the Email MCP server for email operations, manages draft vs send decisions, handles attachments, and enforces rate limiting (max 10 emails/hour).

## When To Use This Skill

- When sending emails via MCP server
- When managing email drafts
- When handling email attachments
- When rate limiting is required
- When integrating with Email MCP tools

## Step By Step Instructions

### 1. Use Email MCP Server

```python
# MCP Email Server Configuration
MCP_EMAIL_CONFIG = {
    'server': 'email_mcp_server.py',
    'draft_folder': 'Drafts/',
    'sent_folder': 'Done/',
    'rate_limit': 10,  # emails per hour
    'rate_window': 3600,  # seconds
}

def get_mcp_email_client():
    """Initialize MCP email client."""
    # This connects to the Email MCP server
    return EmailMCPClient(config=MCP_EMAIL_CONFIG)
```

**MCP Email Tools Available:**
- `email_send` - Send email immediately
- `email_draft` - Create draft email
- `email_read` - Read incoming emails
- `email_list` - List emails in folder
- `email_attachment_add` - Add attachment to draft

### 2. Draft vs Send Rules

**When to Draft:**
- First email to a contact
- Emails requiring approval (see hitl_skill)
- Emails with attachments > 5MB
- Bulk emails (> 3 recipients)
- Emails mentioning sensitive topics (payments, contracts)
- Outside business hours (6 PM - 8 AM)

**When to Send Directly:**
- Reply to known contact
- Simple informational emails
- Emails < 3 recipients
- During business hours
- No sensitive content

```python
def should_draft_or_send(email_details):
    """Decide whether to draft or send email."""
    reasons_to_draft = []
    
    # Check recipient count
    if len(email_details.get('to', [])) > 3:
        reasons_to_draft.append("Bulk email (>3 recipients)")
    
    # Check if new contact
    if is_new_contact(email_details.get('to', [])):
        reasons_to_draft.append("New contact")
    
    # Check for sensitive content
    sensitive_keywords = ['payment', 'invoice', 'contract', 'legal', 'confidential']
    body = email_details.get('body', '').lower()
    for keyword in sensitive_keywords:
        if keyword in body:
            reasons_to_draft.append(f"Sensitive content: {keyword}")
            break
    
    # Check time
    if is_outside_business_hours():
        reasons_to_draft.append("Outside business hours")
    
    # Check attachments
    if email_details.get('attachments'):
        total_size = sum(a.get('size', 0) for a in email_details['attachments'])
        if total_size > 5 * 1024 * 1024:  # 5MB
            reasons_to_draft.append("Large attachment")
    
    # Decision
    if reasons_to_draft:
        return 'draft', reasons_to_draft
    else:
        return 'send', []
```

### 3. Create Draft Email

```python
def create_mcp_draft(email_details):
    """Create draft email using MCP server."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    draft_file = f"Drafts/email_mcp_draft_{timestamp}.md"
    
    content = f"""---
type: mcp_email_draft
to: {', '.join(email_details['to'])}
cc: {', '.join(email_details.get('cc', []))}
subject: {email_details['subject']}
created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
status: draft
has_attachments: {len(email_details.get('attachments', [])) > 0}
---

# MCP Email Draft

**To:** {', '.join(email_details['to'])}
**CC:** {', '.join(email_details.get('cc', [])) if email_details.get('cc') else 'None'}
**Subject:** {email_details['subject']}

## Body

{email_details['body']}

## Attachments
{format_attachments(email_details.get('attachments', []))}

---
## MCP Send Instructions
To send this draft:
1. Review content above
2. Verify recipients
3. Check attachments
4. Use MCP tool: email_send with draft_file path
"""
    
    write_vault_file(draft_file, content)
    return draft_file
```

### 4. Send Email via MCP

```python
def send_mcp_email(email_details):
    """Send email using MCP server with rate limiting."""
    
    # Check rate limit
    if not check_rate_limit():
        wait_time = get_wait_time_for_rate_limit()
        return {
            'success': False,
            'error': f'Rate limit reached. Wait {wait_time} minutes.',
            'action': 'queue_for_later'
        }
    
    # Send via MCP
    try:
        client = get_mcp_email_client()
        result = client.send(
            to=email_details['to'],
            subject=email_details['subject'],
            body=email_details['body'],
            cc=email_details.get('cc'),
            attachments=email_details.get('attachments')
        )
        
        # Log sent email
        log_sent_email(email_details, result)
        
        return {
            'success': True,
            'message_id': result.get('message_id'),
            'sent_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        log_error(f"MCP email send failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
```

### 5. Attachment Handling

```python
def handle_email_attachments(attachments):
    """Process and validate email attachments."""
    processed = []
    max_size = 25 * 1024 * 1024  # 25MB max per email
    total_size = 0
    
    allowed_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', 
                          '.png', '.jpg', '.jpeg', '.txt', '.csv']
    
    for attachment in attachments:
        # Check file extension
        ext = os.path.splitext(attachment.get('filename', ''))[1].lower()
        if ext not in allowed_extensions:
            log_warning(f"Unsupported attachment type: {ext}")
            continue
        
        # Check file size
        size = attachment.get('size', 0)
        total_size += size
        
        if total_size > max_size:
            log_warning("Total attachment size exceeds limit")
            break
        
        # Store attachment reference
        processed.append({
            'filename': attachment['filename'],
            'path': attachment.get('path'),
            'size': size,
            'type': ext
        })
    
    return processed
```

**Attachment Guidelines:**
- Max 25MB total per email
- Allowed types: PDF, DOC, DOCX, XLS, XLSX, PNG, JPG, JPEG, TXT, CSV
- Scan for viruses before sending
- Compress large files when possible

### 6. Rate Limiting

**Rate Limit Rules:**
- Maximum 10 emails per hour
- Maximum 50 emails per day
- Cooldown period after reaching limit

```python
# Rate limiting storage
email_send_log = []

def check_rate_limit():
    """Check if rate limit allows sending."""
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)
    
    # Count emails in last hour
    hour_count = sum(1 for t in email_send_log if t > one_hour_ago)
    if hour_count >= 10:
        return False
    
    # Count emails in last day
    day_count = sum(1 for t in email_send_log if t > one_day_ago)
    if day_count >= 50:
        return False
    
    return True

def get_wait_time_for_rate_limit():
    """Calculate wait time until rate limit resets."""
    if not email_send_log:
        return 0
    
    oldest_in_hour = min(email_send_log)
    one_hour_ago = datetime.now() - timedelta(hours=1)
    
    if oldest_in_hour > one_hour_ago:
        wait_until = oldest_in_hour + timedelta(hours=1)
        wait_minutes = (wait_until - datetime.now()).seconds / 60
        return max(1, int(wait_minutes))
    
    return 0

def log_sent_email(email_details, result):
    """Log sent email for rate limiting."""
    email_send_log.append(datetime.now())
    
    # Clean old entries (older than 24 hours)
    cutoff = datetime.now() - timedelta(days=1)
    email_send_log[:] = [t for t in email_send_log if t > cutoff]
```

## Examples

### Example 1: Draft Email (Requires Approval)

**Input:**
```python
email_details = {
    'to': ['newclient@example.com'],
    'subject': 'Partnership Proposal',
    'body': 'Dear Partner, We would like to discuss a potential partnership...',
    'attachments': []
}
```

**Processing:**
```python
action, reasons = should_draft_or_send(email_details)
# Returns: 'draft', ['New contact']

draft_file = create_mcp_draft(email_details)
# Creates: Drafts/email_mcp_draft_20260307_100000.md
```

### Example 2: Send Email (Within Rate Limit)

**Input:**
```python
email_details = {
    'to': ['known@client.com'],
    'subject': 'Re: Project Update',
    'body': 'Hi, here is the project update you requested...',
    'attachments': [{'filename': 'report.pdf', 'path': '/path/report.pdf'}]
}
```

**Processing:**
```python
if check_rate_limit():  # True
    result = send_mcp_email(email_details)
    # Returns: {'success': True, 'message_id': 'msg_123', 'sent_at': '...'}
```

## Error Handling

### MCP Server Unavailable

```python
try:
    client = get_mcp_email_client()
except MCPConnectionError as e:
    log_error(f"MCP server unavailable: {e}")
    # Fallback to draft creation
    draft_file = create_mcp_draft(email_details)
    create_alert("MCP Email server unavailable - emails queued as drafts")
```

### Rate Limit Exceeded

```python
if not check_rate_limit():
    wait_time = get_wait_time_for_rate_limit()
    log_warning(f"Rate limit exceeded. Wait {wait_time} minutes")
    
    # Queue for later
    queue_email(email_details, send_after=wait_time)
    
    return {
        'success': False,
        'error': 'Rate limit exceeded',
        'retry_after': wait_time
    }
```

### Attachment Error

```python
try:
    processed = handle_email_attachments(attachments)
except AttachmentError as e:
    log_error(f"Attachment error: {e}")
    # Send without attachments
    email_details['attachments'] = []
    create_alert(f"Attachments removed due to error: {e}")
```

## Human Escalation Rules

**Escalate to Human:**
1. Rate limit consistently reached (indicates high volume need)
2. Attachment errors on critical emails
3. MCP server unavailable for > 1 hour
4. Draft emails pending > 24 hours
5. Bounced emails or delivery failures

**Escalation Format:**
```markdown
---
alert_type: mcp_email_issue
issue: <description>
timestamp: 2026-03-07 10:00:00
---

# MCP Email Issue

**Issue:** Rate limit reached frequently
**Impact:** Emails being delayed
**Recommended Action:** Review email volume or increase limits
```

## Related Skills

- `email_skill` - Alternative email handling
- `hitl_skill` - For approval workflows
- `vault_manager_skill` - Manages draft files
- `task_processor_skill` - Executes email tasks
