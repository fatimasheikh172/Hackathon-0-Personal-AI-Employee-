# MASTER SKILL - AI Employee System

## Description

This is the master skill that provides complete system overview, decision trees for common tasks, emergency procedures, human escalation rules, and daily routine checklists. Use this skill to understand which skill to use when and how the entire AI Employee system works together.

## When To Use This Skill

- When starting work on any task in the AI Employee system
- When determining which skill to use
- When troubleshooting system issues
- When onboarding to the system
- When performing daily routines
- When handling emergencies

## Complete System Overview

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI EMPLOYEE SYSTEM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   BRONZE    │    │    SILVER   │    │    GOLD     │        │
│  │   TIER      │    │    TIER     │    │    TIER     │        │
│  ├─────────────┤    ├─────────────┤    ├─────────────┤        │
│  │ File        │    │ Email       │    │ Odoo        │        │
│  │ Watcher     │    │ Skill       │    │ (Finance)   │        │
│  │             │    │             │    │             │        │
│  │ Vault       │    │ WhatsApp    │    │ Twitter     │        │
│  │ Manager     │    │ Skill       │    │ Skill       │        │
│  │             │    │             │    │             │        │
│  │ Task        │    │ LinkedIn    │    │ Instagram   │        │
│  │ Processor   │    │ Skill       │    │ Skill       │        │
│  │             │    │             │    │             │        │
│  │             │    │ Plan        │    │ CEO         │        │
│  │             │    │ Generator   │    │ Briefing    │        │
│  │             │    │             │    │             │        │
│  │             │    │ HITL        │    │ Error       │        │
│  │             │    │ (Approval)  │    │ Recovery    │        │
│  │             │    │             │    │             │        │
│  │             │    │ MCP Email   │    │ Accounting  │        │
│  │             │    │ Skill       │    │ Audit       │        │
│  │             │    │             │    │             │        │
│  │             │    │             │    │ Social      │        │
│  │             │    │             │    │ Content     │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  FOLDERS: Inbox | Needs_Action | Done | Pending_Approval       │
│           | Drafts | Briefings | Logs | Quarantine             │
├─────────────────────────────────────────────────────────────────┤
│  KEY FILES: Dashboard.md | Business_Goals.md | ARCHITECTURE.md │
└─────────────────────────────────────────────────────────────────┘
```

### Tier Responsibilities

**BRONZE TIER (Core Operations):**
- File monitoring and action file creation
- Vault storage management
- Basic task processing
- Foundation for all other operations

**SILVER TIER (Communication & Planning):**
- Email processing and replies
- WhatsApp message handling
- LinkedIn content generation
- Plan creation and approval workflows
- Human-in-the-loop management

**GOLD TIER (Advanced Operations):**
- Financial operations (Odoo)
- Social media management (Twitter, Instagram)
- Executive reporting (CEO Briefing)
- Error recovery and system health
- Accounting audits
- Multi-platform content strategy

## Which Skill to Use When

### Decision Tree for Common Tasks

```
START
  │
  ▼
┌─────────────────────────────────────┐
│ What type of task is this?          │
└─────────────────────────────────────┘
  │
  ├──► File in Inbox/
  │     └──► file_watcher_skill
  │           └──► Creates ACTION file in Needs_Action/
  │                 └──► task_processor_skill
  │
  ├──► Email to process
  │     ├──► Simple reply
  │     │     └──► email_skill → draft reply
  │     ├──► Requires approval
  │     │     └──► email_skill → hitl_skill
  │     └──► Via MCP server
  │           └──► mcp_email_skill
  │
  ├──► WhatsApp message
  │     └──► whatsapp_skill
  │           ├──► Detect urgency
  │           ├──► Create action file
  │           └──► Draft response
  │
  ├──► Social media post needed
  │     ├──► Twitter
  │     │     └──► twitter_skill
  │     ├──► LinkedIn
  │     │     └──► linkedin_skill
  │     ├──► Instagram
  │     │     └──► instagram_skill
  │     └──► All platforms
  │           └──► social_content_skill
  │
  ├──► Invoice/Financial operation
  │     ├──► Create invoice
  │     │     └──► odoo_skill (DRAFT only)
  │     │           └──► hitl_skill (if > $100)
  │     ├──► Check financials
  │     │     └──► odoo_skill → get_financial_summary
  │     └──► Audit transactions
  │           └──► accounting_audit_skill
  │
  ├──► Plan needed
  │     └──► plan_generator_skill
  │           └──► hitl_skill (if requires approval)
  │
  ├──► Approval required
  │     └──► hitl_skill
  │           ├──► Create approval file
  │           └──► Process decision
  │
  ├──► Error occurred
  │     └──► error_recovery_skill
  │           ├──► Categorize error
  │           ├──► Apply handling strategy
  │           └──► Create alert if needed
  │
  ├──► Monday 8 AM
  │     └──► ceo_briefing_skill
  │
  ├──► Sunday 11 PM
  │     └──► accounting_audit_skill
  │
  └──► Health check needed
        └──► error_recovery_skill → perform_health_check
```

### Quick Reference Table

| Task Type | Primary Skill | Secondary Skill | Approval Needed |
|-----------|---------------|-----------------|-----------------|
| New file in Inbox | file_watcher_skill | task_processor_skill | No |
| Email reply | email_skill | mcp_email_skill | If new contact |
| WhatsApp message | whatsapp_skill | - | If urgent/unknown |
| LinkedIn post | linkedin_skill | social_content_skill | Yes |
| Twitter post | twitter_skill | social_content_skill | If new topic |
| Instagram post | instagram_skill | social_content_skill | Yes |
| Create invoice | odoo_skill | hitl_skill | If > $100 |
| Check finances | odoo_skill | - | No |
| Create plan | plan_generator_skill | hitl_skill | If sensitive |
| Process approval | hitl_skill | - | N/A |
| Error handling | error_recovery_skill | - | If persistent |
| CEO briefing | ceo_briefing_skill | odoo_skill | No |
| Weekly audit | accounting_audit_skill | odoo_skill | No |

## Emergency Procedures

### Emergency Contact Flow

```
┌─────────────────────────────────────────────────────────────┐
│ EMERGENCY PROCEDURES                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 1. SYSTEM DOWN                                              │
│    └──► error_recovery_skill → handle_system_error          │
│    └──► Create ALERT file in Needs_Action/                  │
│    └──► Attempt component restart                           │
│    └──► If fails → Escalate to human                        │
│                                                             │
│ 2. DATA CORRUPTION                                          │
│    └──► error_recovery_skill → handle_data_error            │
│    └──► Quarantine affected files                           │
│    └──► Create ALERT file                                   │
│    └──► Human review required                               │
│                                                             │
│ 3. AUTHENTICATION FAILURE                                   │
│    └──► error_recovery_skill → handle_auth_error            │
│    └──► Pause affected operations                           │
│    └──► Create ALERT file                                   │
│    └──► Human must refresh credentials                      │
│                                                             │
│ 4. FINANCIAL ANOMALY                                        │
│    └──► accounting_audit_skill → detect_anomaly             │
│    └──► Create approval file for review                     │
│    └──► Pause related transactions                          │
│    └──► Human investigation required                        │
│                                                             │
│ 5. BACKLOG OVERLOAD (>100 items)                            │
│    └──► Update Dashboard.md with warning                    │
│    └──► Create ALERT file                                   │
│    └──► Prioritize high-priority items only                 │
│    └──► Human review for triage                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Emergency Alert Format

```markdown
---
alert_type: emergency
severity: critical
timestamp: 2026-03-07 10:00:00
requires_immediate_action: true
---

# EMERGENCY ALERT

**Type:** [System Down / Data Corruption / Auth Failure / Financial Anomaly]
**Time:** 2026-03-07 10:00:00
**Impact:** [Description of impact]

## Immediate Actions Taken
1. [Action 1]
2. [Action 2]

## Required Human Actions
1. [Action 1]
2. [Action 2]

## Affected Systems
- [System 1]
- [System 2]

## Contact
Please address immediately.
```

## Human Escalation Rules

### Escalation Matrix

| Situation | When to Escalate | How to Escalate | Urgency |
|-----------|------------------|-----------------|---------|
| Payment > $100 | Always | hitl_skill → approval file | High |
| New Contact | Always | hitl_skill → approval file | Medium |
| Bulk Email > 5 | Always | hitl_skill → approval file | Medium |
| Invoice Posting | Always | odoo_skill → approval file | High |
| Auth Error | On first occurrence | error_recovery_skill → alert | Critical |
| Data Corruption | On detection | error_recovery_skill → quarantine | Critical |
| System Error | After restart fail | error_recovery_skill → alert | Critical |
| Backlog > 100 | On detection | Update Dashboard + alert | High |
| Rate Limit Hit | After 3 occurrences | Create alert | Medium |
| Failed Post | After 3 retries | Create alert | Low |
| Unknown Error | After 3 retries | Create alert | Medium |
| Sensitive Topic | Before posting | hitl_skill → approval | High |

### Escalation File Locations

- **Pending Approvals:** `Pending_Approval/APPROVAL_*.md`
- **System Alerts:** `Needs_Action/ALERT_*.md`
- **Error Reviews:** `Pending_Approval/LOGIC_REVIEW_*.md`
- **Failed Posts:** `Logs/FAILED_POST_*.md`

## Daily Routine Checklist

### Morning Routine (8:00 AM)

```
□ Check Dashboard.md for system status
□ Review Needs_Action/ folder count
□ Check Pending_Approval/ for overnight approvals
□ Review any ALERT files created overnight
□ Process high-priority items first
□ Update Dashboard.md with morning status
```

**Implementation:**
```python
def morning_routine():
    """Execute morning routine checks."""
    # Check Dashboard
    dashboard_status = read_vault_file('Dashboard.md')
    
    # Count pending items
    needs_action_count = count_files('Needs_Action')
    pending_count = count_files('Pending_Approval')
    alert_count = count_files('Needs_Action', pattern='ALERT_*.md')
    
    # Log status
    log_info(f"Morning check: {needs_action_count} actions, {pending_count} approvals, {alert_count} alerts")
    
    # If Monday, generate CEO briefing
    if datetime.now().weekday() == 0 and datetime.now().hour == 8:
        ceo_briefing_skill.generate_briefing()
    
    return {
        'needs_action': needs_action_count,
        'pending_approval': pending_count,
        'alerts': alert_count,
        'status': 'operational' if alert_count == 0 else 'attention_needed'
    }
```

### Continuous Monitoring (Every 5 Minutes)

```
□ Scan Needs_Action/ for new files
□ Process pending tasks (max 10 per batch)
□ Update Dashboard.md if counts change significantly
□ Check for new alerts
□ Monitor system health
```

**Implementation:**
```python
def continuous_monitoring():
    """Run continuous monitoring loop."""
    while True:
        # Scan for new action files
        new_actions = file_watcher_skill.scan_needs_action()
        
        # Process tasks
        if new_actions:
            task_processor_skill.process_batch(new_actions[:10])
        
        # Update dashboard if needed
        update_dashboard_if_changed()
        
        # Wait 5 minutes
        time.sleep(300)
```

### Gmail Check (Every 2 Minutes)

```
□ Check Gmail for new unread emails
□ Process emails with email_skill
□ Create action files for emails requiring action
□ Draft replies for simple emails
□ Escalate complex emails to approval
```

**Implementation:**
```python
def gmail_monitoring():
    """Run Gmail monitoring loop."""
    while True:
        # Check for new emails
        new_emails = email_skill.get_unread_emails()
        
        for email in new_emails:
            email_skill.process_email(email)
        
        # Wait 2 minutes
        time.sleep(120)
```

### Monday 8 AM: CEO Briefing

```
□ Collect data from all sources
□ Generate executive summary
□ Calculate revenue vs target
□ List completed tasks
□ Identify bottlenecks
□ Create proactive suggestions
□ Define next week priorities
□ Save to Briefings/CEO_BRIEFING_YYYY-MM-DD.md
□ Notify CEO of briefing availability
```

**Implementation:**
```python
def monday_briefing_routine():
    """Generate Monday CEO briefing."""
    if datetime.now().weekday() == 0 and datetime.now().hour == 8:
        data = ceo_briefing_skill.collect_briefing_data()
        report = ceo_briefing_skill.generate_ceo_briefing(data)
        ceo_briefing_skill.save_ceo_briefing(report)
        log_info("CEO briefing generated")
```

### Sunday 11 PM: Weekly Audit

```
□ Run accounting_audit_skill
□ Audit bank transactions
□ Detect subscriptions
□ Flag unused subscriptions (30+ days)
□ Alert on cost increases (>20%)
□ Generate audit report
□ Save to Briefings/WEEKLY_AUDIT_YYYY-MM-DD.md
□ Create action items for findings
```

**Implementation:**
```python
def sunday_audit_routine():
    """Run weekly accounting audit."""
    if datetime.now().weekday() == 6 and datetime.now().hour == 23:
        audit_result = accounting_audit_skill.audit_bank_transactions()
        report = accounting_audit_skill.generate_audit_report(audit_result)
        accounting_audit_skill.save_audit_report(report)
        log_info("Weekly audit completed")
```

## Skill Quick Reference Cards

### Bronze Tier Skills

```
┌────────────────────────────────────────────────────────────┐
│ FILE WATCHER SKILL                                         │
├────────────────────────────────────────────────────────────┤
│ Purpose: Monitor Inbox, create action files                │
│ Trigger: New file in Inbox/                                │
│ Output: ACTION_*.md in Needs_Action/                       │
│ Key Rules: Priority detection, metadata creation           │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ VAULT MANAGER SKILL                                        │
├────────────────────────────────────────────────────────────┤
│ Purpose: Read/write vault files, update Dashboard          │
│ Trigger: Any file operation needed                         │
│ Output: Files in vault folders                             │
│ Key Rules: Path validation, overwrite protection           │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ TASK PROCESSOR SKILL                                       │
├────────────────────────────────────────────────────────────┤
│ Purpose: Execute tasks from Needs_Action/                  │
│ Trigger: ACTION files ready to process                     │
│ Output: Completed files in Done/                           │
│ Key Rules: Move to Done/, log completion                   │
└────────────────────────────────────────────────────────────┘
```

### Silver Tier Skills

```
┌────────────────────────────────────────────────────────────┐
│ EMAIL SKILL                                                │
├────────────────────────────────────────────────────────────┤
│ Purpose: Process Gmail, draft replies                      │
│ Trigger: New email received                                │
│ Output: Draft emails, action files                         │
│ Key Rules: Priority detection, known contacts              │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ WHATSAPP SKILL                                             │
├────────────────────────────────────────────────────────────┤
│ Purpose: Monitor WhatsApp, detect urgency                  │
│ Trigger: New WhatsApp message                              │
│ Output: Action files, draft responses                      │
│ Key Rules: Urgency keywords, priority levels               │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ LINKEDIN SKILL                                             │
├────────────────────────────────────────────────────────────┤
│ Purpose: Generate LinkedIn posts                           │
│ Trigger: Content request                                   │
│ Output: LinkedIn posts (150-300 words)                     │
│ Key Rules: Professional tone, approval required            │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ HITL SKILL (Human In The Loop)                             │
├────────────────────────────────────────────────────────────┤
│ Purpose: Manage approval workflows                         │
│ Trigger: Action requires approval                          │
│ Output: Approval files in Pending_Approval/                │
│ Key Rules: $100 threshold, new contacts, bulk sends        │
└────────────────────────────────────────────────────────────┘
```

### Gold Tier Skills

```
┌────────────────────────────────────────────────────────────┐
│ ODOO SKILL                                                 │
├────────────────────────────────────────────────────────────┤
│ Purpose: Financial operations via MCP                      │
│ Trigger: Invoice/payment needed                            │
│ Output: DRAFT invoices, financial summaries                │
│ Key Rules: DRAFT only, >$100 needs approval, never auto-post│
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ CEO BRIEFING SKILL                                         │
├────────────────────────────────────────────────────────────┤
│ Purpose: Generate Monday executive reports                 │
│ Trigger: Monday 8 AM                                       │
│ Output: Briefings/CEO_BRIEFING_YYYY-MM-DD.md               │
│ Key Rules: Check all data sources, structured format       │
└────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────┐
│ ERROR RECOVERY SKILL                                       │
├────────────────────────────────────────────────────────────┤
│ Purpose: Handle errors, retries, alerts                    │
│ Trigger: Any operation fails                               │
│ Output: Alert files, quarantine files                      │
│ Key Rules: Categorize errors, retry transient, alert human │
└────────────────────────────────────────────────────────────┘
```

## System Health Dashboard

### Key Metrics to Monitor

| Metric | Normal | Warning | Critical |
|--------|--------|---------|----------|
| Needs_Action count | < 20 | 20-50 | > 50 |
| Pending_Approval count | < 5 | 5-10 | > 10 |
| Alert count | 0 | 1-2 | > 2 |
| Error rate | < 1% | 1-5% | > 5% |
| Task completion rate | > 95% | 80-95% | < 80% |
| Disk space | > 10GB | 5-10GB | < 5GB |

### Health Check Commands

```python
# Full health check
health = error_recovery_skill.perform_health_check()

# Quick status
status = {
    'needs_action': count_files('Needs_Action'),
    'pending': count_files('Pending_Approval'),
    'alerts': count_files('Needs_Action', 'ALERT_*.md'),
    'done_today': count_files_today('Done'),
}
```

---

*MASTER SKILL - AI Employee System v1.0*
*Use this skill as your primary reference for all system operations*
