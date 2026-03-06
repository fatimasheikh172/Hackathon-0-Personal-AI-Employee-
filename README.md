# AI Employee System - Gold Tier

**Version:** 2.0 (Gold Tier)  
**Last Updated:** March 2026  
**Vault Path:** `F:\AI_Employee_Vault`

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Master Schedule](#master-schedule)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Usage](#usage)
8. [Error Recovery](#error-recovery)
9. [Testing](#testing)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The Gold Tier AI Employee System is a comprehensive business automation platform that integrates:

- **Email Management** (Gmail)
- **Messaging** (WhatsApp)
- **Social Media** (Twitter/X, LinkedIn, Instagram)
- **ERP Integration** (Odoo)
- **File Monitoring** (Watchdog)
- **Executive Reporting** (CEO Briefings)
- **Error Recovery** (Retry + Graceful Degradation)

### Key Features

| Feature | Description |
|---------|-------------|
| 📧 Gmail Integration | Auto-process emails to Needs_Action folder |
| 💬 WhatsApp Monitoring | Keyword-based message detection |
| 📱 Social Media | Multi-platform posting with DRY_RUN |
| 💰 Odoo ERP | Real financial data integration |
| 📊 CEO Briefings | Automated Monday morning reports |
| 🔄 Error Recovery | Automatic retry with exponential backoff |
| 🛡️ Graceful Degradation | Queue locally when services down |
| 📅 Master Scheduler | Coordinated multi-component execution |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AI Employee Gold Tier                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Gmail     │  │  WhatsApp   │  │   File      │             │
│  │  Watcher    │  │  Watcher    │  │  Watcher    │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│         └────────────────┼────────────────┘                     │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Master Orchestrator                         │   │
│  │  (Schedule: 5min/2min/1hr/Mon8AM/Sun11PM)               │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
│         ┌────────────────┼────────────────┐                     │
│         │                │                │                     │
│         ▼                ▼                ▼                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Odoo      │  │   Social    │  │    CEO      │             │
│  │    MCP      │  │  Scheduler  │  │  Briefing   │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Error Recovery System                       │   │
│  │  • retry_handler.py (decorator-based)                   │   │
│  │  • graceful_degradation.py (health checker)             │   │
│  │  • watchdog_advanced.py (process monitoring)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Components

### Core Components

| File | Purpose | Schedule |
|------|---------|----------|
| `orchestrator.py` | Master scheduler | Continuous |
| `gmail_watcher.py` | Gmail monitoring | Every 2 min |
| `whatsapp_watcher.py` | WhatsApp monitoring | Every 30 sec |
| `file_watcher.py` | File system monitoring | Continuous |
| `odoo_mcp_server.py` | Odoo ERP integration | On demand |
| `ceo_briefing.py` | Executive reports | Mon 8 AM |

### Social Media Components

| File | Platform | Rate Limit |
|------|----------|------------|
| `twitter_manager.py` | Twitter/X | 5/hour |
| `linkedin_manager.py` | LinkedIn | 3/day |
| `instagram_manager.py` | Instagram | 5/day |
| `social_scheduler.py` | Multi-platform | Every hour |
| `social_content_generator.py` | Content creation | On demand |

### Error Recovery Components

| File | Purpose | Check Interval |
|------|---------|----------------|
| `retry_handler.py` | Decorator-based retry | Per function |
| `graceful_degradation.py` | Health checker | Every 5 min |
| `watchdog_advanced.py` | Process monitoring | Every 60 sec |

---

## Master Schedule

| Task | Interval | Description |
|------|----------|-------------|
| **Needs_Action Scan** | Every 5 min | Process pending files |
| **Gmail Check** | Every 2 min | Check for new emails |
| **Social Media Check** | Every 1 hour | Post pending content |
| **CEO Briefing** | Monday 8 AM | Generate executive report |
| **Weekly Audit** | Sunday 11 PM | System health audit |

---

## Installation

### Prerequisites

- Python 3.13+
- Playwright (for WhatsApp/Social)
- Google OAuth credentials (for Gmail)
- Odoo ERP access (optional)

### Install Dependencies

```bash
cd F:\AI_Employee_Vault
pip install -r requirements.txt
```

### Required Packages

```
playwright
python-dotenv
google-api-python-client
google-auth-oauthlib
google-auth-httplib2
psutil
pillow
```

---

## Configuration

### .env File

```ini
# Vault Configuration
VAULT_PATH=F:\AI_Employee_Vault
DRY_RUN=true
CHECK_INTERVAL=120
MAX_ACTIONS_PER_HOUR=20

# Gmail
CHECK_INTERVAL=120

# WhatsApp
WHATSAPP_SESSION_PATH=F:\AI_Employee_Vault\whatsapp_session
WHATSAPP_CHECK_INTERVAL=30
WHATSAPP_KEYWORDS=urgent,asap,invoice,payment,help,price,quote,order

# Twitter
TWITTER_EMAIL=your_twitter_email
TWITTER_PASSWORD=your_twitter_password
TWITTER_POST_INTERVAL=12

# LinkedIn
LINKEDIN_EMAIL=your_linkedin_email
LINKEDIN_PASSWORD=your_linkedin_password
LINKEDIN_POST_INTERVAL=24

# Instagram
INSTAGRAM_EMAIL=your_instagram_email
INSTAGRAM_PASSWORD=your_instagram_password
INSTAGRAM_POST_INTERVAL=24

# Odoo ERP
ODOO_URL=http://localhost:8069
ODOO_DB=aiemploy
ODOO_USERNAME=your_odoo_email
ODOO_PASSWORD=your_odoo_password

# API Keys
GEMINI_API_KEY=your_gemini_api_key
```

### Credentials

- **Google OAuth:** Place `credentials.json` in vault root
- **Session Files:** Auto-created in `sessions/` folder

---

## Usage

### Start Master Orchestrator

```bash
cd F:\AI_Employee_Vault
python orchestrator.py
```

### Run Individual Components

```bash
# Gmail Watcher
python gmail_watcher.py

# WhatsApp Watcher
python whatsapp_watcher.py

# CEO Briefing (manual generation)
python ceo_briefing.py

# Social Scheduler (one cycle)
python social_scheduler.py --test --once

# System Health Check
python graceful_degradation.py
```

### DRY_RUN Mode

All components support DRY_RUN mode for safe testing:

```ini
# In .env file
DRY_RUN=true
```

Or use `--test` flag:

```bash
python twitter_manager.py --test --topic "Test tweet"
```

---

## Error Recovery

### Retry Handler

```python
from retry_handler import with_retry, TransientError, AuthError

@with_retry(max_attempts=3, base_delay=1.0)
def fetch_data():
    # Auto-retries on transient errors
    pass

@with_retry(
    max_attempts=5,
    on_retry=lambda a, e, d: print(f"Retry {a}: {e}"),
    on_failure=lambda e: log_error(e)
)
def call_api():
    pass
```

### Error Categories

| Category | Description | Retryable |
|----------|-------------|-----------|
| `TransientError` | Network timeout, service unavailable | ✅ Yes |
| `AuthError` | Invalid credentials, token expired | ❌ No |
| `LogicError` | Invalid input, validation failed | ❌ No |
| `DataError` | Data corruption, parsing error | ⚠️ Conditional |
| `SystemError` | Disk full, file not found | ⚠️ Conditional |

### Graceful Degradation

When services are unavailable:

| Service | Fallback Action |
|---------|-----------------|
| Gmail | Queue emails locally |
| Odoo | Log transactions to `local_transactions.json` |
| WhatsApp | Save missed messages to `missed_messages.md` |

---

## Testing

### Run Full System Test

```bash
cd F:\AI_Employee_Vault
python system_test.py
```

### Test Results

Results saved to `TEST_REPORT.md` with:

- Component status
- Configuration validation
- Import/syntax checks
- Integration tests

### Individual Component Tests

```bash
# Test retry handler
python retry_handler.py

# Test health checker
python -c "from graceful_degradation import HealthChecker; h = HealthChecker(); h.run_full_health_check()"
```

---

## Folder Structure

```
F:\AI_Employee_Vault\
├── .env                          # Configuration
├── credentials.json              # Google OAuth
├── Dashboard.md                  # System dashboard
├── orchestrator.py               # Master scheduler
├── gmail_watcher.py              # Gmail monitoring
├── whatsapp_watcher.py           # WhatsApp monitoring
├── file_watcher.py               # File monitoring
├── odoo_mcp_server.py            # Odoo integration
├── ceo_briefing.py               # CEO reports
├── system_test.py                # System tests
│
├── retry_handler.py              # Retry decorator
├── graceful_degradation.py       # Health checker
├── watchdog_advanced.py          # Process monitor
│
├── twitter_manager.py            # Twitter/X
├── linkedin_manager.py           # LinkedIn
├── instagram_manager.py          # Instagram
├── social_scheduler.py           # Social scheduler
├── social_content_generator.py   # Content generator
│
├── Needs_Action/                 # Pending items
├── Done/                         # Completed items
├── Pending_Approval/             # Awaiting approval
├── Briefings/                    # CEO briefings
├── Logs/                         # System logs
├── sessions/                     # Browser sessions
│   ├── twitter_session/
│   ├── linkedin_session/
│   └── instagram_session/
└── Social_Content/
    ├── pending/
    ├── posted/
    ├── drafts/
    └── failed/
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Gmail OAuth fails | Re-run OAuth flow, check credentials.json |
| WhatsApp QR not showing | Check Playwright installation, browser path |
| Odoo connection fails | Verify URL, database, credentials in .env |
| Social media login fails | Clear session files, re-authenticate |

### Log Files

- **Daily Logs:** `Logs/<component>_YYYY-MM-DD.json`
- **Activity Logs:** `Logs/<component>_activity_YYYY-MM-DD.txt`
- **Test Report:** `TEST_REPORT.md`

### Health Check

```bash
python graceful_degradation.py
# Saves to: system_health.md
```

---

## License

Internal use only - Gold Tier Personal AI Employee System

---

*Generated: March 2026*  
*Version: 2.0 (Gold Tier)*
"# Hackathon-0-Personal-AI-Employee-" 
