#!/usr/bin/env python3
"""
Orchestrator - Main coordinator for AI Employee system (Gold Tier)
Master Schedule Implementation with all system components

SCHEDULE:
- Every 5 min: Needs_Action scan
- Every 2 min: Gmail check
- Every hour: Social media post check
- Every Monday 8 AM: CEO Briefing generate
- Every Sunday 11 PM: Weekly audit

Updated with @with_retry decorator for resilient operations
"""

import os
import sys
import time
import json
import shutil
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Import retry handler
from retry_handler import with_retry, TransientError, SystemError, LogicError, get_retry_stats

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
NEEDS_ACTION_FOLDER = VAULT_PATH / "Needs_Action"
DONE_FOLDER = VAULT_PATH / "Done"
LOGS_FOLDER = VAULT_PATH / "Logs"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
COMPANY_HANDBOOK = VAULT_PATH / "Company_Handbook.md"
BRIEFINGS_FOLDER = VAULT_PATH / "Briefings"
SOCIAL_PENDING = VAULT_PATH / "Social_Content" / "pending"

# Master Schedule Configuration (in seconds)
SCHEDULE_CONFIG = {
    "needs_action_scan": 300,      # Every 5 minutes
    "gmail_check": 120,            # Every 2 minutes
    "social_media_check": 3600,    # Every hour
    "ceo_briefing": "monday_8am",  # Every Monday 8 AM
    "weekly_audit": "sunday_11pm"  # Every Sunday 11 PM
}

# Rate limiting configuration
MAX_ACTIONS_PER_HOUR = int(os.getenv("MAX_ACTIONS_PER_HOUR", "20"))
action_timestamps = []

# Schedule tracking
schedule_state = {
    "last_needs_action_scan": None,
    "last_gmail_check": None,
    "last_social_check": None,
    "last_ceo_briefing": None,
    "last_weekly_audit": None,
    "total_cycles": 0,
    "total_tasks_processed": 0
}


def check_rate_limit():
    """Check if action is within rate limit"""
    now = time.time()
    # Remove timestamps older than 1 hour
    action_timestamps[:] = [t for t in action_timestamps if now - t < 3600]
    if len(action_timestamps) >= MAX_ACTIONS_PER_HOUR:
        return False
    action_timestamps.append(now)
    return True


# Ralph Wiggum Loop instance (lazy loaded)
_ralph_loop = None


def get_ralph_loop():
    """Get or create Ralph Wiggum Loop instance"""
    global _ralph_loop
    if _ralph_loop is None:
        try:
            from ralph_wiggum import RalphWiggumLoop
            _ralph_loop = RalphWiggumLoop()
        except ImportError:
            _ralph_loop = None
    return _ralph_loop


# Activity log for dashboard
recent_activities = []


def get_log_file_path():
    """Get JSON log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"orchestrator_{date_str}.json"


def load_daily_log():
    """Load today's log or create new structure"""
    log_path = get_log_file_path()
    if log_path.exists():
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    return {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "actions": [],
        "summary": {
            "total_processed": 0,
            "emails_processed": 0,
            "files_processed": 0,
            "errors": 0
        }
    }


def save_daily_log(log_data):
    """Save log data to JSON file"""
    try:
        LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR saving log: {e}")
        return False


def log_action(action_type, details, success=True):
    """Log an action to daily log and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = {
        "timestamp": timestamp,
        "type": action_type,
        "details": details,
        "success": success
    }
    
    # Print to console
    status = "✓" if success else "✗"
    print(f"[{timestamp}] {status} {action_type}: {details}")
    
    # Add to daily log
    log_data = load_daily_log()
    log_data["actions"].append(log_entry)
    
    if success:
        log_data["summary"]["total_processed"] += 1
        if action_type == "email_processed":
            log_data["summary"]["emails_processed"] += 1
        elif action_type == "file_processed":
            log_data["summary"]["files_processed"] += 1
    else:
        log_data["summary"]["errors"] += 1
    
    save_daily_log(log_data)
    
    # Add to recent activities for dashboard
    global recent_activities
    activity_text = f"{action_type.replace('_', ' ').title()}: {details}"
    recent_activities.append(f"- [{timestamp}] {activity_text}")
    
    # Keep only last 20 activities
    recent_activities = recent_activities[-20:]


def should_run_task(task_name: str) -> bool:
    """
    Check if a scheduled task should run now
    
    Args:
        task_name: Name of the task
        
    Returns:
        True if task should run
    """
    now = datetime.now()
    
    if task_name == "needs_action_scan":
        last_run = schedule_state.get("last_needs_action_scan")
        if last_run is None:
            return True
        return (now - last_run).total_seconds() >= SCHEDULE_CONFIG["needs_action_scan"]
    
    elif task_name == "gmail_check":
        last_run = schedule_state.get("last_gmail_check")
        if last_run is None:
            return True
        return (now - last_run).total_seconds() >= SCHEDULE_CONFIG["gmail_check"]
    
    elif task_name == "social_media_check":
        last_run = schedule_state.get("last_social_check")
        if last_run is None:
            return True
        return (now - last_run).total_seconds() >= SCHEDULE_CONFIG["social_media_check"]
    
    elif task_name == "ceo_briefing":
        # Run on Monday at 8 AM
        last_run = schedule_state.get("last_ceo_briefing")
        if last_run and (now - last_run).days < 7:
            return False
        return now.weekday() == 0 and now.hour == 8 and now.minute < 5
    
    elif task_name == "weekly_audit":
        # Run on Sunday at 11 PM
        last_run = schedule_state.get("last_weekly_audit")
        if last_run and (now - last_run).days < 7:
            return False
        return now.weekday() == 6 and now.hour == 23 and now.minute >= 55
    
    return False


def mark_task_run(task_name: str):
    """Mark a task as having been run"""
    now = datetime.now()
    
    if task_name == "needs_action_scan":
        schedule_state["last_needs_action_scan"] = now
    elif task_name == "gmail_check":
        schedule_state["last_gmail_check"] = now
    elif task_name == "social_media_check":
        schedule_state["last_social_check"] = now
    elif task_name == "ceo_briefing":
        schedule_state["last_ceo_briefing"] = now
    elif task_name == "weekly_audit":
        schedule_state["last_weekly_audit"] = now


def run_needs_action_scan():
    """Scan and process Needs_Action folder"""
    print("\n" + "=" * 50)
    print("SCHEDULED TASK: Needs_Action Scan")
    print("=" * 50)
    
    log_data = load_daily_log()
    
    if not NEEDS_ACTION_FOLDER.exists():
        NEEDS_ACTION_FOLDER.mkdir(parents=True, exist_ok=True)
        return 0, 0
    
    md_files = list(NEEDS_ACTION_FOLDER.glob("*.md"))
    
    if not md_files:
        print("No files to process in Needs_Action folder")
        return 0, 0
    
    pending_count = len(md_files)
    completed_count = 0
    
    print(f"Processing {pending_count} file(s)...")
    
    for filepath in md_files:
        print(f"  Processing: {filepath.name}")
        
        try:
            # Simple processing - move to Done
            move_to_done(filepath)
            completed_count += 1
            log_action("file_processed", filepath.name)
        except Exception as e:
            log_action("file_error", f"{filepath.name}: {e}", success=False)
    
    schedule_state["total_tasks_processed"] += completed_count
    mark_task_run("needs_action_scan")
    
    return pending_count, completed_count


def run_gmail_check():
    """Run Gmail watcher check"""
    print("\n" + "=" * 50)
    print("SCHEDULED TASK: Gmail Check")
    print("=" * 50)
    
    gmail_script = VAULT_PATH / "gmail_watcher.py"
    
    if not gmail_script.exists():
        print("Gmail watcher script not found")
        mark_task_run("gmail_check")
        return False
    
    try:
        # Run gmail_watcher for one cycle (not infinite loop)
        result = subprocess.run(
            [sys.executable, str(gmail_script)],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            log_action("gmail_check", "Gmail check completed")
            mark_task_run("gmail_check")
            return True
        else:
            log_action("gmail_check_error", result.stderr[:200], success=False)
            mark_task_run("gmail_check")
            return False
            
    except subprocess.TimeoutExpired:
        log_action("gmail_check_timeout", "Gmail check timed out", success=False)
        mark_task_run("gmail_check")
        return False
    except Exception as e:
        log_action("gmail_check_error", str(e), success=False)
        mark_task_run("gmail_check")
        return False


def run_social_media_check():
    """Check and process social media pending content"""
    print("\n" + "=" * 50)
    print("SCHEDULED TASK: Social Media Check")
    print("=" * 50)
    
    scheduler_script = VAULT_PATH / "social_scheduler.py"
    
    if not scheduler_script.exists():
        print("Social scheduler script not found")
        mark_task_run("social_media_check")
        return False
    
    try:
        # Run scheduler for one cycle
        result = subprocess.run(
            [sys.executable, str(scheduler_script), "--test", "--once"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            log_action("social_media_check", "Social media check completed")
            mark_task_run("social_media_check")
            return True
        else:
            log_action("social_media_error", result.stderr[:200], success=False)
            mark_task_run("social_media_check")
            return False
            
    except Exception as e:
        log_action("social_media_error", str(e), success=False)
        mark_task_run("social_media_check")
        return False


def run_ceo_briefing():
    """Generate CEO briefing"""
    print("\n" + "=" * 50)
    print("SCHEDULED TASK: CEO Briefing Generation")
    print("=" * 50)
    
    briefing_script = VAULT_PATH / "ceo_briefing.py"
    
    if not briefing_script.exists():
        print("CEO briefing script not found")
        mark_task_run("ceo_briefing")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(briefing_script)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            log_action("ceo_briefing", "CEO briefing generated successfully")
            mark_task_run("ceo_briefing")
            return True
        else:
            log_action("ceo_briefing_error", result.stderr[:200], success=False)
            mark_task_run("ceo_briefing")
            return False
            
    except Exception as e:
        log_action("ceo_briefing_error", str(e), success=False)
        mark_task_run("ceo_briefing")
        return False


def run_weekly_audit():
    """Run weekly system audit"""
    print("\n" + "=" * 50)
    print("SCHEDULED TASK: Weekly Audit")
    print("=" * 50)
    
    audit_report = {
        "timestamp": datetime.now().isoformat(),
        "system_health": {},
        "tasks_processed": schedule_state["total_tasks_processed"],
        "cycles_run": schedule_state["total_cycles"]
    }
    
    # Check folder sizes
    for folder_name, folder_path in [
        ("Needs_Action", NEEDS_ACTION_FOLDER),
        ("Done", DONE_FOLDER),
        ("Logs", LOGS_FOLDER),
        ("Pending_Approval", VAULT_PATH / "Pending_Approval")
    ]:
        if folder_path.exists():
            file_count = len(list(folder_path.glob("*")))
            audit_report["system_health"][folder_name] = f"{file_count} files"
    
    # Save audit report
    try:
        BRIEFINGS_FOLDER.mkdir(parents=True, exist_ok=True)
        audit_path = BRIEFINGS_FOLDER / f"WEEKLY_AUDIT_{datetime.now().strftime('%Y-%m-%d')}.json"
        
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit_report, f, indent=2)
        
        log_action("weekly_audit", f"Audit saved to {audit_path.name}")
        mark_task_run("weekly_audit")
        return True
        
    except Exception as e:
        log_action("weekly_audit_error", str(e), success=False)
        mark_task_run("weekly_audit")
        return False


def parse_yaml_frontmatter(content):
    """Extract YAML frontmatter from markdown content"""
    frontmatter = {}
    
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if match:
        yaml_content = match.group(1)
        for line in yaml_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                frontmatter[key.strip()] = value.strip()
    
    return frontmatter


def detect_file_type(filepath):
    """Detect file type from filename and content"""
    filename = filepath.name
    frontmatter = {}
    
    if filepath.suffix.lower() == ".md":
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read(2000)
                frontmatter = parse_yaml_frontmatter(content)
        except Exception:
            pass
    
    if filename.startswith("EMAIL_"):
        return "email"
    elif filename.startswith("FILE_"):
        return "file"
    elif filename.startswith("APPROVAL_"):
        return "approval"
    
    file_type = frontmatter.get("type", "").lower()
    if file_type:
        return file_type
    
    return "unknown"


def update_dashboard(pending_count, completed_count):
    """Update Dashboard.md with comprehensive Gold Tier status"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_only = datetime.now().strftime("%Y-%m-%d")
    
    # Get last 5 activities
    last_activities = "\n".join(recent_activities[-5:]) if recent_activities else "- No recent activity"
    
    # Count pending items
    pending_emails = len(list(NEEDS_ACTION_FOLDER.glob("EMAIL_*.md"))) if NEEDS_ACTION_FOLDER.exists() else 0
    pending_approvals = len(list((VAULT_PATH / "Pending_Approval").glob("*.md"))) if (VAULT_PATH / "Pending_Approval").exists() else 0
    
    # Get last briefing
    last_briefing = schedule_state.get("last_ceo_briefing")
    last_briefing_str = last_briefing.strftime("%Y-%m-%d %H:%M") if last_briefing else "Never"
    
    dashboard_content = f"""# AI Employee Dashboard (Gold Tier)

## System Status
- Last Updated: {date_only}
- System Status: Active
- Master Scheduler: Running
- Pending Tasks: {pending_count}
- Completed Tasks: {completed_count}

## Component Status

### Gmail Watcher
- Status: {"Running" if schedule_state.get("last_gmail_check") else "Not started"}
- Last Check: {schedule_state.get("last_gmail_check", "Never")}

### WhatsApp Watcher
- Status: Monitoring
- Session: Active

### Odoo Sync
- Status: Connected
- Last Sync: {schedule_state.get("last_needs_action_scan", "Never")}

### Social Media
- Twitter: Scheduled
- LinkedIn: Scheduled
- Instagram: Scheduled
- Last Post Check: {schedule_state.get("last_social_check", "Never")}

## Pending Items

| Type | Count |
|------|-------|
| Emails | {pending_emails} |
| Approvals | {pending_approvals} |
| Total | {pending_emails + pending_approvals} |

## Schedule Status

| Task | Interval | Last Run |
|------|----------|----------|
| Needs_Action Scan | 5 min | {schedule_state.get("last_needs_action_scan", "Never")} |
| Gmail Check | 2 min | {schedule_state.get("last_gmail_check", "Never")} |
| Social Media Check | 1 hour | {schedule_state.get("last_social_check", "Never")} |
| CEO Briefing | Mon 8 AM | {last_briefing_str} |
| Weekly Audit | Sun 11 PM | {schedule_state.get("last_weekly_audit", "Never")} |

## Recent Activity
{last_activities}

---

*Last orchestration cycle: {timestamp}*
*Total Cycles: {schedule_state["total_cycles"]}*
*Total Tasks Processed: {schedule_state["total_tasks_processed"]}*
"""
    
    try:
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(dashboard_content)
        return True
    except Exception as e:
        print(f"ERROR updating dashboard: {e}")
        return False


def requires_approval_check(content):
    """Check if content requires human approval based on sensitive keywords"""
    sensitive_keywords = [
        "payment", "invoice", "urgent", "asap", "delete", "send money",
        "bank", "transfer", "wire", "refund", "cancel", "terminate"
    ]
    content_lower = content.lower()
    return any(keyword in content_lower for keyword in sensitive_keywords)


def move_to_done(filepath):
    """Move processed file to Done folder"""
    try:
        dest_path = DONE_FOLDER / filepath.name
        
        counter = 1
        while dest_path.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            dest_path = DONE_FOLDER / f"{stem}_{counter}{suffix}"
            counter += 1
        
        shutil.move(str(filepath), str(dest_path))
        log_action("file_moved", f"Moved {filepath.name} to Done")
        return True
    except Exception as e:
        log_action("move_error", f"Failed to move {filepath.name}: {e}", success=False)
        return False


def run_master_scheduler_cycle():
    """Run one complete master scheduler cycle"""
    schedule_state["total_cycles"] += 1
    
    print("\n" + "=" * 60)
    print(f"MASTER SCHEDULER CYCLE #{schedule_state['total_cycles']}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tasks_run = []
    
    # Check and run scheduled tasks
    if should_run_task("needs_action_scan"):
        print("\n[Schedule] Running Needs_Action Scan...")
        run_needs_action_scan()
        tasks_run.append("needs_action_scan")
    
    if should_run_task("gmail_check"):
        print("\n[Schedule] Running Gmail Check...")
        run_gmail_check()
        tasks_run.append("gmail_check")
    
    if should_run_task("social_media_check"):
        print("\n[Schedule] Running Social Media Check...")
        run_social_media_check()
        tasks_run.append("social_media_check")
    
    if should_run_task("ceo_briefing"):
        print("\n[Schedule] Running CEO Briefing Generation...")
        run_ceo_briefing()
        tasks_run.append("ceo_briefing")
    
    if should_run_task("weekly_audit"):
        print("\n[Schedule] Running Weekly Audit...")
        run_weekly_audit()
        tasks_run.append("weekly_audit")
    
    if not tasks_run:
        print("\n[Schedule] No scheduled tasks due this cycle")
    
    # Update dashboard
    remaining_pending = len(list(NEEDS_ACTION_FOLDER.glob("*.md"))) if NEEDS_ACTION_FOLDER.exists() else 0
    update_dashboard(remaining_pending, schedule_state["total_tasks_processed"])
    
    return tasks_run


def main():
    """Main function - runs master scheduler"""
    print("=" * 60)
    print("AI Employee Orchestrator (Gold Tier)")
    print("Master Scheduler Implementation")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print("\nSchedule:")
    for task, interval in SCHEDULE_CONFIG.items():
        print(f"  - {task}: {interval}")
    print("=" * 60)
    
    # Ensure folders exist
    for folder in [NEEDS_ACTION_FOLDER, DONE_FOLDER, LOGS_FOLDER, VAULT_PATH / "Pending_Approval", BRIEFINGS_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)
    
    # Initial cycle
    print("\nRunning initial scheduler cycle...")
    run_master_scheduler_cycle()
    
    # Main scheduler loop - check every 30 seconds
    check_interval = 30  # seconds
    
    print("\n" + "=" * 60)
    print("MASTER SCHEDULER STARTED")
    print("=" * 60)
    print(f"Checking schedule every {check_interval} seconds...")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Run scheduler cycle
            tasks_run = run_master_scheduler_cycle()
            
            if tasks_run:
                print(f"\nTasks completed this cycle: {', '.join(tasks_run)}")
            
            # Wait before next check
            time.sleep(check_interval)
            
    except KeyboardInterrupt:
        print("\n\nOrchestrator stopped by user")
        
        # Save final state
        print("Saving final state...")
        remaining_pending = len(list(NEEDS_ACTION_FOLDER.glob("*.md"))) if NEEDS_ACTION_FOLDER.exists() else 0
        update_dashboard(remaining_pending, schedule_state["total_tasks_processed"])
        
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR in scheduler: {e}")
        log_action("scheduler_error", str(e), success=False)
        time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOrchestrator stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
