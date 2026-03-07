# Email Skill

## Description

This skill processes Gmail emails, drafts replies, detects priority levels, and handles known contacts. It integrates with the Gmail watcher and determines when to escalate to human review.

## When To Use This Skill

- When processing incoming Gmail messages
- When drafting email replies
- When categorizing email priority
- When managing known contact relationships
- When determining if human review is needed

## Step By Step Instructions

### 1. Process Gmail Emails

```python
from gmail_watcher import get_unread_emails, mark_as_read

def process_incoming_emails():
    """Fetch and process unread Gmail messages."""
    emails = get_unread_emails(max_results=10)
    
    for email in emails:
        # Extract email data
        email_data = {
            'id': email['id'],
            'from': email['from'],
            'subject': email['subject'],
            'body': email['body'],
            'timestamp': email['timestamp'],
            'attachments': email.get('attachments', [])
        }
        
        # Mark as read
        mark_as_read(email['id'])
        
        # Process email
        handle_email(email_data)
```

**Email Processing Steps:**
1. Fetch unread emails (max 10 per batch)
2. Extract sender, subject, body, attachments
3. Mark as read in Gmail
4. Detect priority level
5. Check if sender is known contact
6. Create action file or draft reply

### 2. Draft Email Replies

```python
def draft_reply(original_email, reply_content):
    """Create draft email reply."""
    draft = {
        'to': original_email['from'],
        'subject': f"Re: {original_email['subject']}",
        'body': reply_content,
        'in_reply_to': original_email['id'],
        'attachments': []
    }
    
    # Save as draft file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    draft_file = f"Drafts/email_draft_{timestamp}.md"
    
    content = f"""---
type: email_draft
to: {draft['to']}
subject: {draft['subject']}
created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
status: draft
---

# Email Draft

**To:** {draft['to']}
**Subject:** {draft['subject']}

{draft['body']}

---
## Original Email

**From:** {original_email['from']}
**Date:** {original_email['timestamp']}

{original_email['body']}
"""
    
    write_vault_file(draft_file, content)
    return draft_file
```

**Reply Guidelines:**
- Keep replies concise and professional
- Address all questions from original email
- Include signature if sending to external contacts
- Reference previous correspondence when relevant
- Proofread before marking as ready to send

### 3. Priority Detection Rules

**High Priority Indicators:**
- Subject contains: URGENT, ASAP, EMERGENCY, CRITICAL
- Body contains: urgent, asap, emergency, critical, immediately, today, deadline
- Sender is VIP contact (CEO, key client, manager)
- Email mentions: invoice, payment, money, contract, legal
- Multiple exclamation marks or all caps

**Medium Priority Indicators:**
- Subject contains: Action Required, Review Needed, Important
- Body contains: soon, this week, priority, important, reminder, please
- Sender is regular contact
- Email requires response but not immediate

**Low Priority:**
- Newsletters and notifications
- Automated system messages
- Informational emails (no action needed)
- Default category if no indicators found

```python
def detect_priority(email_data):
    """Detect email priority level."""
    subject = email_data['subject'].lower()
    body = email_data['body'].lower()
    sender = email_data['from']
    
    high_keywords = ['urgent', 'asap', 'emergency', 'critical', 
                     'immediately', 'today', 'deadline', 'invoice', 
                     'payment', 'money']
    medium_keywords = ['soon', 'this week', 'priority', 'important', 
                       'reminder', 'please', 'review']
    
    # Check for high priority
    for keyword in high_keywords:
        if keyword in subject or keyword in body:
            return 'high'
    
    # Check for VIP sender
    if is_vip_sender(sender):
        return 'high'
    
    # Check for medium priority
    for keyword in medium_keywords:
        if keyword in subject or keyword in body:
            return 'medium'
    
    return 'low'
```

### 4. Known Contacts Handling

**Known Contacts List:**
Maintain a file `Templates/known_contacts.json`:

```json
{
  "vip": [
    {"email": "ceo@company.com", "name": "CEO"},
    {"email": "manager@company.com", "name": "Manager"}
  ],
  "clients": [
    {"email": "john@client.com", "name": "John Client", "company": "Client Corp"},
    {"email": "sarah@partner.com", "name": "Sarah Partner", "company": "Partner Inc"}
  ],
  "vendors": [
    {"email": "support@vendor.com", "name": "Vendor Support"}
  ],
  "internal": [
    {"email": "team@company.com", "name": "Internal Team"}
  ]
}
```

**Contact Handling Rules:**
- VIP: Always high priority, auto-escalate complex requests
- Clients: High priority, professional tone required
- Vendors: Medium priority, standard responses OK
- Internal: Medium priority, casual tone OK
- Unknown: Medium priority, verify before sharing sensitive info

```python
def get_contact_category(email_address):
    """Get category for email address."""
    with open('Templates/known_contacts.json', 'r') as f:
        contacts = json.load(f)
    
    for category, contact_list in contacts.items():
        for contact in contact_list:
            if contact['email'].lower() == email_address.lower():
                return category
    
    return 'unknown'
```

## Examples

### Example 1: High Priority Client Email

**Incoming Email:**
```
From: john@client.com
Subject: URGENT: Invoice needed for payment
Body: Hi, we need the invoice ASAP to process payment this week. 
Please send it immediately. Thanks, John
```

**Processing:**
```python
priority = detect_priority(email)  # Returns 'high'
category = get_contact_category('john@client.com')  # Returns 'clients'

# Create action file
create_action_file({
    'action_type': 'email_reply',
    'priority': 'high',
    'contact_category': 'clients',
    'requires_approval': False,  # Known client, can draft reply
    'notes': 'Invoice request - may need odoo_skill'
})
```

### Example 2: Unknown Sender Request

**Incoming Email:**
```
From: newperson@unknown.com
Subject: Partnership opportunity
Body: Hello, I'd like to discuss a potential partnership...
```

**Processing:**
```python
priority = detect_priority(email)  # Returns 'medium'
category = get_contact_category('newperson@unknown.com')  # Returns 'unknown'

# Escalate - unknown contact
create_approval_request({
    'type': 'new_contact',
    'email': email,
    'reason': 'Unknown sender - requires human review',
    'suggested_action': 'Review and categorize contact'
})
```

### Example 3: Draft Reply

**Reply Draft:**
```markdown
---
type: email_draft
to: john@client.com
subject: Re: URGENT: Invoice needed for payment
created_at: 2026-03-07 09:30:00
status: draft
---

# Email Draft

**To:** john@client.com
**Subject:** Re: URGENT: Invoice needed for payment

Hi John,

Thank you for your email. I'm preparing your invoice now and will send it 
within the next hour.

Could you please confirm the invoice should be sent to this email address?

Best regards,
AI Employee

---
## Original Email

**From:** john@client.com
**Date:** 2026-03-07 09:25:00

Hi, we need the invoice ASAP to process payment this week. 
Please send it immediately. Thanks, John
```

## Error Handling

### Gmail API Error

```python
try:
    emails = get_unread_emails(max_results=10)
except GmailAPIError as e:
    log_error(f"Gmail API error: {e}")
    # Retry with backoff
    if retry_count < 3:
        time.sleep(2 ** retry_count)
        retry_count += 1
    else:
        create_alert("Gmail API unavailable - emails not processing")
```

### Reply Draft Failure

```python
try:
    draft_file = draft_reply(email, reply_content)
except Exception as e:
    log_error(f"Draft creation failed: {e}")
    # Save raw content for manual review
    save_for_review(email, reply_content)
```

### Contact List Corruption

```python
try:
    contacts = load_known_contacts()
except JSONDecodeError:
    log_error("Known contacts file corrupted")
    # Use empty contacts list
    contacts = {'vip': [], 'clients': [], 'vendors': [], 'internal': []}
    create_alert("Known contacts file needs repair")
```

## Human Escalation Rules

**Always Escalate to Human:**
1. Unknown sender with sensitive request (invoice, payment, contract)
2. Email mentions legal, compliance, or HR topics
3. Complaint or negative feedback from client
4. Request involves money > $100 (see hitl_skill)
5. Bulk email requests (> 5 recipients)
6. Email with suspicious attachments
7. Sender requests to be removed from mailing list

**Escalation Format:**
```markdown
---
approval_type: email_review
email_id: <gmail_id>
from: <sender_email>
priority: <high|medium|low>
reason: <escalation_reason>
timestamp: 2026-03-07 09:30:00
---

# Email Review Required

**From:** john@unknown.com
**Subject:** Partnership opportunity
**Issue:** Unknown sender - requires categorization
**Recommended Action:** Review sender and draft appropriate response

## Email Content
[Full email content here]
```

## Related Skills

- `mcp_email_skill` - Alternative email handling via MCP
- `hitl_skill` - For approval workflows
- `odoo_skill` - For invoice-related emails
- `file_watcher_skill` - Creates action files
- `vault_manager_skill` - Manages draft files
