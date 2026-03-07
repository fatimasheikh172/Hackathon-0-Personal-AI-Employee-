# WhatsApp Skill

## Description

This skill monitors WhatsApp messages, detects urgent communications using keyword analysis, creates action files, assigns priority levels, and provides response templates for common scenarios.

## When To Use This Skill

- When monitoring WhatsApp for incoming messages
- When detecting urgent client/colleague messages
- When categorizing message priority
- When drafting WhatsApp responses
- When creating action files from messages

## Step By Step Instructions

### 1. Detect Urgent Messages

```python
import re
from datetime import datetime

URGENCY_KEYWORDS = {
    'urgent': ['urgent', 'urgently', 'urgency'],
    'asap': ['asap', 'as soon as possible', 'immediately'],
    'invoice': ['invoice', 'invoices', 'billing', 'payment'],
    'payment': ['payment', 'pay', 'paid', 'transfer', 'bank'],
    'help': ['help', 'assistance', 'support', 'issue', 'problem'],
    'emergency': ['emergency', 'critical', 'crisis'],
    'deadline': ['deadline', 'due today', 'ending today']
}

def detect_urgency(message_text):
    """Detect urgency level in WhatsApp message."""
    text_lower = message_text.lower()
    
    urgency_score = 0
    found_keywords = []
    
    for category, keywords in URGENCY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                urgency_score += 1
                found_keywords.append(keyword)
    
    # Determine priority level
    if urgency_score >= 3 or 'emergency' in found_keywords:
        return 'high', found_keywords
    elif urgency_score >= 1:
        return 'medium', found_keywords
    else:
        return 'low', found_keywords
```

**Urgency Detection Rules:**
- **High Priority:** 3+ urgency keywords OR contains "emergency"/"critical"
- **Medium Priority:** 1-2 urgency keywords
- **Low Priority:** No urgency keywords

### 2. Priority Levels Assignment

```python
def assign_priority(message, urgency_level, sender_info):
    """Assign final priority considering sender and context."""
    
    # Base priority from urgency
    priority_map = {'high': 1, 'medium': 2, 'low': 3}
    base_priority = priority_map.get(urgency_level, 3)
    
    # Adjust for sender type
    if sender_info.get('is_vip'):
        base_priority = max(1, base_priority - 1)  # Increase priority
    elif sender_info.get('is_unknown'):
        base_priority = min(3, base_priority + 1)  # Decrease priority
    
    # Adjust for time sensitivity
    if is_outside_business_hours():
        if urgency_level == 'high':
            base_priority = 1  # Keep high priority even after hours
    
    priority_names = {1: 'high', 2: 'medium', 3: 'low'}
    return priority_names.get(base_priority, 'medium')
```

**Priority Level Definitions:**
- **High:** Immediate action required (respond within 15 minutes)
- **Medium:** Action required today (respond within 2 hours)
- **Low:** Action when available (respond within 24 hours)

### 3. Create Action Files

```python
def create_whatsapp_action(message, priority, keywords):
    """Create action file from WhatsApp message."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"Needs_Action/ACTION_whatsapp_{timestamp}.md"
    
    # Sanitize sender name for filename
    safe_sender = re.sub(r'[^a-zA-Z0-9]', '_', message['sender'])[:20]
    
    content = f"""---
action_type: whatsapp_response
source: WhatsApp
sender: {message['sender']}
sender_number: {message.get('number', 'Unknown')}
created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
priority: {priority}
urgency_keywords: {', '.join(keywords)}
status: pending
---

# WhatsApp Message Action

**From:** {message['sender']}
**Received:** {message['timestamp']}
**Priority:** {priority.upper()}

## Message Content
{message['text']}

## Detected Keywords
{', '.join(keywords) if keywords else 'None'}

## Required Action
- [ ] Review message
- [ ] Draft response (see templates below)
- [ ] Send response or escalate
- [ ] Move to Done/ when complete

## Response Templates
See templates in section below based on message type.
"""
    
    write_vault_file(filename, content)
    return filename
```

### 4. Response Templates

**Template: Invoice Request**
```
Hi [Name], thanks for reaching out. I'm preparing your invoice now and 
will send it within [timeframe]. Please confirm the billing details are 
still [details]. Best regards!
```

**Template: Payment Confirmation**
```
Hi [Name], yes, we received your payment on [date]. Thank you! Your 
account is up to date. Let me know if you need anything else!
```

**Template: Urgent Help Request**
```
Hi [Name], I understand this is urgent. I'm looking into it right now 
and will get back to you within [timeframe] with a solution. Thanks for 
your patience!
```

**Template: General Inquiry**
```
Hi [Name], thanks for your message! [Answer to inquiry]. Let me know if 
you need any clarification. Best regards!
```

**Template: Meeting Request**
```
Hi [Name], I'd be happy to meet. I'm available [availability options]. 
Please let me know what works for you. Thanks!
```

**Template: Out of Hours Auto-Reply**
```
Hi [Name], thanks for your message. I'm currently outside business hours 
but will respond first thing in the morning. If this is urgent, please 
call [emergency contact]. Thanks!
```

### 5. Draft Response

```python
def draft_whatsapp_response(message, template_type, custom_content=None):
    """Draft WhatsApp response using template."""
    templates = {
        'invoice_request': INVOICE_TEMPLATE,
        'payment_confirmation': PAYMENT_TEMPLATE,
        'urgent_help': URGENT_HELP_TEMPLATE,
        'general_inquiry': GENERAL_TEMPLATE,
        'meeting_request': MEETING_TEMPLATE,
    }
    
    template = templates.get(template_type, GENERAL_TEMPLATE)
    
    # Personalize template
    response = template.replace('[Name]', message['sender'].split()[0])
    
    if custom_content:
        response = response.replace('[custom]', custom_content)
    
    # Save draft
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    draft_file = f"Drafts/whatsapp_draft_{timestamp}.md"
    
    content = f"""---
type: whatsapp_draft
to: {message['sender']}
to_number: {message.get('number', '')}
created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
status: draft
---

# WhatsApp Draft Response

**To:** {message['sender']}

{response}

---
## Original Message
{message['text']}
"""
    
    write_vault_file(draft_file, content)
    return draft_file, response
```

## Examples

### Example 1: Urgent Invoice Request

**Incoming Message:**
```
From: John Client
Number: +1234567890
Text: "URGENT! Need invoice ASAP for payment processing. Deadline today!"
Timestamp: 2026-03-07 09:30:00
```

**Processing:**
```python
urgency_level, keywords = detect_urgency(message['text'])
# Returns: 'high', ['urgent', 'asap', 'invoice', 'deadline']

priority = assign_priority(message, urgency_level, {'is_vip': False})
# Returns: 'high'

create_whatsapp_action(message, priority, keywords)
```

**Created Action File:**
```markdown
---
action_type: whatsapp_response
source: WhatsApp
sender: John Client
sender_number: +1234567890
created_at: 2026-03-07 09:30:00
priority: high
urgency_keywords: urgent, asap, invoice, deadline
status: pending
---

# WhatsApp Message Action

**From:** John Client
**Received:** 2026-03-07 09:30:00
**Priority:** HIGH

## Message Content
URGENT! Need invoice ASAP for payment processing. Deadline today!

## Detected Keywords
urgent, asap, invoice, deadline

## Required Action
- [ ] Review message
- [ ] Create invoice (see odoo_skill)
- [ ] Send invoice via WhatsApp
- [ ] Move to Done/ when complete
```

### Example 2: Payment Confirmation

**Incoming Message:**
```
From: Sarah Partner
Text: "Hi, just confirming the payment was sent yesterday. Can you check?"
```

**Processing:**
```python
urgency_level, keywords = detect_urgency(message['text'])
# Returns: 'medium', ['payment']

# Draft response
draft_file, response = draft_whatsapp_response(
    message, 
    'payment_confirmation',
    custom_content='I can confirm we received it this morning.'
)
```

## Error Handling

### WhatsApp API Unavailable

```python
try:
    messages = get_whatsapp_messages()
except WhatsAppAPIError as e:
    log_error(f"WhatsApp API error: {e}")
    create_alert("WhatsApp monitoring paused - API unavailable")
    # Retry with exponential backoff
    schedule_retry(check_whatsapp, delay=300)  # 5 minutes
```

### Unknown Sender

```python
if sender_info.get('is_unknown'):
    # Create approval request for new contact
    create_approval_request({
        'type': 'new_whatsapp_contact',
        'sender': message['sender'],
        'number': message.get('number'),
        'message': message['text'],
        'reason': 'Unknown WhatsApp contact'
    })
```

### Template Not Found

```python
if template_type not in templates:
    log_warning(f"Template not found: {template_type}")
    # Use generic template
    template_type = 'general_inquiry'
```

## Human Escalation Rules

**Always Escalate to Human:**
1. Message from unknown number with urgent keywords
2. Message mentions: lawsuit, legal, court, police, fraud
3. Payment/invoice requests over $100 (see hitl_skill)
4. Threats or abusive language
5. Requests for sensitive information (passwords, bank details)
6. Media/content that requires human review
7. Bulk message requests (forwarding to multiple contacts)

**Escalation Format:**
```markdown
---
approval_type: whatsapp_review
message_id: <whatsapp_msg_id>
sender: <sender_name>
number: <sender_number>
reason: <escalation_reason>
priority: <high|medium|low>
timestamp: 2026-03-07 09:30:00
---

# WhatsApp Review Required

**Sender:** Unknown Contact (+1234567890)
**Message:** [Full message content]
**Issue:** Unknown sender with urgent request
**Recommended Action:** Verify sender identity and respond appropriately
```

## Related Skills

- `hitl_skill` - For approval workflows
- `email_skill` - For email-based communications
- `file_watcher_skill` - Creates action files
- `odoo_skill` - For invoice-related messages
