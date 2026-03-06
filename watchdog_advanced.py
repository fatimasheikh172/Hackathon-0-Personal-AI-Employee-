#!/usr/bin/env python3
"""
Advanced Watchdog - Process Monitoring and Auto-Restart with Retry Integration
Monitors critical processes, restarts failed PM2 processes, and writes alerts

Features:
- Integrates retry_handler.py for resilient operations
- Auto-restart failed PM2 processes
- Write alerts to Needs_Action\ALERT_*.md
- Health status tracking
"""

import os
import sys
import time
import json
import subprocess
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import psutil
from dotenv import load_dotenv

# Import retry handler
from retry_handler import with_retry, TransientError, SystemError, get_retry_stats

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"
NEEDS_ACTION_FOLDER = VAULT_PATH / "Needs_Action"
BRIEFINGS_FOLDER = VAULT_PATH / "Briefings"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
SYSTEM_HEALTH_FILE = VAULT_PATH / "system_health.md"

# Critical processes to monitor
CRITICAL_PROCESSES = [
    "gmail_watcher.py",
    "file_watcher.py",
    "orchestrator.py",
    "master_scheduler.py",
    "hitl_monitor.py",
    "whatsapp_watcher.py"
]

# PM2 process names (if using PM2)
PM2_PROCESSES = [
    "gmail_watcher",
    "file_watcher",
    "orchestrator",
    "master_scheduler"
]

# Check interval
CHECK_INTERVAL_SECONDS = int(os.getenv("WATCHDOG_CHECK_INTERVAL", "60"))

# Watchdog statistics
watchdog_stats = {
    "checks_performed": 0,
    "processes_restarted": 0,
    "pm2_restarts": 0,
    "alerts_created": 0,
    "degradation_events": 0,
    "start_time": datetime.now().isoformat()
}

# Restart tracking
restart_history: Dict[str, List[datetime]] = {}


# =============================================================================
# LOGGING
# =============================================================================

def get_log_file_path():
    """Get log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"watchdog_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"watchdog_activity_{date_str}.txt"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, NEEDS_ACTION_FOLDER, BRIEFINGS_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type: str, details: str, success: bool = True):
    """Log a watchdog action to log files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    status = "[OK]" if success else "[ERROR]"
    log_entry = f"[{timestamp}] {status} {action_type}: {details}\n"
    
    try:
        with open(get_text_log_file_path(), "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"[WARN] Failed to write text log: {e}")
    
    # JSON logging
    json_entry = {
        "timestamp": timestamp,
        "type": action_type,
        "details": details,
        "success": success
    }
    
    try:
        log_data = load_json_log()
        log_data["actions"].append(json_entry)
        save_json_log(log_data)
    except Exception as e:
        print(f"[WARN] Failed to write JSON log: {e}")
    
    print(f"[{timestamp}] {status} {action_type}: {details}")


def load_json_log():
    """Load today's JSON log or create new structure"""
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
            "total_checks": 0,
            "total_restarts": 0,
            "total_alerts": 0
        }
    }


def save_json_log(log_data: dict):
    """Save log data to JSON file"""
    try:
        log_data["summary"]["total_checks"] = watchdog_stats["checks_performed"]
        log_data["summary"]["total_restarts"] = watchdog_stats["processes_restarted"]
        log_data["summary"]["total_alerts"] = watchdog_stats["alerts_created"]
        
        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save JSON log: {e}")
        return False


# =============================================================================
# ALERT CREATION
# =============================================================================

@with_retry(max_attempts=3, base_delay=0.5)
def create_alert_file(alert_type: str, message: str, severity: str = "high"):
    """
    Create an alert file in Needs_Action folder
    
    Args:
        alert_type: Type of alert (process_down, pm2_failed, etc.)
        message: Alert message
        severity: Alert severity (low, medium, high, critical)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    alert_id = f"ALERT_{alert_type}_{timestamp}"
    filename = f"{alert_id}.md"
    filepath = NEEDS_ACTION_FOLDER / filename
    
    # Determine expiration (24 hours from now)
    expires = datetime.now() + timedelta(hours=24)
    
    content = f"""---
type: alert
alert_id: {alert_id}
alert_type: {alert_type}
severity: {severity}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
expires: {expires.strftime("%Y-%m-%d %H:%M:%S")}
status: pending
---

# System Alert: {alert_type.replace("_", " ").title()}

**Severity:** {severity.upper()}
**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Expires:** {expires.strftime("%Y-%m-%d %H:%M:%S")}

---

## Alert Details

{message}

---

## Required Actions

- [ ] Review the alert details
- [ ] Take corrective action
- [ ] Verify system recovery
- [ ] Mark as resolved

---

## Resolution Notes

*Add notes about how this alert was resolved*

---

*Generated by Advanced Watchdog System*
"""
    
    try:
        NEEDS_ACTION_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        watchdog_stats["alerts_created"] += 1
        log_action("alert_created", f"{alert_type}: {message[:100]}...")
        return filepath
        
    except Exception as e:
        log_action("alert_error", f"Failed to create alert: {e}", success=False)
        raise SystemError(f"Failed to create alert file: {e}")


# =============================================================================
# PROCESS MONITORING
# =============================================================================

@with_retry(max_attempts=3, base_delay=1.0)
def is_process_running(process_name: str) -> bool:
    """
    Check if a process is running
    
    Args:
        process_name: Name of the process/script to check
        
    Returns:
        True if running, False otherwise
    """
    try:
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info.get('cmdline', []) or [])
                if process_name in cmdline:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False
    except Exception as e:
        log_action("process_check_error", f"Error checking {process_name}: {e}", success=False)
        raise TransientError(f"Failed to check process: {e}")


@with_retry(max_attempts=3, base_delay=2.0)
def restart_process(process_name: str) -> bool:
    """
    Restart a process
    
    Args:
        process_name: Name of the process/script to restart
        
    Returns:
        True if restarted successfully, False otherwise
    """
    try:
        script_path = VAULT_PATH / process_name
        
        if not script_path.exists():
            log_action("restart_error", f"Script not found: {script_path}", success=False)
            return False
        
        # Start the process
        subprocess.Popen(
            [sys.executable, str(script_path)],
            creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
        )
        
        # Track restart
        if process_name not in restart_history:
            restart_history[process_name] = []
        
        restart_history[process_name].append(datetime.now())
        
        # Clean old restart records (older than 1 hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        restart_history[process_name] = [
            t for t in restart_history[process_name] if t > one_hour_ago
        ]
        
        watchdog_stats["processes_restarted"] += 1
        
        log_action("process_restarted", f"Restarted {process_name}")
        
        # Check for excessive restarts
        if len(restart_history[process_name]) > 3:
            log_action("excessive_restarts", f"{process_name} restarted >3 times in 1 hour", success=False)
            create_alert_file(
                "excessive_restarts",
                f"Process {process_name} has been restarted more than 3 times in the last hour. "
                f"This may indicate a deeper issue that needs investigation.",
                severity="critical"
            )
        
        return True
        
    except Exception as e:
        log_action("restart_error", f"Failed to restart {process_name}: {e}", success=False)
        raise SystemError(f"Failed to restart process: {e}")


# =============================================================================
# PM2 INTEGRATION
# =============================================================================

def check_pm2_installed() -> bool:
    """Check if PM2 is installed"""
    try:
        result = subprocess.run(
            ["pm2", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


@with_retry(max_attempts=3, base_delay=1.0)
def get_pm2_process_status(process_name: str) -> Optional[dict]:
    """
    Get PM2 process status
    
    Args:
        process_name: PM2 process name
        
    Returns:
        Process status dict or None if not found
    """
    try:
        result = subprocess.run(
            ["pm2", "show", process_name, "--json"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            elif isinstance(data, dict):
                return data
        return None
    except Exception as e:
        log_action("pm2_status_error", f"Error getting PM2 status for {process_name}: {e}", success=False)
        raise TransientError(f"Failed to get PM2 status: {e}")


@with_retry(max_attempts=3, base_delay=2.0)
def restart_pm2_process(process_name: str) -> bool:
    """
    Restart a PM2 process
    
    Args:
        process_name: PM2 process name
        
    Returns:
        True if restarted successfully
    """
    try:
        result = subprocess.run(
            ["pm2", "restart", process_name],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            watchdog_stats["pm2_restarts"] += 1
            log_action("pm2_restarted", f"PM2 process {process_name} restarted")
            return True
        else:
            log_action("pm2_restart_failed", f"PM2 restart failed for {process_name}: {result.stderr}", success=False)
            return False
            
    except Exception as e:
        log_action("pm2_restart_error", f"Error restarting PM2 process {process_name}: {e}", success=False)
        raise SystemError(f"Failed to restart PM2 process: {e}")


def check_and_restart_pm2_processes() -> Dict[str, str]:
    """
    Check all PM2 processes and restart if needed
    
    Returns:
        Dict of process name -> status
    """
    if not check_pm2_installed():
        log_action("pm2_not_installed", "PM2 is not installed, skipping PM2 checks")
        return {}
    
    print("\n" + "=" * 60)
    print("PM2 PROCESS CHECK")
    print("=" * 60)
    
    process_status = {}
    
    for process_name in PM2_PROCESSES:
        watchdog_stats["checks_performed"] += 1
        
        try:
            status = get_pm2_process_status(process_name)
            
            if status:
                online = status.get("pm2_env", {}).get("status", "") == "online"
                
                if online:
                    print(f"  [OK] {process_name} is online")
                    process_status[process_name] = "online"
                else:
                    print(f"  [WARN] {process_name} is {status.get('pm2_env', {}).get('status', 'unknown')}")
                    
                    # Try to restart
                    if restart_pm2_process(process_name):
                        process_status[process_name] = "restarted"
                    else:
                        process_status[process_name] = "failed"
                        create_alert_file(
                            "pm2_process_failed",
                            f"PM2 process {process_name} failed to restart. "
                            f"Current status: {status.get('pm2_env', {}).get('status', 'unknown')}",
                            severity="high"
                        )
            else:
                print(f"  [MISSING] {process_name} not found in PM2")
                process_status[process_name] = "missing"
                
        except Exception as e:
            print(f"  [ERROR] {process_name}: {e}")
            process_status[process_name] = "error"
    
    return process_status


# =============================================================================
# STANDARD PROCESS CHECK
# =============================================================================

def check_and_restart_processes() -> Dict[str, str]:
    """
    Check all critical processes and restart if needed
    
    Returns:
        Dict of process name -> status
    """
    print("\n" + "=" * 60)
    print("PROCESS MONITORING CHECK")
    print("=" * 60)
    
    process_status = {}
    
    for process_name in CRITICAL_PROCESSES:
        watchdog_stats["checks_performed"] += 1
        
        print(f"\nChecking: {process_name}")
        
        try:
            if is_process_running(process_name):
                print(f"  [OK] {process_name} is running")
                process_status[process_name] = "running"
            else:
                print(f"  [WARN] {process_name} is NOT running")
                log_action("process_down", f"{process_name} is not running", success=False)
                
                # Wait 10 seconds then check again (process might be restarting)
                print(f"  Waiting 10 seconds...")
                time.sleep(10)
                
                if is_process_running(process_name):
                    print(f"  [OK] {process_name} recovered on its own")
                    process_status[process_name] = "recovered"
                else:
                    # Try to restart
                    print(f"  Attempting restart...")
                    if restart_process(process_name):
                        print(f"  [OK] {process_name} restarted successfully")
                        process_status[process_name] = "restarted"
                    else:
                        print(f"  [ERROR] Failed to restart {process_name}")
                        process_status[process_name] = "failed"
                        
                        # Create alert
                        create_alert_file(
                            "process_failed",
                            f"Critical process {process_name} failed to restart. "
                            f"Manual intervention required.",
                            severity="critical"
                        )
                        
        except Exception as e:
            print(f"  [ERROR] {process_name}: {e}")
            process_status[process_name] = "error"
    
    return process_status


# =============================================================================
# HEALTH REPORT
# =============================================================================

def create_health_report() -> dict:
    """Create comprehensive health report"""
    print("\n" + "=" * 60)
    print("HEALTH REPORT")
    print("=" * 60)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "watchdog_stats": watchdog_stats.copy(),
        "restart_history": {
            k: [t.isoformat() for t in v]
            for k, v in restart_history.items()
        },
        "process_status": check_and_restart_processes(),
        "pm2_status": check_and_restart_pm2_processes() if check_pm2_installed() else {},
        "retry_stats": get_retry_stats()
    }
    
    # Save report
    try:
        BRIEFINGS_FOLDER.mkdir(parents=True, exist_ok=True)
        report_path = BRIEFINGS_FOLDER / f"WATCHDOG_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json"
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        
        log_action("health_report_created", f"Saved to {report_path}")
        print(f"\nReport saved: {report_path}")
        
    except Exception as e:
        log_action("report_error", f"Failed to save report: {e}", success=False)
    
    # Update system_health.md
    update_system_health_md(report)
    
    return report


def update_system_health_md(report: dict):
    """Update system_health.md with watchdog status"""
    try:
        content = f"""# System Health - Watchdog Status

**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Watchdog Statistics

| Metric | Value |
|--------|-------|
| Checks Performed | {report['watchdog_stats']['checks_performed']} |
| Processes Restarted | {report['watchdog_stats']['processes_restarted']} |
| PM2 Restarts | {report['watchdog_stats'].get('pm2_restarts', 0)} |
| Alerts Created | {report['watchdog_stats']['alerts_created']} |
| Uptime Since | {report['watchdog_stats']['start_time'][:19]} |

---

## Process Status

| Process | Status |
|---------|--------|
"""
        
        for process, status in report.get("process_status", {}).items():
            content += f"| {process} | {status} |\n"
        
        content += "\n## PM2 Status\n\n| Process | Status |\n|---------|--------|\n"
        
        for process, status in report.get("pm2_status", {}).items():
            content += f"| {process} | {status} |\n"
        
        content += f"""
---

## Recent Restarts

"""
        if report.get("restart_history"):
            for process, times in report["restart_history"].items():
                if times:
                    content += f"### {process}\n"
                    for t in times[-5:]:  # Last 5 restarts
                        content += f"- {t[:19]}\n"
        else:
            content += "*No recent restarts*\n"
        
        content += """
---

*Generated by Advanced Watchdog System*
"""
        
        with open(SYSTEM_HEALTH_FILE, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"[OK] Updated {SYSTEM_HEALTH_FILE}")
        
    except Exception as e:
        log_action("health_md_error", f"Failed to update system_health.md: {e}", success=False)


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """Main function - runs watchdog in infinite loop"""
    print("=" * 60)
    print("Advanced Watchdog - Process Monitoring with Retry")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Monitoring: {', '.join(CRITICAL_PROCESSES)}")
    print(f"Check Interval: {CHECK_INTERVAL_SECONDS} seconds")
    print(f"PM2 Enabled: {check_pm2_installed()}")
    print("=" * 60)
    
    # Ensure folders exist
    ensure_folders_exist()
    
    # Initial check
    print("\nPerforming initial check...")
    check_and_restart_processes()
    
    if check_pm2_installed():
        check_and_restart_pm2_processes()
    
    # Create initial health report
    create_health_report()
    
    print("\n" + "=" * 60)
    print("WATCHDOG STARTED")
    print("=" * 60)
    print(f"Monitoring every {CHECK_INTERVAL_SECONDS} seconds...")
    print("Press Ctrl+C to stop\n")
    
    last_report_time = datetime.now()
    
    try:
        while True:
            # Check and restart processes
            check_and_restart_processes()
            
            # Check PM2 processes every 5 minutes
            if check_pm2_installed() and (datetime.now() - last_report_time).total_seconds() >= 300:
                check_and_restart_pm2_processes()
            
            # Create health report every hour
            if (datetime.now() - last_report_time).total_seconds() >= 3600:
                create_health_report()
                last_report_time = datetime.now()
            
            # Wait before next check
            time.sleep(CHECK_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        print("\n\nWatchdog stopped by user")
        
        # Create final report
        create_health_report()
        
        sys.exit(0)
    except Exception as e:
        log_action("watchdog_error", f"Error in watchdog loop: {e}", success=False)
        time.sleep(30)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nWatchdog stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
