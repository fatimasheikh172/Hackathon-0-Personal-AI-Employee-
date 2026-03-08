# AI Employee System - Platinum Tier

**Version:** 3.0 (Platinum Tier - Cloud)  
**Last Updated:** March 9, 2026  
**Hackathon:** Claude Code Hackathon 2026  
**Deployment:** Railway.app + Local Hybrid

---

## 🎯 Quick Start

```bash
# Local Development
pip install -r requirements.txt
python main.py

# Cloud Deployment (Railway.app)
# 1. Connect GitHub repo to Railway
# 2. Set environment variables
# 3. Deploy automatically
```

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Tier Evolution](#tier-evolution)
3. [Architecture](#architecture)
4. [Cloud Features](#cloud-features)
5. [Installation](#installation)
6. [Configuration](#configuration)
7. [Deployment](#deployment)
8. [Components](#components)
9. [API Reference](#api-reference)
10. [Troubleshooting](#troubleshooting)

---

## Overview

The **AI Employee System** is a comprehensive business automation platform that evolves from a local Gold Tier system to a **Platinum Tier Cloud-Native Digital Employee**. This autonomous system monitors multiple communication channels, processes incoming tasks, executes social media posting, and maintains business intelligence—all while requiring human approval for sensitive actions.

### What It Does

| Capability | Description |
|------------|-------------|
| 📧 **Email Management** | Monitor Gmail, create action items, draft responses |
| 💬 **WhatsApp Monitoring** | Keyword-based message detection and alerts |
| 📱 **Social Media** | Auto-post to Twitter/X, LinkedIn, Instagram |
| ☁️ **Cloud Sync** | Bidirectional sync between local vault and GitHub |
| 🤖 **AI Processing** | Claude Code integration for task reasoning |
| 👤 **Human-in-the-Loop** | Approval workflow for sensitive actions |
| 📊 **Executive Reports** | Automated CEO briefings with business intelligence |
| 🔄 **Error Recovery** | Automatic retry, graceful degradation, self-healing |

### Key Benefits

- **24/7 Monitoring** - Never miss an important email or message
- **Consistent Processing** - All incoming communications handled uniformly
- **Automated Social Presence** - Maintain active social media without manual effort
- **Business Intelligence** - Automated reporting and goal tracking
- **Safety First** - Human approval required for payments, deletions, sensitive actions
- **Cloud + Local** - Best of both worlds: cloud reliability with local control

---

## Tier Evolution

### Bronze Tier ✓ (Foundation)
- Basic Gmail monitoring
- File system watching
- Simple task processing
- Basic logging

### Silver Tier ✓ (Enhanced)
- Plan generation system
- HITL approval workflow
- LinkedIn auto-posting
- Error recovery with retry
- Process monitoring

### Gold Tier ✓ (Advanced)
- WhatsApp monitoring
- Twitter/X & Instagram posting
- Odoo ERP integration
- CEO briefing generation
- Master scheduler
- Ralph Wiggum loop pattern
- Advanced error recovery

### Platinum Tier ✓ (Cloud-Native)
- **Cloud deployment on Railway.app**
- **GitHub-based file sync**
- **Flask web dashboard**
- **Background workers**
- **REST API endpoints**
- **Health check monitoring**
- **DRY_RUN by default**
- **Environment-based configuration**

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        PLATINUM TIER ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CLOUD LAYER (Railway.app)                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │   Flask     │  │   Gmail     │  │   Cloud     │              │   │
│  │  │   Server    │  │  Watcher    │  │Orchestrator │              │   │
│  │  │  (main.py)  │  │   (Cloud)   │  │   (Cloud)   │              │   │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │   │
│  │         │                │                │                       │   │
│  │         └────────────────┼────────────────┘                       │   │
│  │                          │                                        │   │
│  │                          ▼                                        │   │
│  │              ┌─────────────────────────┐                         │   │
│  │              │    GitHub Repository     │                         │   │
│  │              │  (File Storage & Sync)   │                         │   │
│  │              └─────────────────────────┘                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│                              │ Sync                                     │
│                              ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    LOCAL LAYER (Your Machine)                    │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │   GitHub    │  │    HITL     │  │   Local     │              │   │
│  │  │    Sync     │  │   Monitor   │  │  Watchers   │              │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │   │
│  │                                                                  │   │
│  │  ┌──────────────────────────────────────────────────────────┐   │   │
│  │  │              Obsidian Vault / File System                 │   │   │
│  │  │  Needs_Action │ Pending_Approval │ Approved │ Done │ Logs │   │   │
│  │  └──────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
External Sources → Cloud Watchers → GitHub → Local Sync → Processing
                      │                │                    │
                      ▼                ▼                    ▼
                  Gmail API      Needs_Action/        Orchestrator
                  WhatsApp       Pending_Approval/    HITL Monitor
                  Social         Approved/            Local Actions
```

---

## Cloud Features

### 1. Flask Web Server (`main.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | HTML status dashboard |
| `/health` | GET | JSON health check |
| `/dashboard` | GET | Markdown dashboard content |

**Features:**
- Background threads for Gmail watcher and orchestrator
- Real-time status monitoring
- Environment-based configuration
- DRY_RUN mode by default

### 2. Cloud Gmail Watcher (`cloud_gmail_watcher.py`)

**Differences from Local:**
- Writes files to GitHub repo via GitHub API
- Uses `GITHUB_TOKEN` and `GITHUB_REPO` environment variables
- Creates files in `Needs_Action/` folder in GitHub
- Full error handling with retry logic
- Runs continuously, checks every 2 minutes

### 3. Cloud Orchestrator (`cloud_orchestrator.py`)

**Differences from Local:**
- Reads files from GitHub repository
- Writes approval requests to `Pending_Approval/` via GitHub API
- Creates drafts only - **NEVER sends directly**
- Syncs every 5 minutes
- All actions logged

### 4. GitHub Sync (`github_sync.py`)

**Bidirectional Sync:**
- **Pull:** Download new files from GitHub to local vault
- **Push:** Upload local changes to GitHub
- **Conflict Resolution:**
  - Cloud wins for `Needs_Action/`
  - Local wins for `Approved/` and `Rejected/`
- Runs every 5 minutes
- Skips: `.env`, `credentials.json`, `sessions/`

### 5. Cloud HITL Monitor (`cloud_hitl.py`)

**Human-in-the-Loop:**
- Monitors GitHub `Approved/` folder
- Creates signal files in local `Updates/` folder
- Tracks all pending approvals
- Notifies local system of status changes

---

## Installation

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| Python | 3.11+ | Core runtime |
| pip | Latest | Package management |
| Git | Latest | Version control |
| GitHub Account | - | Cloud storage |
| Railway Account | - | Cloud deployment (optional) |

### Local Setup

```bash
# Clone repository
git clone <repo-url>
cd AI_Employee_Vault

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run locally
python main.py
```

### Dependencies

```txt
# Core
python-dotenv
flask
requests

# GitHub
PyGithub

# Google APIs
google-auth
google-auth-oauthlib
google-api-python-client

# File watching
watchdog

# AI
anthropic
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | `8000` | Flask server port |
| `DRY_RUN` | No | `true` | Enable dry run mode |
| `GITHUB_TOKEN` | **Yes** | - | GitHub personal access token |
| `GITHUB_REPO` | **Yes** | - | GitHub repo (user/repo) |
| `GITHUB_BRANCH` | No | `main` | GitHub branch name |
| `GMAIL_CHECK_INTERVAL` | No | `120` | Gmail check interval (seconds) |
| `ORCHESTRATOR_SYNC_INTERVAL` | No | `300` | Orchestrator sync interval |
| `SYNC_INTERVAL` | No | `300` | GitHub sync interval |
| `HITL_CHECK_INTERVAL` | No | `120` | HITL monitor interval |
| `VAULT_PATH` | No | `F:\AI_Employee_Vault` | Local vault path |

### .env Example

```ini
# Server Configuration
PORT=8000
DRY_RUN=true

# GitHub Configuration (Required for Cloud)
GITHUB_TOKEN=ghp_your_personal_access_token
GITHUB_REPO=username/ai-employee-vault
GITHUB_BRANCH=main

# Service Intervals
GMAIL_CHECK_INTERVAL=120
ORCHESTRATOR_SYNC_INTERVAL=300
SYNC_INTERVAL=300
HITL_CHECK_INTERVAL=120

# Local Configuration
VAULT_PATH=F:\AI_Employee_Vault

# Gmail OAuth (Local only)
GMAIL_CREDENTIALS_PATH=F:\AI_Employee_Vault\credentials.json
```

### GitHub Token Setup

1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Click "Generate new token (classic)"
3. Select scopes: `repo`, `workflow`
4. Copy token and add to `.env` as `GITHUB_TOKEN`

---

## Deployment

### Railway.app Deployment

1. **Connect GitHub**
   - Login to Railway.app
   - Connect your GitHub repository

2. **Set Environment Variables**
   ```
   GITHUB_TOKEN=ghp_your_token
   GITHUB_REPO=username/repo
   DRY_RUN=true
   PORT=8000
   ```

3. **Deploy**
   - Railway auto-detects Python
   - Uses `Procfile`: `web: python main.py`
   - Uses `runtime.txt`: `python-3.12.0`

4. **Verify**
   - Access dashboard at `https://your-app.railway.app`
   - Check `/health` endpoint for status

### Local Development

```bash
# Start Flask server
python main.py

# Access dashboard
open http://localhost:8000

# Check health
curl http://localhost:8000/health
```

---

## Components

### Cloud Components

| File | Purpose | Interval |
|------|---------|----------|
| `main.py` | Flask web server + background workers | Continuous |
| `cloud_gmail_watcher.py` | Gmail → GitHub sync | Every 2 min |
| `cloud_orchestrator.py` | Process GitHub files | Every 5 min |
| `github_sync.py` | Bidirectional sync | Every 5 min |
| `cloud_hitl.py` | Approval monitoring | Every 2 min |

### Local Components (Gold Tier)

| File | Purpose | Interval |
|------|---------|----------|
| `gmail_watcher.py` | Local Gmail monitoring | Every 2 min |
| `orchestrator.py` | Master scheduler | Every 5 min |
| `whatsapp_watcher.py` | WhatsApp monitoring | Every 30 sec |
| `file_watcher.py` | File system monitoring | Continuous |
| `hitl_monitor.py` | Local HITL monitoring | Every 30 sec |

### Error Recovery

| File | Purpose | Check Interval |
|------|---------|----------------|
| `retry_handler.py` | Decorator-based retry | Per function |
| `graceful_degradation.py` | Health checker | Every 5 min |
| `watchdog_advanced.py` | Process monitoring | Every 60 sec |

---

## API Reference

### Health Check

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-09T12:00:00Z",
  "version": "3.0.0-platinum",
  "dry_run": true,
  "components": {
    "gmail_watcher": {
      "status": "running",
      "check_interval": 120
    },
    "orchestrator": {
      "status": "running",
      "sync_interval": 300
    },
    "github_sync": {
      "status": "configured",
      "repo": "username/repo",
      "branch": "main"
    }
  }
}
```

### Dashboard

```bash
GET /
GET /dashboard
```

Returns HTML status page or Markdown dashboard content.

---

## Folder Structure

```
F:\AI_Employee_Vault\
├── main.py                     # Flask server (Platinum)
├── cloud_gmail_watcher.py      # Cloud Gmail watcher
├── cloud_orchestrator.py       # Cloud orchestrator
├── github_sync.py              # Bidirectional sync
├── cloud_hitl.py               # HITL monitor
├── Procfile                    # Railway deployment
├── runtime.txt                 # Python version
├── requirements.txt            # Dependencies
├── .env                        # Configuration
│
├── Needs_Action/               # Pending tasks
├── Pending_Approval/           # Awaiting approval
├── Approved/                   # Approved actions
├── Rejected/                   # Rejected actions
├── Done/                       # Completed tasks
├── Updates/                    # Signal files from cloud
├── Logs/                       # System logs
├── Briefings/                  # CEO briefings
└── sessions/                   # Browser sessions
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Gmail Watcher shows "stopped" | Check `GITHUB_TOKEN` and `GITHUB_REPO` are set |
| Thread not starting | Check logs in `Logs/main_*.log` |
| GitHub sync failing | Verify token has `repo` scope |
| OAuth flow not working | Ensure `credentials.json` exists locally |
| Railway deployment fails | Check `Procfile` and environment variables |

### Log Files

| Log | Location |
|-----|----------|
| Main Server | `Logs/main_YYYY-MM-DD.log` |
| Gmail Watcher | `Logs/cloud_gmail_watcher_YYYY-MM-DD.log` |
| Orchestrator | `Logs/cloud_orchestrator_YYYY-MM-DD.log` |
| GitHub Sync | `Logs/github_sync_YYYY-MM-DD.log` |
| HITL Monitor | `Logs/cloud_hitl_YYYY-MM-DD.log` |

### Health Check Commands

```bash
# Check server health
curl http://localhost:8000/health

# View dashboard
curl http://localhost:8000/dashboard

# Check logs
tail -f Logs/main_*.log
```

---

## Security

### Credential Management

- **Never** hardcode credentials in code
- All secrets via environment variables only
- `.env` file excluded from version control
- GitHub token stored securely in Railway

### DRY_RUN Mode

- Enabled by default (`DRY_RUN=true`)
- Prevents destructive operations
- Logs actions without executing
- Disable only when ready for production

### Human-in-the-Loop

Sensitive actions require approval:
- Payments/Invoices
- Account deletions
- New contact communications
- Large transfers

---

## Testing

### Local Testing

```bash
# Run system test
python system_test.py

# Test retry handler
python retry_handler.py

# Test health checker
python graceful_degradation.py
```

### Cloud Testing

1. Set `DRY_RUN=true`
2. Deploy to Railway
3. Monitor `/health` endpoint
4. Check logs for errors

---

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with DRY_RUN enabled
4. Test locally
5. Submit pull request

---

## License

Internal use only - AI Employee System

---

## Acknowledgments

- **Claude Code Hackathon 2026** - Inspiration and platform
- **Railway.app** - Cloud deployment platform
- **GitHub** - Version control and cloud storage

---

*Generated: March 9, 2026*  
*Version: 3.0 (Platinum Tier)*  
*Status: Production Ready*
