#!/usr/bin/env python3
"""
Error Recovery and Graceful Degradation System
Automatically recovers from errors and degrades gracefully when components fail
"""

import os
import sys
import time
import json
import shutil
import random
from datetime import datetime, timedelta
from pathlib import Path

import psutil
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
NEEDS_ACTION_FOLDER = VAULT_PATH / "Needs_Action"
DONE_FOLDER = VAULT_PATH / "Done"
LOGS_FOLDER = VAULT_PATH / "Logs"
PLANS_FOLDER = VAULT_PATH / "Plans"
APPROVED_FOLDER = VAULT_PATH / "Approved"
QUARANTINE_FOLDER = VAULT_PATH / "Quarantine"
BRIEFINGS_FOLDER = VAULT_PATH / "Briefings"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"

# Critical scripts to monitor
CRITICAL_SCRIPTS = [
    "gmail_watcher.py",
    "file_watcher.py",
    "orchestrator.py",
    "master_scheduler.py",
    "hitl_monitor.py"
]

# Recovery statistics
recovery_stats = {
    "total_retries": 0,
    "successful_recoveries": 0,
    "failed_recoveries": 0,
    "process_restarts": 0,
    "quarantined_files": 0,
    "cleanup_count": 0,
    "degradation_events": 0
}


def get_log_file_path():
    """Get log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"error_recovery_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"error_recovery_activity_{date_str}.txt"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, QUARANTINE_FOLDER, BRIEFINGS_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True):
    """Log a recovery action to log files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    status = "[OK]" if success else "[ERROR]"
    log_entry = f"[{timestamp}] {status} {action_type}: {details}\n"
    
    try:
        with open(get_text_log_file_path(), "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"ERROR writing text log: {e}")
    
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
        print(f"ERROR writing JSON log: {e}")
    
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
            "total_retries": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0
        }
    }


def save_json_log(log_data):
    """Save log data to JSON file"""
    try:
        log_data["summary"]["total_retries"] = recovery_stats["total_retries"]
        log_data["summary"]["successful_recoveries"] = recovery_stats["successful_recoveries"]
        log_data["summary"]["failed_recoveries"] = recovery_stats["failed_recoveries"]
        
        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR saving JSON log: {e}")
        return False


class ErrorRecovery:
    """
    Error Recovery and Graceful Degradation System
    
    Usage:
        recovery = ErrorRecovery()
        result = recovery.with_retry(some_function, max_attempts=3)
        health = recovery.check_system_health()
    """
    
    def __init__(self):
        """Initialize Error Recovery system"""
        ensure_folders_exist()
        self.restart_counts = {}  # Track restarts per process
        self.degradation_status = {}  # Track degraded components
    
    def with_retry(self, func, max_attempts=3, base_delay=1, max_delay=60, *args, **kwargs):
        """
        Retry function with exponential backoff
        
        Args:
            func: Function to retry
            max_attempts: Maximum number of attempts (default: 3)
            base_delay: Base delay in seconds (default: 1)
            max_delay: Maximum delay in seconds (default: 60)
            *args, **kwargs: Arguments to pass to func
        
        Returns:
            Result from func if successful
        
        Raises:
            Exception: If all attempts fail
        """
        last_exception = None
        
        for attempt in range(max_attempts):
            try:
                recovery_stats["total_retries"] += 1
                
                if attempt > 0:
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    # Add jitter to prevent thundering herd
                    delay = delay * (0.5 + random.random())
                    
                    log_action("retry_waiting", f"Attempt {attempt + 1}/{max_attempts}, waiting {delay:.1f}s")
                    time.sleep(delay)
                
                result = func(*args, **kwargs)
                
                if attempt > 0:
                    log_action("retry_success", f"Success on attempt {attempt + 1}/{max_attempts}")
                    recovery_stats["successful_recoveries"] += 1
                
                return result
                
            except Exception as e:
                last_exception = e
                log_action("retry_failed", f"Attempt {attempt + 1}/{max_attempts} failed: {e}", success=False)
        
        # All attempts failed
        log_action("retry_exhausted", f"All {max_attempts} attempts failed: {last_exception}", success=False)
        recovery_stats["failed_recoveries"] += 1
        raise last_exception
    
    def check_system_health(self):
        """
        Check system health and return health report
        
        Returns:
            dict: Health report with status for each component
        """
        print("\n" + "=" * 60)
        print("SYSTEM HEALTH CHECK")
        print("=" * 60)
        
        health_report = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "overall_status": "Good",
            "folders": {},
            "scripts": {},
            "disk_space": {"status": "Unknown", "free_gb": 0},
            "log_activity": {"status": "Unknown", "last_activity": None},
            "issues": []
        }
        
        # Check critical folders
        print("\nChecking critical folders...")
        critical_folders = {
            "Needs_Action": NEEDS_ACTION_FOLDER,
            "Done": DONE_FOLDER,
            "Logs": LOGS_FOLDER,
            "Plans": PLANS_FOLDER,
            "Approved": APPROVED_FOLDER
        }
        
        for name, path in critical_folders.items():
            exists = path.exists()
            health_report["folders"][name] = "OK" if exists else "MISSING"
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {name}: {path}")
            
            if not exists:
                health_report["issues"].append(f"Missing folder: {name}")
                health_report["overall_status"] = "Critical"
        
        # Check critical scripts
        print("\nChecking critical scripts...")
        for script in CRITICAL_SCRIPTS:
            script_path = VAULT_PATH / script
            exists = script_path.exists()
            health_report["scripts"][script] = "OK" if exists else "MISSING"
            status = "[OK]" if exists else "[MISSING]"
            print(f"  {status} {script}")
            
            if not exists:
                health_report["issues"].append(f"Missing script: {script}")
                health_report["overall_status"] = "Warning"
        
        # Check disk space
        print("\nChecking disk space...")
        try:
            import shutil
            total, used, free = shutil.disk_usage(str(VAULT_PATH))
            free_gb = free / (1024 ** 3)
            health_report["disk_space"]["free_gb"] = round(free_gb, 2)
            
            if free_gb < 1:
                health_report["disk_space"]["status"] = "CRITICAL"
                health_report["issues"].append(f"Low disk space: {free_gb:.2f}GB free")
                health_report["overall_status"] = "Critical"
                print(f"  [CRITICAL] Disk space: {free_gb:.2f}GB free (less than 1GB)")
            elif free_gb < 5:
                health_report["disk_space"]["status"] = "Warning"
                health_report["issues"].append(f"Low disk space: {free_gb:.2f}GB free")
                health_report["overall_status"] = "Warning"
                print(f"  [WARN] Disk space: {free_gb:.2f}GB free (less than 5GB)")
            else:
                health_report["disk_space"]["status"] = "OK"
                print(f"  [OK] Disk space: {free_gb:.2f}GB free")
        except Exception as e:
            health_report["disk_space"]["status"] = "Unknown"
            health_report["issues"].append(f"Disk space check failed: {e}")
            print(f"  [ERROR] Could not check disk space: {e}")
        
        # Check log activity
        print("\nChecking log activity...")
        try:
            log_files = list(LOGS_FOLDER.glob("*.log")) + list(LOGS_FOLDER.glob("*.txt"))
            if log_files:
                latest_log = max(log_files, key=lambda f: f.stat().st_mtime)
                last_modified = datetime.fromtimestamp(latest_log.stat().st_mtime)
                age = datetime.now() - last_modified
                
                health_report["log_activity"]["last_activity"] = last_modified.strftime("%Y-%m-%d %H:%M:%S")
                
                if age.total_seconds() < 86400:  # 24 hours
                    health_report["log_activity"]["status"] = "OK"
                    print(f"  [OK] Recent activity: {age.total_seconds() / 3600:.1f} hours ago")
                else:
                    health_report["log_activity"]["status"] = "Warning"
                    health_report["issues"].append(f"No recent log activity: {age.total_seconds() / 3600:.1f} hours")
                    health_report["overall_status"] = "Warning"
                    print(f"  [WARN] No recent activity: {age.total_seconds() / 3600:.1f} hours ago")
            else:
                health_report["log_activity"]["status"] = "Warning"
                health_report["issues"].append("No log files found")
                print(f"  [WARN] No log files found")
        except Exception as e:
            health_report["log_activity"]["status"] = "Unknown"
            health_report["issues"].append(f"Log activity check failed: {e}")
            print(f"  [ERROR] Could not check log activity: {e}")
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"OVERALL STATUS: {health_report['overall_status']}")
        print(f"Issues found: {len(health_report['issues'])}")
        for issue in health_report['issues']:
            print(f"  - {issue}")
        print("=" * 60)
        
        # Save health report
        self._save_health_report(health_report)
        
        return health_report
    
    def _save_health_report(self, health_report):
        """Save health report to Briefings folder"""
        try:
            BRIEFINGS_FOLDER.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            report_path = BRIEFINGS_FOLDER / f"HEALTH_{date_str}.md"
            
            report_content = f"""# System Health Report - {health_report['timestamp']}

## Overall Status: {health_report['overall_status']}

## Folders Status
"""
            for folder, status in health_report['folders'].items():
                report_content += f"- {folder}: {status}\n"
            
            report_content += "\n## Scripts Status\n"
            for script, status in health_report['scripts'].items():
                report_content += f"- {script}: {status}\n"
            
            report_content += f"""
## Disk Space
- Status: {health_report['disk_space']['status']}
- Free Space: {health_report['disk_space']['free_gb']} GB

## Log Activity
- Status: {health_report['log_activity']['status']}
- Last Activity: {health_report['log_activity']['last_activity']}

## Issues
"""
            if health_report['issues']:
                for issue in health_report['issues']:
                    report_content += f"- {issue}\n"
            else:
                report_content += "- No issues found\n"
            
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            
            log_action("health_report_saved", f"Saved to {report_path}")
            
        except Exception as e:
            log_action("health_report_error", f"Failed to save report: {e}", success=False)
    
    def recover_stuck_files(self):
        """
        Recover files stuck in Needs_Action for more than 24 hours
        
        Returns:
            int: Count of recovered files
        """
        print("\n" + "=" * 60)
        print("RECOVER STUCK FILES")
        print("=" * 60)
        
        if not NEEDS_ACTION_FOLDER.exists():
            print("Needs_Action folder does not exist")
            return 0
        
        recovered_count = 0
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        for file_path in NEEDS_ACTION_FOLDER.glob("*.md"):
            try:
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                
                if file_mtime < cutoff_time:
                    # File is older than 24 hours - quarantine it
                    QUARANTINE_FOLDER.mkdir(parents=True, exist_ok=True)
                    dest_path = QUARANTINE_FOLDER / file_path.name
                    
                    shutil.move(str(file_path), str(dest_path))
                    recovered_count += 1
                    recovery_stats["quarantined_files"] += 1
                    
                    print(f"  Quarantined: {file_path.name} (older than 24h)")
                    log_action("file_quarantined", f"Moved {file_path.name} to Quarantine")
                    
            except Exception as e:
                print(f"  ERROR processing {file_path.name}: {e}")
                log_action("quarantine_error", f"Failed to quarantine {file_path.name}: {e}", success=False)
        
        print(f"\nRecovered {recovered_count} file(s) to Quarantine folder")
        log_action("recovery_complete", f"Quarantined {recovered_count} files")
        
        return recovered_count
    
    def cleanup_old_logs(self):
        """
        Delete log files older than 90 days
        
        Returns:
            int: Count of deleted files
        """
        print("\n" + "=" * 60)
        print("CLEANUP OLD LOGS")
        print("=" * 60)
        
        if not LOGS_FOLDER.exists():
            print("Logs folder does not exist")
            return 0
        
        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(days=90)
        
        for file_path in LOGS_FOLDER.glob("*"):
            if file_path.is_file():
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    
                    if file_mtime < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        recovery_stats["cleanup_count"] += 1
                        
                        print(f"  Deleted: {file_path.name} (older than 90 days)")
                        log_action("log_deleted", f"Deleted {file_path.name}")
                        
                except Exception as e:
                    print(f"  ERROR deleting {file_path.name}: {e}")
                    log_action("cleanup_error", f"Failed to delete {file_path.name}: {e}", success=False)
        
        print(f"\nDeleted {deleted_count} old log file(s)")
        log_action("cleanup_complete", f"Deleted {deleted_count} files")
        
        return deleted_count
    
    def restart_failed_process(self, process_name):
        """
        Restart a failed process if it's not running
        
        Args:
            process_name: Name of the process to restart
        
        Returns:
            bool: True if restarted, False otherwise
        """
        print(f"\nChecking process: {process_name}")
        
        try:
            # Check if process is running
            process_running = False
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info.get('cmdline', []) or [])
                    if process_name in cmdline:
                        process_running = True
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if process_running:
                print(f"  [OK] {process_name} is running")
                return True
            
            # Process not running - restart it
            print(f"  [WARN] {process_name} is NOT running - attempting restart...")
            
            script_path = VAULT_PATH / process_name
            if not script_path.exists():
                print(f"  [ERROR] Script not found: {script_path}")
                return False
            
            # Start the process
            import subprocess
            subprocess.Popen([sys.executable, str(script_path)], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0)
            
            recovery_stats["process_restarts"] += 1
            
            # Track restart count
            if process_name not in self.restart_counts:
                self.restart_counts[process_name] = []
            
            self.restart_counts[process_name].append(datetime.now())
            
            # Clean old restart records (older than 1 hour)
            one_hour_ago = datetime.now() - timedelta(hours=1)
            self.restart_counts[process_name] = [
                t for t in self.restart_counts[process_name] if t > one_hour_ago
            ]
            
            # Check for excessive restarts
            if len(self.restart_counts[process_name]) > 3:
                print(f"  [ALERT] {process_name} restarted more than 3 times in 1 hour!")
                log_action("excessive_restarts", f"{process_name} restarted excessively", success=False)
                self._update_dashboard_alert(f"ALERT: {process_name} restarting excessively")
            
            print(f"  [OK] Restarted {process_name}")
            log_action("process_restarted", f"Restarted {process_name}")
            
            return True
            
        except Exception as e:
            print(f"  [ERROR] Failed to restart {process_name}: {e}")
            log_action("restart_error", f"Failed to restart {process_name}: {e}", success=False)
            return False
    
    def graceful_degradation(self, component, fallback_action):
        """
        Handle component failure with graceful degradation
        
        Args:
            component: Name of failed component
            fallback_action: Function to run as fallback
        
        Returns:
            Result from fallback_action
        """
        print(f"\n" + "=" * 60)
        print(f"GRACEFUL DEGRADATION: {component}")
        print("=" * 60)
        
        recovery_stats["degradation_events"] += 1
        
        # Log degradation
        log_action("degradation_started", f"Component {component} failed, using fallback")
        
        # Update degradation status
        self.degradation_status[component] = {
            "status": "degraded",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fallback": fallback_action.__name__ if hasattr(fallback_action, '__name__') else str(fallback_action)
        }
        
        # Update dashboard
        self._update_dashboard_degradation(component, "degraded")
        
        # Run fallback action
        try:
            print(f"Running fallback action: {fallback_action.__name__ if hasattr(fallback_action, '__name__') else 'fallback'}")
            result = fallback_action()
            
            log_action("degradation_fallback", f"Fallback action completed for {component}")
            
            return result
            
        except Exception as e:
            log_action("degradation_fallback_failed", f"Fallback failed for {component}: {e}", success=False)
            print(f"[ERROR] Fallback action failed: {e}")
            return None
    
    def _update_dashboard_alert(self, alert_message):
        """Update Dashboard.md with alert message"""
        try:
            if not DASHBOARD_FILE.exists():
                return
            
            with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Add alert to recent activity
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            alert_entry = f"- [{timestamp}] ALERT: {alert_message}\n"
            
            if "## Recent Activity" in content:
                content = content.replace("## Recent Activity", f"## Recent Activity\n{alert_entry}")
            
            with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
                f.write(content)
                
        except Exception as e:
            print(f"ERROR updating dashboard: {e}")
    
    def _update_dashboard_degradation(self, component, status):
        """Update Dashboard.md with degradation status"""
        try:
            if not DASHBOARD_FILE.exists():
                return
            
            with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Update system health section
            degradation_entry = f"- {component}: {status}"
            
            if "## System Health Status" in content:
                # Add to health status section
                if degradation_entry not in content:
                    content = content.replace("## System Health Status", 
                                            f"## System Health Status\n{degradation_entry}")
            
            with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
                f.write(content)
                
        except Exception as e:
            print(f"ERROR updating dashboard: {e}")
    
    def create_health_report(self):
        """
        Create comprehensive health report
        
        Returns:
            dict: Health report
        """
        print("\n" + "=" * 60)
        print("CREATE HEALTH REPORT")
        print("=" * 60)
        
        # Run health check
        health_report = self.check_system_health()
        
        # Add recovery stats
        health_report["recovery_stats"] = recovery_stats.copy()
        
        # Save report
        self._save_health_report(health_report)
        
        return health_report


def main():
    """Main function - run health check and recovery"""
    print("=" * 60)
    print("Error Recovery System - AI Employee")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print("=" * 60)
    
    # Ensure folders exist
    ensure_folders_exist()
    
    # Create recovery instance
    recovery = ErrorRecovery()
    
    # Run health check
    health = recovery.check_system_health()
    
    # Recover stuck files
    recovered = recovery.recover_stuck_files()
    
    # Print summary
    print("\n" + "=" * 60)
    print("RECOVERY SUMMARY")
    print("=" * 60)
    print(f"Overall Health: {health['overall_status']}")
    print(f"Files Quarantined: {recovered}")
    print(f"Total Retries: {recovery_stats['total_retries']}")
    print(f"Successful Recoveries: {recovery_stats['successful_recoveries']}")
    print(f"Failed Recoveries: {recovery_stats['failed_recoveries']}")
    print("=" * 60)
    
    return health


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nError Recovery stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
