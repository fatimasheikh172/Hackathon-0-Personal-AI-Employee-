# Personal AI Employee - Gold Tier Architecture

## System Overview

The Personal AI Employee is a **Gold Tier Digital Full-Time Employee (FTE)** system built for the Claude Code Hackathon. This autonomous digital worker monitors multiple communication channels, processes incoming tasks, generates action plans, executes social media posting, and maintains business intelligence—all while requiring human approval for sensitive actions.

### What It Does

- **Monitors** Gmail, WhatsApp, file system, and social media platforms
- **Processes** incoming emails, messages, and files automatically
- **Generates** action plans for all detected tasks
- **Posts** content to LinkedIn, Twitter, and Instagram on schedule
- **Creates** CEO briefings with business intelligence
- **Recovers** from errors automatically with graceful degradation
- **Requires** human approval for sensitive actions (payments, deletions, etc.)

### Why It Was Built

Modern businesses face information overload across multiple channels. This system provides:
- **24/7 monitoring** without human fatigue
- **Consistent processing** of all incoming communications
- **Automated social media presence** across platforms
- **Business intelligence** through automated reporting
- **Safety** through human-in-the-loop approval for sensitive actions
- **Reliability** through automatic error recovery

### How It Works

The system uses a **perception-reasoning-action** architecture:
1. **Watchers** (perception) monitor external sources for new content
2. **Orchestrator** (reasoning) processes detected items and creates plans
3. **MCP Servers** (action) execute approved tasks
4. **HITL Monitor** ensures human oversight for sensitive actions
5. **Error Recovery** maintains system reliability

---

## Tech Stack

| Technology | Purpose |
|------------|---------|
| **Python 3.14** | Core programming language |
| **Claude Code** | AI reasoning and task processing |
| **Playwright** | Browser automation (WhatsApp, Twitter) |
| **Instagrapi** | Instagram API (no browser needed) |
| **Gmail API** | Gmail integration |
| **Watchdog library** | File system monitoring |
| **Schedule library** | Task scheduling |
| **Pillow (PIL)** | Image generation for social posts |
| **psutil** | Process monitoring |
| **python-dotenv** | Environment variable management |

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SOURCES                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │  Gmail   │  │ WhatsApp │  │Instagram │  │ Twitter  │  │   File   │  │
│  │   API    │  │   Web    │  │   API    │  │   API    │  │  System  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
└───────┼─────────────┼─────────────┼─────────────┼─────────────┼────────┘
        │             │             │             │             │
        ▼             ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    PERCEPTION LAYER (WATCHERS)                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │gmail_watcher │ │whatsapp_watch│ │twitter_poster│ │file_watcher  │   │
│  │    .py       │ │    er.py     │ │    .py       │ │    .py       │   │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘   │
└─────────┼────────────────┼────────────────┼────────────────┼────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    OBSIDIAN VAULT / FILE SYSTEM                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │ Needs_Action │ │    Plans     │ │    Logs      │ │   Approved   │   │
│  │    Folder    │ │    Folder    │ │    Folder    │ │    Folder    │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │    Done      │ │  Pending_    │ │  Rejected    │ │  Briefings   │   │
│  │    Folder    │ │  Approval    │ │    Folder    │ │    Folder    │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      REASONING LAYER (CLAUDE CODE)                       │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      orchestrator.py                              │   │
│  │  - Scans Needs_Action folder                                      │   │
│  │  - Detects file types (email, file, approval)                     │   │
│  │  - Routes to appropriate processors                               │   │
│  │  - Creates approval requests for sensitive actions                │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     plan_generator.py                             │   │
│  │  - Creates Plan.md files for each task                            │   │
│  │  - Assigns priority levels (High/Medium/Low)                      │   │
│  │  - Defines action steps                                           │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      ralph_wiggum.py                              │   │
│  │  - Implements retry loop pattern                                  │   │
│  │  - Ensures 100% task completion                                   │   │
│  │  - Tracks iterations and logs progress                            │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ACTION LAYER (MCP SERVERS)                          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │
│  │email_mcp_    │ │linkedin_     │ │twitter_      │ │instagram_    │   │
│  │server.py     │ │poster.py     │ │poster.py     │ │instagrapi.py │   │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
          │                │                │                │
          ▼                ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         HUMAN IN THE LOOP                                │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                     hitl_monitor.py                                │   │
│  │  - Monitors Pending_Approval folder                               │   │
│  │  - Notifies human of required approvals                           │   │
│  │  - Processes Approved/Rejected decisions                          │   │
│  │  - Logs all approval decisions                                    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                                 │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    master_scheduler.py                            │   │
│  │  - Schedules all periodic tasks                                   │   │
│  │  - Runs health checks every 30 minutes                            │   │
│  │  - Recovers stuck files hourly                                    │   │
│  │  - Cleans old logs daily                                          │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                   error_recovery.py                               │   │
│  │  - with_retry() with exponential backoff                          │   │
│  │  - check_system_health()                                          │   │
│  │  - graceful_degradation()                                         │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                  watchdog_advanced.py                             │   │
│  │  - Monitors critical processes                                    │   │
│  │  - Auto-restarts failed processes                                 │   │
│  │  - Tracks restart frequency                                       │   │
│  └──────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Component Description

### Watchers (Perception Layer)

#### gmail_watcher.py
**Purpose:** Monitor Gmail for new emails

**How it works:**
1. Authenticates with Gmail API using OAuth2
2. Saves session token for reuse
3. Polls inbox every 2 minutes for new messages
4. Downloads new emails as markdown files
5. Saves to Needs_Action folder with metadata

**Key features:**
- OAuth2 authentication with token persistence
- Processes emails in batches
- Creates structured markdown with headers
- Logs all activity

#### file_watcher.py
**Purpose:** Monitor file system for new files

**How it works:**
1. Uses Watchdog library to monitor Inbox folder
2. Detects new files (txt, pdf, docx, etc.)
3. Creates metadata file with file info
4. Moves original to Files folder
5. Creates action file in Needs_Action

**Key features:**
- Real-time file system monitoring
- Supports multiple file types
- Extracts metadata (size, type, date)
- Handles large files efficiently

#### whatsapp_watcher.py
**Purpose:** Monitor WhatsApp Web for messages

**How it works:**
1. Uses Playwright to automate browser
2. Logs into WhatsApp Web (saves session)
3. Scans for unread messages every 30 seconds
4. Detects keywords (urgent, asap, invoice, payment)
5. Creates action files for matching messages

**Key features:**
- Session persistence (no repeated QR scans)
- Keyword-based filtering
- Priority assignment (High/Medium/Low)
- Anti-detection measures

### Core Processing

#### orchestrator.py
**Purpose:** Main processing loop for all tasks

**How it works:**
1. Scans Needs_Action folder every 5 minutes
2. Detects file type from filename/frontmatter
3. Routes to appropriate processor:
   - EMAIL_* → Email processor
   - FILE_* → File processor
   - APPROVAL_* → Approval processor
4. Checks for sensitive content requiring approval
5. Moves processed files to Done folder

**Key features:**
- Type detection from filename and frontmatter
- Sensitive content detection (payment, invoice, delete)
- Approval routing for sensitive actions
- Retry logic with max attempts

#### plan_generator.py
**Purpose:** Generate action plans for tasks

**How it works:**
1. Scans Needs_Action for unprocessed files
2. Analyzes content for priority indicators
3. Creates Plan.md with:
   - Task description
   - Priority level (High/Medium/Low)
   - Action steps
   - Required approvals
4. Saves to Plans folder

**Key features:**
- Automatic priority detection
- Structured plan format
- Links to source files
- Status tracking

#### ralph_wiggum.py
**Purpose:** Implement retry loop pattern for reliability

**How it works:**
1. Creates task file in Active_Tasks folder
2. Runs work function in loop
3. After each iteration:
   - Checks if task complete
   - Increments iteration counter
   - Logs progress
4. Continues until TASK_COMPLETE or max iterations

**Key features:**
- Exponential backoff retry
- Iteration tracking
- Progress logging
- Max iteration protection

### Social Media

#### linkedin_poster.py
**Purpose:** Automated LinkedIn posting

**How it works:**
1. Reads linkedin_templates.md for content ideas
2. Generates professional posts
3. Uses Playwright to post to LinkedIn
4. Saves session for reuse
5. Logs all posts

**Key features:**
- Template-based content generation
- Session persistence
- Professional tone enforcement
- Activity logging

#### twitter_poster.py
**Purpose:** Automated Twitter/X posting

**How it works:**
1. Generates tweet content from business data
2. Uses Playwright for browser automation
3. Logs into Twitter (saves session)
4. Posts tweet with hashtags
5. Handles verification challenges

**Key features:**
- 280 character limit enforcement
- Hashtag generation
- Session persistence
- 2FA support

#### instagram_instagrapi.py
**Purpose:** Automated Instagram posting

**How it works:**
1. Uses instagrapi library (no browser)
2. Creates text images with Pillow
3. Generates captions with hashtags
4. Posts via Instagram API
5. Saves session for reuse

**Key features:**
- Direct API (more reliable than browser)
- Image generation (1080x1080)
- Caption generation
- Session persistence

### Business Intelligence

#### ceo_briefing.py
**Purpose:** Generate weekly business audit

**How it works:**
1. Reads Bank_Transactions.md for financial data
2. Reads Dashboard.md for activity metrics
3. Reads Business_Goals.md for targets
4. Calculates:
   - Revenue this week
   - Expenses this week
   - Net profit
   - Goal progress
5. Generates briefing with suggestions

**Key features:**
- Financial analysis
- Goal tracking
- Proactive suggestions
- Professional formatting

#### email_mcp_server.py
**Purpose:** Email operations server

**How it works:**
1. Provides email functions via MCP protocol
2. draft_email() - Creates Gmail drafts
3. send_email() - Sends with approval check
4. search_emails() - Searches Gmail
5. reply_to_email() - Creates reply drafts

**Key features:**
- Approval checking before send
- Draft creation
- Search functionality
- Complete logging

### Safety & Recovery

#### hitl_monitor.py
**Purpose:** Human-in-the-loop approval system

**How it works:**
1. Monitors Pending_Approval folder every 30 seconds
2. When new file detected:
   - Reads content
   - Prints notification to terminal
   - Logs to Logs folder
   - Updates Dashboard.md
3. Monitors Approved folder:
   - Processes approved actions
   - Moves to Done folder
4. Monitors Rejected folder:
   - Logs rejections
   - Moves to Done folder

**Key features:**
- Real-time approval monitoring
- Clear terminal notifications
- Complete audit trail
- Dashboard integration

#### error_recovery.py
**Purpose:** Automatic error recovery

**How it works:**
1. ErrorRecovery class with methods:
   - with_retry() - Exponential backoff
   - check_system_health() - Health monitoring
   - recover_stuck_files() - File quarantine
   - cleanup_old_logs() - Log cleanup
   - restart_failed_process() - Process restart
   - graceful_degradation() - Fallback handling

**Key features:**
- Exponential backoff retry
- System health monitoring
- Automatic file quarantine
- Process auto-restart
- Graceful degradation

#### watchdog_advanced.py
**Purpose:** Process monitoring and auto-restart

**How it works:**
1. Monitors critical processes every 60 seconds:
   - gmail_watcher.py
   - file_watcher.py
   - orchestrator.py
   - master_scheduler.py
   - hitl_monitor.py
2. If process not running:
   - Waits 10 seconds
   - Restarts process
   - Logs restart
3. Tracks restart frequency
4. Alerts if >3 restarts/hour

**Key features:**
- Process monitoring via psutil
- Auto-restart capability
- Restart frequency tracking
- Alert system

### Scheduling

#### master_scheduler.py
**Purpose:** Central task scheduling

**Scheduled jobs:**
| Frequency | Job | Description |
|-----------|-----|-------------|
| Every 2 min | Check Needs_Action | Process new files |
| Every 5 min | Generate Plans | Create action plans |
| Every 5 min | Check Approvals | Process HITL decisions |
| Every 10 min | Ralph Wiggum | Ensure task completion |
| Every 30 min | Health Check | System health monitoring |
| Every 1 hour | Check Emails | Gmail monitoring |
| Every 1 hour | Recover Files | Quarantine stuck files |
| Every 12 hours | Twitter Post | Auto-post tweets |
| Every 24 hours | Instagram Post | Auto-post images |
| Daily 8AM | Daily Briefing | Generate daily report |
| Daily Midnight | Log Cleanup | Delete old logs |
| Monday 8AM | CEO Briefing | Weekly business audit |
| Sunday 9PM | Weekly Report | Weekly summary |

---

## Folder Structure

```
F:\AI_Employee_Vault\
├── Needs_Action/          # Incoming tasks to process
├── Done/                  # Completed tasks archive
├── Inbox/                 # Raw incoming files
├── Logs/                  # System activity logs
├── Plans/                 # Generated action plans
├── Briefings/             # CEO briefings and health reports
├── Archive/               # Old files (>7 days from Done)
├── Approved/              # Awaiting approval processing
├── Rejected/              # Rejected approvals
├── Pending_Approval/      # Pending human approval
├── whatsapp_session/      # WhatsApp session storage
├── twitter_session/       # Twitter session storage
├── instagram_session/     # Instagram session storage
├── Instagram_Posts/       # Generated Instagram images
├── Active_Tasks/          # Ralph Wiggum active tasks
├── Quarantine/            # Stuck files (>24h in Needs_Action)
├── Accounting/            # Financial records
└── [Python Scripts]       # All .py files
```

### Folder Purposes

| Folder | Purpose | Retention |
|--------|---------|-----------|
| **Needs_Action/** | Incoming tasks awaiting processing | Until processed |
| **Done/** | Completed tasks | 7 days then Archive |
| **Inbox/** | Raw incoming files | Until processed |
| **Logs/** | System activity logs | 90 days |
| **Plans/** | Generated action plans | Indefinite |
| **Briefings/** | CEO briefings, health reports | Indefinite |
| **Archive/** | Old completed tasks | Indefinite |
| **Approved/** | Approved actions awaiting processing | Until processed |
| **Rejected/** | Rejected actions | Until archived |
| **Pending_Approval/** | Awaiting human approval | Until decision |
| **whatsapp_session/** | WhatsApp auth session | Indefinite |
| **twitter_session/** | Twitter auth session | Indefinite |
| **instagram_session/** | Instagram auth session | Indefinite |
| **Instagram_Posts/** | Generated post images | Indefinite |
| **Active_Tasks/** | Ralph Wiggum active tasks | Until complete |
| **Quarantine/** | Stuck files recovery | Indefinite |
| **Accounting/** | Financial records | Indefinite |

---

## Security Architecture

### Credential Storage
- All credentials stored in `.env` file
- File excluded from version control (.gitignore)
- Loaded via python-dotenv at runtime
- Never hardcoded in scripts

### Data Locality
- All data stored locally in vault folder
- Session tokens stored locally (encrypted by provider)
- Logs stored locally with 90-day retention
- No cloud storage except provider APIs (Gmail, Instagram, etc.)

### HITL Approval
Sensitive actions require human approval:
- **Payments/Invoices:** Always requires approval
- **Emails to new contacts:** Requires approval
- **Deletions:** Requires approval
- **Large transfers:** Requires approval

Keywords that trigger approval:
- payment, invoice, urgent, asap
- delete, remove, cancel
- send money, transfer, wire
- bank, refund

### Audit Logging
- All actions logged to Logs folder
- JSON logs with timestamps
- Text logs for human readability
- 90-day retention with automatic cleanup
- Health reports saved to Briefings folder

---

## Hackathon Tier Achievement

### Bronze Tier ✓
- Basic Gmail monitoring
- File system watching
- Simple task processing
- Basic logging

### Silver Tier ✓
- Plan generation system
- HITL approval workflow
- LinkedIn auto-posting
- Error recovery system
- Process monitoring

### Gold Tier ✓
- WhatsApp monitoring
- Twitter auto-posting
- Instagram auto-posting
- CEO briefing generation
- Email MCP server
- Ralph Wiggum loop pattern
- Advanced error recovery
- Watchdog process monitoring
- Comprehensive scheduling

---

## Lessons Learned

### Challenges Faced

1. **Instagram Browser Automation Unreliable**
   - Playwright browser automation for Instagram was flaky
   - Frequent detection and blocking
   - Solution: Switched to instagrapi library (direct API)

2. **Session Management**
   - Repeated logins triggered security alerts
   - Solution: Implemented session persistence for all platforms

3. **File Processing Loops**
   - Single-pass processing missed files
   - Solution: Ralph Wiggum loop pattern ensures 100% completion

4. **Process Crashes**
   - Watchers would crash silently
   - Solution: Watchdog with auto-restart and alerting

### What Worked Well

1. **File-Based Communication**
   - Simple, reliable, debuggable
   - No database dependencies
   - Easy to inspect and modify

2. **HITL Pattern**
   - Prevents costly mistakes
   - Builds trust with users
   - Clear audit trail

3. **Exponential Backoff**
   - Handles transient failures gracefully
   - Prevents API rate limiting
   - Self-healing system

---

## Future Improvements

### Platinum Tier Features
- Cloud deployment (AWS/Azure)
- Web dashboard for monitoring
- Mobile app for approvals
- Voice interface for queries
- Odoo ERP integration
- Advanced analytics dashboard
- Multi-tenant support

### Cloud Deployment
- Docker containers for each service
- Kubernetes orchestration
- Cloud storage for vault
- Managed database for logs
- Load balancing for watchers

### Odoo Integration
- Invoice processing
- Customer communication
- Project management
- Accounting sync
- CRM integration

---

## Setup Instructions

### Prerequisites
- Python 3.14
- Node.js (for MCP servers)
- Gmail API credentials
- Instagram account
- Twitter account
- LinkedIn account

### Installation Steps

1. **Clone repository**
   ```bash
   git clone <repo-url>
   cd AI_Employee_Vault
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers**
   ```bash
   playwright install chromium
   ```

4. **Configure environment**
   - Copy `.env.example` to `.env`
   - Edit `.env` with your credentials

5. **First-time setup**
   - Run each social media script once to authenticate
   - Complete 2FA if required
   - Sessions will be saved for future use

### Configuration

Edit `.env` file with your credentials:
```
VAULT_PATH=F:\AI_Employee_Vault
GMAIL_CREDENTIALS=path/to/credentials.json
INSTAGRAM_EMAIL=your@email.com
INSTAGRAM_PASSWORD=your_password
TWITTER_EMAIL=your@email.com
TWITTER_PASSWORD=your_password
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=your_password
```

### How to Run

**Start all services:**
```bash
F:\AI_Employee_Vault\startup.bat
```

**Start individual services:**
```bash
python gmail_watcher.py
python file_watcher.py
python master_scheduler.py
python hitl_monitor.py
```

**Monitor logs:**
```bash
tail -f Logs/watchdog_activity_*.txt
```

---

*Documentation generated for Gold Tier submission - Claude Code Hackathon 2026*
