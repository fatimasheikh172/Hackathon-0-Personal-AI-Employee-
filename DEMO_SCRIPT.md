# Demo Script - Personal AI Employee Gold Tier

## 5-10 Minute Demo Walkthrough

**Presenter Notes:** This script guides you through a complete demo of the Gold Tier AI Employee system. Total time: 5-10 minutes.

---

## Pre-Demo Setup (Before Starting Timer)

1. Open Command Prompt at `F:\AI_Employee_Vault`
2. Have these windows ready:
   - File Explorer showing vault folder
   - Dashboard.md in text editor
   - Logs folder open
3. Ensure all services are stopped (clean demo)

---

## Step 1: Show Folder Structure (30 seconds)

**Script:**
"Let me start by showing you the vault structure where our AI Employee operates."

**Actions:**
```bash
dir F:\AI_Employee_Vault
```

**Point out:**
```
F:\AI_Employee_Vault\
├── Needs_Action/     ← Incoming tasks
├── Done/             ← Completed work
├── Plans/            ← Action plans
├── Logs/             ← Activity logs
├── Briefings/        ← CEO reports
├── Approved/         ← Approved actions
├── Pending_Approval/ ← Awaiting approval
└── [Python Scripts]  ← All automation
```

**Say:**
"This file-based architecture is simple, reliable, and easy to debug. All communication between components happens through these folders."

---

## Step 2: Show Dashboard.md (30 seconds)

**Script:**
"The Dashboard gives us real-time visibility into system status."

**Actions:**
```bash
type F:\AI_Employee_Vault\Dashboard.md
```

**Point out:**
- System Status: Active
- Completed Tasks count
- Recent Activity log
- All component statuses (Gmail, WhatsApp, Twitter, Instagram, etc.)
- Scheduler Status
- System Health Status

**Say:**
"Everything is monitored and logged. If any component fails, it shows up here immediately."

---

## Step 3: Demo Gmail Watcher (1 minute)

**Script:**
"Let me show you how the Gmail Watcher detects new emails."

**Actions:**
1. Send a test email to the configured Gmail account
2. Run the watcher:
   ```bash
   python gmail_watcher.py
   ```
3. Wait for detection (up to 2 minutes) OR show pre-detected email

**Show:**
```bash
dir Needs_Action\EMAIL_*.md
type Needs_Action\EMAIL_*.md
```

**Say:**
"When a new email arrives, the watcher downloads it as a markdown file with full metadata. The orchestrator will process this automatically."

---

## Step 4: Demo Plan Generator (1 minute)

**Script:**
"For every task detected, the system creates an action plan."

**Actions:**
```bash
dir Plans\
type Plans\PLAN_*.md
```

**Point out in plan:**
- Task description
- Priority level (High/Medium/Low)
- Action steps
- Source file reference

**Say:**
"Plans are automatically generated with priority levels. High priority plans get immediate attention. This ensures nothing falls through the cracks."

---

## Step 5: Demo HITL Approval (1 minute)

**Script:**
"Sensitive actions require human approval. Let me show you how this works."

**Actions:**
```bash
dir Pending_Approval\
type Pending_Approval\APPROVAL_*.md
```

**Explain the workflow:**
1. System detects sensitive content (payment, invoice, delete, etc.)
2. Creates approval request in Pending_Approval folder
3. Human reviews and moves file to:
   - **Approved/** → Action proceeds
   - **Rejected/** → Action cancelled

**Show approval file contents:**
- Action type
- Details
- Instructions for approval

**Say:**
"This Human-in-the-Loop system prevents costly mistakes. No payment or deletion happens without your explicit approval."

---

## Step 6: Demo Social Media Posting (1 minute)

**Script:**
"The system automatically posts to LinkedIn, Twitter, and Instagram on schedule."

**Show configurations:**
```bash
type .env | findstr POST
```

**Show recent posts:**
```bash
dir Instagram_Posts\
type Logs\linkedin_*.log
type Logs\twitter_activity_*.txt
```

**Explain schedule:**
- **LinkedIn:** Professional posts (configured interval)
- **Twitter:** Every 12 hours with hashtags
- **Instagram:** Every 24 hours with generated images

**Say:**
"Your social media presence is maintained automatically. Content is generated from business data and posted on schedule."

---

## Step 7: Demo CEO Briefing (1 minute)

**Script:**
"Every week, the system generates a comprehensive business briefing."

**Actions:**
```bash
dir Briefings\CEO_BRIEFING_*.md
type Briefings\CEO_BRIEFING_*.md
```

**Point out sections:**
- Executive Summary
- Revenue This Week (Income, Expenses, Net Profit)
- Goal Progress
- Top Income Sources
- Expense Breakdown
- Subscription Audit
- Tasks Completed
- Bottlenecks
- Proactive Suggestions
- Next Week Priorities

**Say:**
"This briefing gives you complete business visibility. Revenue, expenses, task completion, bottlenecks—all automatically analyzed and reported."

---

## Step 8: Demo Error Recovery (1 minute)

**Script:**
"The system automatically recovers from errors. Let me show you how."

**Actions:**
```bash
python error_recovery.py
```

**Show health check output:**
- All folders OK
- All scripts present
- Disk space check
- Log activity check
- Overall status: Good

**Show recovery features:**
```bash
type Logs\error_recovery_activity_*.txt
```

**Explain:**
- **with_retry()** - Exponential backoff for transient failures
- **recover_stuck_files()** - Quarantines files stuck >24 hours
- **cleanup_old_logs()** - Deletes logs >90 days old
- **restart_failed_process()** - Auto-restarts crashed processes

**Say:**
"The system is self-healing. Errors are automatically retried, stuck files are recovered, and crashed processes are restarted."

---

## Step 9: Show All Logs (30 seconds)

**Script:**
"Every action is logged for complete audit trail."

**Actions:**
```bash
dir Logs\
type Logs\watchdog_activity_*.txt
```

**Show log types:**
- `gmail_watcher_*.json` - Gmail activity
- `whatsapp_activity_*.txt` - WhatsApp messages
- `twitter_activity_*.txt` - Twitter posts
- `instagram_activity_*.txt` - Instagram posts
- `error_recovery_*.txt` - Recovery actions
- `watchdog_activity_*.txt` - Process monitoring

**Say:**
"90 days of complete audit trail. Every email, post, approval, and error is logged."

---

## Step 10: Show Complete System Running (1 minute)

**Script:**
"Let me start the complete system so you can see all components working together."

**Actions:**
```bash
F:\AI_Employee_Vault\startup.bat
```

**Show 7 windows opening:**
1. Gmail Watcher - Monitoring Gmail
2. File Watcher - Monitoring file system
3. HITL Monitor - Processing approvals
4. Master Scheduler - Running scheduled tasks
5. WhatsApp Watcher - Monitoring WhatsApp
6. Twitter Scheduler - Auto-posting tweets
7. Instagram Scheduler - Auto-posting images

**Say:**
"All seven services running simultaneously. This is your Gold Tier Digital FTE—working 24/7 to monitor communications, process tasks, post to social media, and generate business intelligence."

---

## Closing (30 seconds)

**Script:**
"To summarize what you've seen:"

**Quick recap:**
1. ✓ File-based architecture (simple, reliable)
2. ✓ Dashboard with real-time status
3. ✓ Gmail monitoring and processing
4. ✓ Automatic plan generation
5. ✓ HITL approval for sensitive actions
6. ✓ Social media automation (LinkedIn, Twitter, Instagram)
7. ✓ CEO briefings with business intelligence
8. ✓ Error recovery and self-healing
9. ✓ Complete audit logging
10. ✓ All services running together

**Final statement:**
"This is a Gold Tier Digital Full-Time Employee—autonomous, reliable, and safe. It works 24/7 so you don't have to."

**Thank you!**

---

## Troubleshooting Tips

### If Gmail Watcher Doesn't Detect Email
- Check credentials.json is valid
- Verify token.json exists
- Check Gmail API is enabled

### If Social Media Posts Fail
- Check sessions exist in *_session folders
- Verify credentials in .env file
- Instagram uses instagrapi (more reliable)

### If Dashboard Doesn't Update
- Check master_scheduler.py is running
- Verify write permissions on Dashboard.md

### If Approval Not Processing
- Check hitl_monitor.py is running
- Verify Pending_Approval folder has files
- Check Logs for errors

---

## Demo Checklist

Before demo:
- [ ] All services stopped
- [ ] Test email ready to send
- [ ] Dashboard.md shows recent activity
- [ ] Logs folder has recent entries
- [ ] Briefings folder has at least one report
- [ ] .env file configured with credentials
- [ ] All session files exist

During demo:
- [ ] Show folder structure
- [ ] Show Dashboard.md
- [ ] Demo Gmail detection
- [ ] Show Plan generation
- [ ] Show HITL approval workflow
- [ ] Show social media posts
- [ ] Show CEO briefing
- [ ] Show error recovery
- [ ] Show logs
- [ ] Start all services

After demo:
- [ ] Stop all services (Ctrl+C in each window)
- [ ] Answer questions
- [ ] Show ARCHITECTURE.md if asked for details

---

*Demo script for Gold Tier submission - Claude Code Hackathon 2026*
