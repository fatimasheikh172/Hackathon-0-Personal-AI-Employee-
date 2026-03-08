#!/usr/bin/env python3
"""
Main Flask Web Server for Platinum Tier Cloud Deployment
Runs on Railway.app with background workers for Gmail and Orchestrator

Environment Variables Required:
    PORT: Server port (default: 8000)
    DRY_RUN: Enable dry run mode (default: true)
    GITHUB_TOKEN: GitHub personal access token
    GITHUB_REPO: GitHub repository (user/repo)
    GITHUB_BRANCH: GitHub branch (default: main)
    GMAIL_CHECK_INTERVAL: Gmail check interval in seconds (default: 120)
    ORCHESTRATOR_SYNC_INTERVAL: Orchestrator sync interval in seconds (default: 300)
"""

import os
import sys
import time
import threading
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, Response
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from environment
PORT = int(os.getenv("PORT", "8000"))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
GMAIL_CHECK_INTERVAL = int(os.getenv("GMAIL_CHECK_INTERVAL", "120"))
ORCHESTRATOR_SYNC_INTERVAL = int(os.getenv("ORCHESTRATOR_SYNC_INTERVAL", "300"))

# Local vault path for dashboard
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
LOGS_FOLDER = VAULT_PATH / "Logs"

# Ensure logs folder exists
LOGS_FOLDER.mkdir(parents=True, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_FOLDER / f"main_{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("main")

# Flask app
app = Flask(__name__)

# Background thread control
background_threads = {}
thread_stop_flags = {}


def log_message(message: str, level: str = "INFO"):
    """Log a message to file and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    
    if level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)
    
    print(log_entry)


def run_cloud_gmail_watcher():
    """
    Background thread: Run cloud Gmail watcher
    Writes files to GitHub repo instead of local vault
    """
    log_message("Starting cloud_gmail_watcher background thread...")
    
    try:
        # Import here to avoid blocking server startup
        from cloud_gmail_watcher import CloudGmailWatcher
        
        watcher = CloudGmailWatcher(
            github_token=GITHUB_TOKEN,
            github_repo=GITHUB_REPO,
            github_branch=GITHUB_BRANCH,
            check_interval=GMAIL_CHECK_INTERVAL,
            dry_run=DRY_RUN
        )
        
        log_message(f"Cloud Gmail Watcher initialized (interval: {GMAIL_CHECK_INTERVAL}s, dry_run: {DRY_RUN})")
        
        # Run the watcher (it has its own loop)
        watcher.run()
        
    except ImportError as e:
        log_message(f"cloud_gmail_watcher module not found: {e}", "ERROR")
    except Exception as e:
        log_message(f"cloud_gmail_watcher error: {e}", "ERROR")
        time.sleep(10)  # Wait before retry


def run_cloud_orchestrator():
    """
    Background thread: Run cloud orchestrator
    Reads/writes files from GitHub repo, creates drafts only
    """
    log_message("Starting cloud_orchestrator background thread...")
    
    try:
        # Import here to avoid blocking server startup
        from cloud_orchestrator import CloudOrchestrator
        
        orchestrator = CloudOrchestrator(
            github_token=GITHUB_TOKEN,
            github_repo=GITHUB_REPO,
            github_branch=GITHUB_BRANCH,
            sync_interval=ORCHESTRATOR_SYNC_INTERVAL,
            dry_run=DRY_RUN
        )
        
        log_message(f"Cloud Orchestrator initialized (interval: {ORCHESTRATOR_SYNC_INTERVAL}s, dry_run: {DRY_RUN})")
        
        # Run the orchestrator (it has its own loop)
        orchestrator.run()
        
    except ImportError as e:
        log_message(f"cloud_orchestrator module not found: {e}", "ERROR")
    except Exception as e:
        log_message(f"cloud_orchestrator error: {e}", "ERROR")
        time.sleep(10)  # Wait before retry


def start_background_thread(name: str, target_func):
    """Start a background thread with stop flag"""
    if name in background_threads and background_threads[name].is_alive():
        log_message(f"Thread {name} already running", "WARNING")
        return
    
    thread_stop_flags[name] = False
    background_threads[name] = threading.Thread(target=target_func, daemon=True)
    background_threads[name].start()
    log_message(f"Background thread '{name}' started")


def stop_background_thread(name: str):
    """Request a background thread to stop"""
    if name in thread_stop_flags:
        thread_stop_flags[name] = True
        log_message(f"Stop requested for thread '{name}'")


@app.route("/")
def index():
    """
    GET / - HTML Status Dashboard
    Shows system status, background threads, and recent activity
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Check thread status
    gmail_status = "Running" if (
        "gmail_watcher" in background_threads and 
        background_threads["gmail_watcher"].is_alive()
    ) else "Not Started"
    
    orchestrator_status = "Running" if (
        "orchestrator" in background_threads and 
        background_threads["orchestrator"].is_alive()
    ) else "Not Started"
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Employee Vault - Cloud Status</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2em;
        }}
        .header p {{
            margin: 10px 0 0;
            opacity: 0.9;
        }}
        .status-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            margin-top: 0;
            color: #333;
            font-size: 1.2em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .status-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
        }}
        .status-item:last-child {{
            border-bottom: none;
        }}
        .status-label {{
            color: #666;
        }}
        .status-value {{
            font-weight: 600;
        }}
        .status-running {{
            color: #28a745;
        }}
        .status-stopped {{
            color: #dc3545;
        }}
        .status-warning {{
            color: #ffc107;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
        }}
        .badge-success {{
            background: #28a745;
            color: white;
        }}
        .badge-info {{
            background: #17a2b8;
            color: white;
        }}
        .badge-warning {{
            background: #ffc107;
            color: #333;
        }}
        .config-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .config-table td {{
            padding: 8px;
            border-bottom: 1px solid #eee;
        }}
        .config-table tr:last-child td {{
            border-bottom: none;
        }}
        .config-key {{
            color: #666;
            font-family: monospace;
        }}
        .config-value {{
            font-family: monospace;
            color: #333;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 AI Employee Vault</h1>
        <p>Platinum Tier Cloud Deployment | Railway.app</p>
        <p style="margin-top: 10px; font-size: 0.9em;">
            <span class="badge badge-info">DRY_RUN: {DRY_RUN}</span>
            <span class="badge badge-success">GitHub Sync: {"Enabled" if GITHUB_TOKEN else "Not Configured"}</span>
        </p>
    </div>
    
    <div class="status-grid">
        <div class="card">
            <h2>📊 System Status</h2>
            <div class="status-item">
                <span class="status-label">Last Updated</span>
                <span class="status-value">{timestamp}</span>
            </div>
            <div class="status-item">
                <span class="status-label">Server Status</span>
                <span class="status-value status-running">● Online</span>
            </div>
            <div class="status-item">
                <span class="status-label">Port</span>
                <span class="status-value">{PORT}</span>
            </div>
            <div class="status-item">
                <span class="status-label">Environment</span>
                <span class="status-value {"status-warning" if DRY_RUN else "status-running"}">
                    {"🧪 Dry Run Mode" if DRY_RUN else "🚀 Production Mode"}
                </span>
            </div>
        </div>
        
        <div class="card">
            <h2>🔧 Background Workers</h2>
            <div class="status-item">
                <span class="status-label">Gmail Watcher</span>
                <span class="status-value {"status-running" if gmail_status == "Running" else "status-stopped"}">
                    ● {gmail_status}
                </span>
            </div>
            <div class="status-item">
                <span class="status-label">Check Interval</span>
                <span class="status-value">{GMAIL_CHECK_INTERVAL}s</span>
            </div>
            <div class="status-item">
                <span class="status-label">Orchestrator</span>
                <span class="status-value {"status-running" if orchestrator_status == "Running" else "status-stopped"}">
                    ● {orchestrator_status}
                </span>
            </div>
            <div class="status-item">
                <span class="status-label">Sync Interval</span>
                <span class="status-value">{ORCHESTRATOR_SYNC_INTERVAL}s</span>
            </div>
        </div>
        
        <div class="card">
            <h2>⚙️ Configuration</h2>
            <table class="config-table">
                <tr>
                    <td class="config-key">GITHUB_REPO</td>
                    <td class="config-value">{"✅ Set" if GITHUB_REPO else "❌ Not Set"}</td>
                </tr>
                <tr>
                    <td class="config-key">GITHUB_BRANCH</td>
                    <td class="config-value">{GITHUB_BRANCH}</td>
                </tr>
                <tr>
                    <td class="config-key">GMAIL_CHECK_INTERVAL</td>
                    <td class="config-value">{GMAIL_CHECK_INTERVAL}s</td>
                </tr>
                <tr>
                    <td class="config-key">ORCHESTRATOR_SYNC_INTERVAL</td>
                    <td class="config-value">{ORCHESTRATOR_SYNC_INTERVAL}s</td>
                </tr>
                <tr>
                    <td class="config-key">VAULT_PATH</td>
                    <td class="config-value">{VAULT_PATH}</td>
                </tr>
            </table>
        </div>
    </div>
    
    <div class="card">
        <h2>📖 Quick Links</h2>
        <ul>
            <li><a href="/health">/health</a> - JSON Health Check</li>
            <li><a href="/dashboard">/dashboard</a> - Markdown Dashboard</li>
            <li><a href="/logs">/logs</a> - System Logs (coming soon)</li>
        </ul>
    </div>
    
    <div class="footer">
        <p>AI Employee Vault v3.0 (Platinum Tier) | Deployed on Railway.app</p>
        <p>All actions are logged. DRY_RUN mode prevents destructive operations.</p>
    </div>
</body>
</html>"""
    
    return Response(html_content, mimetype="text/html")


@app.route("/health")
def health():
    """
    GET /health - JSON Health Check
    Returns system health status
    """
    timestamp = datetime.now().isoformat()
    
    # Check component health
    gmail_healthy = (
        "gmail_watcher" in background_threads and 
        background_threads["gmail_watcher"].is_alive()
    )
    
    orchestrator_healthy = (
        "orchestrator" in background_threads and 
        background_threads["orchestrator"].is_alive()
    )
    
    github_configured = bool(GITHUB_TOKEN and GITHUB_REPO)
    
    # Determine overall status
    if gmail_healthy and orchestrator_healthy:
        status = "healthy"
        status_code = 200
    elif gmail_healthy or orchestrator_healthy:
        status = "degraded"
        status_code = 200
    else:
        status = "starting"
        status_code = 200
    
    return jsonify({
        "status": status,
        "timestamp": timestamp,
        "version": "3.0.0-platinum",
        "dry_run": DRY_RUN,
        "components": {
            "gmail_watcher": {
                "status": "running" if gmail_healthy else "stopped",
                "check_interval": GMAIL_CHECK_INTERVAL
            },
            "orchestrator": {
                "status": "running" if orchestrator_healthy else "stopped",
                "sync_interval": ORCHESTRATOR_SYNC_INTERVAL
            },
            "github_sync": {
                "status": "configured" if github_configured else "not_configured",
                "repo": GITHUB_REPO or None,
                "branch": GITHUB_BRANCH
            }
        },
        "config": {
            "port": PORT,
            "vault_path": str(VAULT_PATH),
            "logs_path": str(LOGS_FOLDER)
        }
    }), status_code


@app.route("/dashboard")
def dashboard():
    """
    GET /dashboard - Return Dashboard.md contents
    Falls back to generated status if file doesn't exist
    """
    if DASHBOARD_FILE.exists():
        try:
            with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            return Response(content, mimetype="text/markdown")
        except Exception as e:
            logger.error(f"Error reading dashboard: {e}")
            return jsonify({
                "error": "Failed to read dashboard file",
                "message": str(e)
            }), 500
    else:
        # Generate fallback dashboard
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        fallback_content = f"""# AI Employee Dashboard (Platinum Tier - Cloud)

## System Status
- **Last Updated:** {timestamp}
- **Deployment:** Railway.app
- **Mode:** {"Dry Run" if DRY_RUN else "Production"}
- **Status:** Active

## Cloud Components

### Gmail Watcher (Cloud)
- **Status:** {"Running" if "gmail_watcher" in background_threads else "Not Started"}
- **Output:** GitHub Repository
- **Check Interval:** {GMAIL_CHECK_INTERVAL} seconds

### Orchestrator (Cloud)
- **Status:** {"Running" if "orchestrator" in background_threads else "Not Started"}
- **Sync Source:** GitHub Repository
- **Sync Interval:** {ORCHESTRATOR_SYNC_INTERVAL} seconds

### GitHub Sync
- **Repository:** {GITHUB_REPO or "Not Configured"}
- **Branch:** {GITHUB_BRANCH}
- **Token:** {"Configured" if GITHUB_TOKEN else "Not Configured"}

## Configuration

| Setting | Value |
|---------|-------|
| PORT | {PORT} |
| DRY_RUN | {DRY_RUN} |
| VAULT_PATH | {VAULT_PATH} |

---

*Generated by AI Employee Vault v3.0 (Platinum Tier)*
"""
        return Response(fallback_content, mimetype="text/markdown")


def main():
    """Main entry point"""
    log_message("=" * 60)
    log_message("AI Employee Vault - Platinum Tier Cloud Server")
    log_message("=" * 60)
    log_message(f"PORT: {PORT}")
    log_message(f"DRY_RUN: {DRY_RUN}")
    log_message(f"GITHUB_REPO: {GITHUB_REPO or 'Not configured'}")
    log_message(f"GITHUB_BRANCH: {GITHUB_BRANCH}")
    log_message("=" * 60)
    
    # Validate configuration
    if not GITHUB_TOKEN:
        log_message("WARNING: GITHUB_TOKEN not set. GitHub features will be disabled.", "WARNING")
    if not GITHUB_REPO:
        log_message("WARNING: GITHUB_REPO not set. GitHub features will be disabled.", "WARNING")
    
    # Start background threads
    start_background_thread("gmail_watcher", run_cloud_gmail_watcher)
    
    # Small delay to avoid race conditions
    time.sleep(2)
    
    start_background_thread("orchestrator", run_cloud_orchestrator)
    
    log_message("=" * 60)
    log_message(f"Starting Flask server on port {PORT}...")
    log_message("Press Ctrl+C to stop")
    log_message("=" * 60)
    
    # Run Flask server
    # For Railway, we need host='0.0.0.0'
    try:
        app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
    except Exception as e:
        log_message(f"Server error: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
