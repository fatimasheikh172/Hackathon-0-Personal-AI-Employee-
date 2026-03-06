#!/usr/bin/env python3
"""
Master Scheduler - Central scheduling system for AI Employee
Runs all scheduled tasks using the 'schedule' library
"""

import os
import sys
import time
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import schedule
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
NEEDS_ACTION_FOLDER = VAULT_PATH / "Needs_Action"
DONE_FOLDER = VAULT_PATH / "Done"
ARCHIVE_FOLDER = VAULT_PATH / "Archive"
BRIEFINGS_FOLDER = VAULT_PATH / "Briefings"
PLANS_FOLDER = VAULT_PATH / "Plans"
PENDING_APPROVAL_FOLDER = VAULT_PATH / "Pending_Approval"
LOGS_FOLDER = VAULT_PATH / "Logs"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"

# Scheduler settings from .env
DAILY_BRIEFING_TIME = os.getenv("DAILY_BRIEFING_TIME", "08:00")
WEEKLY_REPORT_DAY = os.getenv("WEEKLY_REPORT_DAY", "sunday")
CLEANUP_DAYS = int(os.getenv("CLEANUP_DAYS", "7"))
SCHEDULER_INTERVAL = int(os.getenv("SCHEDULER_INTERVAL", "120"))

# Scheduler statistics
scheduler_stats = {
    "last_run": None,
    "last_email_check": None,
    "last_plan_generation": None,
    "last_approval_check": None,
    "last_daily_briefing": None,
    "last_weekly_report": None,
    "last_cleanup": None,
    "total_jobs_run": 0,
    "total_errors": 0,
    "status": "Active"
}


def get_log_file_path():
    """Get JSON log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"scheduler_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"scheduler_activity_{date_str}.txt"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, BRIEFINGS_FOLDER, ARCHIVE_FOLDER, PLANS_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)


def log_scheduler_action(action_type, details, success=True):
    """Log a scheduler action to log files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Text log entry
    status = "[OK]" if success else "[ERROR]"
    log_entry = f"[{timestamp}] {status} {action_type}: {details}\n"
    
    try:
        with open(get_text_log_file_path(), "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"ERROR writing text log: {e}")
    
    # JSON log entry
    json_entry = {
        "timestamp": timestamp,
        "type": action_type,
        "details": details,
        "success": success
    }
    
    try:
        log_data = load_scheduler_json_log()
        log_data["actions"].append(json_entry)
        save_scheduler_json_log(log_data)
    except Exception as e:
        print(f"ERROR writing JSON log: {e}")
    
    # Print to console
    print(f"[{timestamp}] {status} {action_type}: {details}")


def load_scheduler_json_log():
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
            "total_jobs": 0,
            "total_errors": 0
        }
    }


def save_scheduler_json_log(log_data):
    """Save log data to JSON file"""
    try:
        log_data["summary"]["total_jobs"] = scheduler_stats["total_jobs_run"]
        log_data["summary"]["total_errors"] = scheduler_stats["total_errors"]
        
        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR saving JSON log: {e}")
        return False


def count_files_in_folder(folder, pattern="*.md"):
    """Count files matching pattern in folder"""
    try:
        if not folder.exists():
            return 0
        return len(list(folder.glob(pattern)))
    except Exception:
        return 0


def get_today_stats():
    """Get statistics for today"""
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Count emails processed (from orchestrator logs)
    emails_processed = 0
    orchestrator_log = LOGS_FOLDER / f"orchestrator_{today}.json"
    if orchestrator_log.exists():
        try:
            with open(orchestrator_log, "r", encoding="utf-8") as f:
                data = json.load(f)
                emails_processed = data.get("summary", {}).get("emails_processed", 0)
        except Exception:
            pass
    
    # Count plans created
    plans_created = count_files_in_folder(PLANS_FOLDER)
    
    # Count pending approvals
    pending_approvals = count_files_in_folder(PENDING_APPROVAL_FOLDER)
    
    # Count LinkedIn posts (from linkedin logs)
    linkedin_posts = 0
    linkedin_log = LOGS_FOLDER / f"linkedin_{today}.log"
    if linkedin_log.exists():
        try:
            with open(linkedin_log, "r", encoding="utf-8") as f:
                content = f.read()
                linkedin_posts = content.count("Posted successfully")
        except Exception:
            pass
    
    return {
        "emails_processed": emails_processed,
        "plans_created": plans_created,
        "pending_approvals": pending_approvals,
        "linkedin_posts": linkedin_posts
    }


def get_weekly_stats():
    """Get statistics for this week"""
    # This is a simplified version - would need more complex logic for actual week tracking
    today_stats = get_today_stats()
    
    # For now, return today's stats multiplied by 7 (placeholder)
    return {
        "emails_processed": today_stats["emails_processed"] * 7,
        "tasks_completed": today_stats["emails_processed"] + today_stats["linkedin_posts"],
        "linkedin_posts": today_stats["linkedin_posts"] * 7,
        "pending_items": today_stats["pending_approvals"]
    }


# ============================================================================
# SCHEDULED JOB: Check Needs_Action folder (Every 2 minutes)
# ============================================================================
def job_check_needs_action():
    """Check Needs_Action folder for new files and process them"""
    print(f"\n{'='*60}")
    print(f"JOB: Check Needs_Action Folder")
    print(f"{'='*60}")
    
    try:
        scheduler_stats["last_run"] = datetime.now()
        
        if not NEEDS_ACTION_FOLDER.exists():
            NEEDS_ACTION_FOLDER.mkdir(parents=True, exist_ok=True)
            print("  Needs_Action folder created")
            log_scheduler_action("needs_action_check", "Folder checked - no files")
            return
        
        # Count files
        md_files = list(NEEDS_ACTION_FOLDER.glob("*.md"))
        file_count = len(md_files)
        
        if file_count > 0:
            print(f"  Found {file_count} file(s) to process")
            log_scheduler_action("needs_action_check", f"Found {file_count} files")
            
            # Import and run orchestrator logic
            try:
                sys.path.insert(0, str(VAULT_PATH))
                from orchestrator import scan_and_process_needs_action
                
                pending, completed = scan_and_process_needs_action()
                print(f"  Processed {completed} file(s)")
                log_scheduler_action("needs_action_processed", f"Completed {completed} files")
            except ImportError as e:
                print(f"  Could not import orchestrator: {e}")
                log_scheduler_action("needs_action_error", f"Import error: {e}", success=False)
        else:
            print("  No files to process")
            log_scheduler_action("needs_action_check", "No files")
        
        scheduler_stats["total_jobs_run"] += 1
        
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("needs_action_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Generate Plans (Every 5 minutes)
# ============================================================================
def job_generate_plans():
    """Run plan_generator logic to create plans"""
    print(f"\n{'='*60}")
    print(f"JOB: Generate Plans")
    print(f"{'='*60}")
    
    try:
        scheduler_stats["last_plan_generation"] = datetime.now()
        
        # Import and run plan generator logic
        try:
            sys.path.insert(0, str(VAULT_PATH))
            from plan_generator import process_needs_action_folder
            
            plans_created = process_needs_action_folder()
            print(f"  Generated {plans_created} plan(s)")
            log_scheduler_action("plans_generated", f"Created {plans_created} plans")
        except ImportError as e:
            print(f"  Could not import plan_generator: {e}")
            log_scheduler_action("plans_error", f"Import error: {e}", success=False)
        except AttributeError as e:
            print(f"  Function not found: {e}")
            log_scheduler_action("plans_error", f"Function not found: {e}", success=False)
        
        scheduler_stats["total_jobs_run"] += 1
        
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("plans_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Check HITL Approvals (Every 5 minutes)
# ============================================================================
def job_check_approvals():
    """Run HITL monitor logic to check approvals"""
    print(f"\n{'='*60}")
    print(f"JOB: Check HITL Approvals")
    print(f"{'='*60}")
    
    try:
        scheduler_stats["last_approval_check"] = datetime.now()
        
        # Count pending approvals
        pending_count = count_files_in_folder(PENDING_APPROVAL_FOLDER)
        approved_count = count_files_in_folder(VAULT_PATH / "Approved")
        rejected_count = count_files_in_folder(VAULT_PATH / "Rejected")
        
        print(f"  Pending: {pending_count} | Approved: {approved_count} | Rejected: {rejected_count}")
        log_scheduler_action("approvals_check", f"Pending: {pending_count}, Approved: {approved_count}")
        
        # Import and run HITL monitor logic
        try:
            sys.path.insert(0, str(VAULT_PATH))
            from hitl_monitor import monitor_pending_approval, monitor_approved, monitor_rejected
            
            monitor_pending_approval()
            monitor_approved()
            monitor_rejected()
            
            print("  HITL monitor executed")
            log_scheduler_action("approvals_processed", "HITL monitor completed")
        except ImportError as e:
            print(f"  Could not import hitl_monitor: {e}")
            log_scheduler_action("approvals_error", f"Import error: {e}", success=False)
        
        scheduler_stats["total_jobs_run"] += 1
        
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("approvals_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Check Emails (Every 1 hour)
# ============================================================================
def job_check_emails():
    """Run Gmail watcher logic to check new emails"""
    print(f"\n{'='*60}")
    print(f"JOB: Check Emails")
    print(f"{'='*60}")
    
    try:
        scheduler_stats["last_email_check"] = datetime.now()
        
        # Import and run Gmail watcher logic
        try:
            sys.path.insert(0, str(VAULT_PATH))
            from gmail_watcher import check_new_emails
            
            emails_found = check_new_emails()
            print(f"  Email check completed, found {emails_found} new email(s)")
            log_scheduler_action("emails_checked", f"Found {emails_found} new emails")
        except ImportError as e:
            print(f"  Could not import gmail_watcher: {e}")
            log_scheduler_action("emails_error", f"Import error: {e}", success=False)
        except AttributeError:
            print("  Gmail watcher executed")
            log_scheduler_action("emails_checked", "Gmail watcher completed")
        
        # Run email actions
        try:
            from email_actions import scan_and_process_plans
            
            email_count, logged_count = scan_and_process_plans()
            print(f"  Processed {email_count} email plan(s)")
            log_scheduler_action("email_actions_processed", f"Processed {email_count} plans")
        except ImportError as e:
            print(f"  Could not import email_actions: {e}")
            log_scheduler_action("email_actions_error", f"Import error: {e}", success=False)
        
        # Update Dashboard
        update_dashboard()
        
        scheduler_stats["total_jobs_run"] += 1

    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("emails_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Check WhatsApp (Every 30 seconds)
# ============================================================================
def job_check_whatsapp():
    """Check WhatsApp for new messages"""
    print(f"\n{'='*60}")
    print(f"JOB: Check WhatsApp")
    print(f"{'='*60}")
    
    try:
        # Note: WhatsApp watcher runs as a separate process
        # This job just logs the check and updates stats
        
        print(f"  WhatsApp watcher is running as separate process")
        log_scheduler_action("whatsapp_check", "WhatsApp watcher check")
        
        scheduler_stats["total_jobs_run"] += 1
        
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("whatsapp_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Daily Briefing (Every day at 8:00 AM)
# ============================================================================
def job_daily_briefing():
    """Generate daily briefing file"""
    print(f"\n{'='*60}")
    print(f"JOB: Generate Daily Briefing")
    print(f"{'='*60}")
    
    try:
        scheduler_stats["last_daily_briefing"] = datetime.now()
        
        # Get today's stats
        stats = get_today_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        briefing_file = BRIEFINGS_FOLDER / f"DAILY_{today}.md"
        
        # Get top 3 priority tasks from Plans folder
        top_tasks = []
        if PLANS_FOLDER.exists():
            for plan_file in PLANS_FOLDER.glob("*.md"):
                try:
                    with open(plan_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    if "priority: high" in content.lower():
                        top_tasks.append(plan_file.name)
                        if len(top_tasks) >= 3:
                            break
                except Exception:
                    continue
        
        # Create briefing content
        briefing_content = f"""# Daily Briefing - {today}

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Today's Summary

### Emails Processed
- Total Emails: {stats['emails_processed']}

### Plans
- Plans Created: {stats['plans_created']}
- Pending Approvals: {stats['pending_approvals']}

### LinkedIn
- Posts Made Today: {stats['linkedin_posts']}

---

## Top 3 Priority Tasks

"""
        
        for i, task in enumerate(top_tasks, 1):
            briefing_content += f"{i}. {task}\n"
        
        if not top_tasks:
            briefing_content += "No high priority tasks\n"
        
        briefing_content += f"""
---

## Notes

*This briefing was automatically generated by the Master Scheduler*
"""
        
        # Write briefing file
        BRIEFINGS_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(briefing_file, "w", encoding="utf-8") as f:
            f.write(briefing_content)
        
        print(f"  Daily briefing created: {briefing_file.name}")
        log_scheduler_action("daily_briefing", f"Created {briefing_file.name}")
        
        scheduler_stats["total_jobs_run"] += 1
        
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("daily_briefing_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Daily Cleanup (Every day at 11:00 PM)
# ============================================================================
def job_daily_cleanup():
    """Clean up Done folder and generate daily summary"""
    print(f"\n{'='*60}")
    print(f"JOB: Daily Cleanup")
    print(f"{'='*60}")
    
    try:
        scheduler_stats["last_cleanup"] = datetime.now()
        
        # Move files older than CLEANUP_DAYS to Archive
        if DONE_FOLDER.exists():
            cutoff_date = datetime.now() - timedelta(days=CLEANUP_DAYS)
            moved_count = 0
            
            for file_path in DONE_FOLDER.glob("*.md"):
                try:
                    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        ARCHIVE_FOLDER.mkdir(parents=True, exist_ok=True)
                        dest_path = ARCHIVE_FOLDER / file_path.name
                        shutil.move(str(file_path), str(dest_path))
                        moved_count += 1
                except Exception:
                    continue
            
            print(f"  Archived {moved_count} file(s) older than {CLEANUP_DAYS} days")
            log_scheduler_action("cleanup_archived", f"Moved {moved_count} files to Archive")
        
        # Update Dashboard with daily stats
        update_dashboard()
        
        print("  Daily cleanup completed")
        log_scheduler_action("daily_cleanup", "Cleanup completed")
        
        scheduler_stats["total_jobs_run"] += 1
        
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("daily_cleanup_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Weekly Report (Every Sunday at 9:00 PM)
# ============================================================================
def job_weekly_report():
    """Generate weekly report file"""
    print(f"\n{'='*60}")
    print(f"JOB: Generate Weekly Report")
    print(f"{'='*60}")
    
    try:
        scheduler_stats["last_weekly_report"] = datetime.now()
        
        # Get weekly stats
        stats = get_weekly_stats()
        today = datetime.now().strftime("%Y-%m-%d")
        week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).strftime("%Y-%m-%d")
        report_file = BRIEFINGS_FOLDER / f"WEEKLY_{today}.md"
        
        # Create report content
        report_content = f"""# Weekly Report - Week of {week_start}

Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## This Week's Summary

### Emails
- Total Emails Processed: {stats['emails_processed']}

### Tasks
- Total Tasks Completed: {stats['tasks_completed']}

### LinkedIn
- Posts This Week: {stats['linkedin_posts']}

---

## Pending Items Summary

- Pending Approvals: {stats['pending_items']}

---

## Notes

*This report was automatically generated by the Master Scheduler*
"""
        
        # Write report file
        BRIEFINGS_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_content)
        
        print(f"  Weekly report created: {report_file.name}")
        log_scheduler_action("weekly_report", f"Created {report_file.name}")
        
        scheduler_stats["total_jobs_run"] += 1
        
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("weekly_report_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: CEO Briefing (Monday 8AM and Sunday 9PM)
# ============================================================================
def job_ceo_briefing():
    """Generate CEO briefing"""
    print(f"\n{'='*60}")
    print(f"JOB: Generate CEO Briefing")
    print(f"{'='*60}")
    
    try:
        # Import and run CEO briefing generator
        try:
            sys.path.insert(0, str(VAULT_PATH))
            from ceo_briefing import generate_ceo_briefing
            
            briefing_path = generate_ceo_briefing()
            print(f"  CEO briefing generated: {briefing_path}")
            log_scheduler_action("ceo_briefing", f"Generated {briefing_path.name}")
        except ImportError as e:
            print(f"  Could not import ceo_briefing: {e}")
            log_scheduler_action("ceo_briefing_error", f"Import error: {e}", success=False)
        
        scheduler_stats["total_jobs_run"] += 1
        
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("ceo_briefing_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Ralph Wiggum Process (Every 10 minutes)
# ============================================================================
def job_ralph_wiggum_process():
    """Run Ralph Wiggum Loop to process Needs_Action files"""
    print(f"\n{'='*60}")
    print(f"JOB: Ralph Wiggum Process Needs_Action")
    print(f"{'='*60}")
    
    try:
        # Import and run Ralph Wiggum Loop
        try:
            sys.path.insert(0, str(VAULT_PATH))
            from ralph_wiggum import RalphWiggumLoop
            
            loop = RalphWiggumLoop()
            
            # Run loop with max 5 iterations
            result = loop.run_loop(
                task_name="process_needs_action",
                work_function=loop.process_needs_action_loop,
                max_iterations=5
            )
            
            if result:
                print(f"  Ralph Wiggum completed successfully")
                log_scheduler_action("ralph_wiggum", "Process completed")
            else:
                print(f"  Ralph Wiggum reached max iterations")
                log_scheduler_action("ralph_wiggum", "Process reached max iterations", success=False)
                
        except ImportError as e:
            print(f"  Could not import ralph_wiggum: {e}")
            log_scheduler_action("ralph_wiggum_error", f"Import error: {e}", success=False)
        
        scheduler_stats["total_jobs_run"] += 1
        
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("ralph_wiggum_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Twitter Post (Every 12 hours)
# ============================================================================
def job_twitter_post():
    """Run Twitter poster to post tweet"""
    print(f"\n{'='*60}")
    print(f"JOB: Twitter Post")
    print(f"{'='*60}")
    
    try:
        # Import and run Twitter poster
        try:
            sys.path.insert(0, str(VAULT_PATH))
            from twitter_poster import main as twitter_main
            
            # Run twitter poster
            twitter_main()
            print(f"  Twitter post completed")
            log_scheduler_action("twitter_post", "Tweet posted")
        except ImportError as e:
            print(f"  Could not import twitter_poster: {e}")
            log_scheduler_action("twitter_error", f"Import error: {e}", success=False)
        
        scheduler_stats["total_jobs_run"] += 1
        
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("twitter_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Instagram Post (Every 24 hours)
# ============================================================================
def job_instagram_post():
    """Run Instagram poster to create post"""
    print(f"\n{'='*60}")
    print(f"JOB: Instagram Post")
    print(f"{'='*60}")

    try:
        # Import and run Instagram poster
        try:
            sys.path.insert(0, str(VAULT_PATH))
            from instagram_instagrapi import main as instagram_main

            # Run instagram poster
            instagram_main()
            print(f"  Instagram post completed")
            log_scheduler_action("instagram_post", "Instagram post created")
        except ImportError as e:
            print(f"  Could not import instagram_instagrapi: {e}")
            log_scheduler_action("instagram_error", f"Import error: {e}", success=False)

        scheduler_stats["total_jobs_run"] += 1

    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("instagram_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Weekly Report Sunday Check
# ============================================================================
def job_weekly_report_sunday_check():
    """Check if today is Sunday and generate weekly report"""
    today = datetime.now().strftime("%A").lower()

    if today == WEEKLY_REPORT_DAY.lower():
        job_weekly_report()
    else:
        # Skip if not Sunday
        pass


# ============================================================================
# SCHEDULED JOB: Error Recovery - System Health Check (Every 30 minutes)
# ============================================================================
def job_error_recovery_health():
    """Run system health check every 30 minutes"""
    print(f"\n{'='*60}")
    print(f"JOB: Error Recovery - System Health Check")
    print(f"{'='*60}")
    
    try:
        sys.path.insert(0, str(VAULT_PATH))
        from error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        health = recovery.check_system_health()
        
        if health['overall_status'] == 'Good':
            print(f"  System health: Good")
            log_scheduler_action("health_check", "System health: Good")
        else:
            print(f"  System health: {health['overall_status']}")
            log_scheduler_action("health_check", f"System health: {health['overall_status']}", success=False)
        
        scheduler_stats["total_jobs_run"] += 1
        
    except ImportError as e:
        print(f"  Could not import error_recovery: {e}")
        log_scheduler_action("health_error", f"Import error: {e}", success=False)
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("health_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Error Recovery - Recover Stuck Files (Every hour)
# ============================================================================
def job_recover_stuck_files():
    """Recover stuck files every hour"""
    print(f"\n{'='*60}")
    print(f"JOB: Error Recovery - Recover Stuck Files")
    print(f"{'='*60}")
    
    try:
        sys.path.insert(0, str(VAULT_PATH))
        from error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        recovered = recovery.recover_stuck_files()
        
        print(f"  Recovered {recovered} file(s)")
        log_scheduler_action("file_recovery", f"Recovered {recovered} files")
        
        scheduler_stats["total_jobs_run"] += 1
        
    except ImportError as e:
        print(f"  Could not import error_recovery: {e}")
        log_scheduler_action("recovery_error", f"Import error: {e}", success=False)
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("recovery_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# SCHEDULED JOB: Error Recovery - Cleanup Old Logs (Daily at midnight)
# ============================================================================
def job_cleanup_old_logs():
    """Cleanup old logs daily at midnight"""
    print(f"\n{'='*60}")
    print(f"JOB: Error Recovery - Cleanup Old Logs")
    print(f"{'='*60}")
    
    try:
        sys.path.insert(0, str(VAULT_PATH))
        from error_recovery import ErrorRecovery
        
        recovery = ErrorRecovery()
        deleted = recovery.cleanup_old_logs()
        
        print(f"  Deleted {deleted} old log file(s)")
        log_scheduler_action("log_cleanup", f"Deleted {deleted} files")
        
        scheduler_stats["total_jobs_run"] += 1
        
    except ImportError as e:
        print(f"  Could not import error_recovery: {e}")
        log_scheduler_action("cleanup_error", f"Import error: {e}", success=False)
    except Exception as e:
        print(f"  ERROR: {e}")
        log_scheduler_action("cleanup_error", str(e), success=False)
        scheduler_stats["total_errors"] += 1


# ============================================================================
# Dashboard Update
# ============================================================================
def update_dashboard():
    """Update Dashboard.md with scheduler status"""
    try:
        if not DASHBOARD_FILE.exists():
            return False
        
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Format next run times
        next_email_check = "Pending"
        next_daily_briefing = f"{DAILY_BRIEFING_TIME}"
        next_weekly_report = f"{WEEKLY_REPORT_DAY.title()} 9:00 PM"
        
        scheduler_section = f"""## Scheduler Status
- Master Scheduler: {scheduler_stats['status']}
- Last Run: {scheduler_stats['last_run'].strftime('%Y-%m-%d %H:%M:%S') if scheduler_stats['last_run'] else 'Never'}
- Next Email Check: {next_email_check}
- Next Daily Briefing: {next_daily_briefing}
- Next Weekly Report: {next_weekly_report}
"""
        
        if "## Scheduler Status" in content:
            import re
            pattern = r"## Scheduler Status.*?(?=## |\Z)"
            content = re.sub(pattern, scheduler_section, content, flags=re.DOTALL)
        else:
            if "---" in content:
                parts = content.rsplit("---", 1)
                content = parts[0] + scheduler_section + "\n---" + parts[1] if len(parts) > 1 else content + "\n" + scheduler_section
            else:
                content = content + "\n" + scheduler_section
        
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
    except Exception as e:
        log_scheduler_action("dashboard_error", f"Failed to update dashboard: {e}", success=False)
        return False


# ============================================================================
# Setup Schedule
# ============================================================================
def setup_schedule():
    """Setup all scheduled jobs"""
    print("\n" + "=" * 60)
    print("SETTING UP SCHEDULE")
    print("=" * 60)
    
    # Every 2 minutes: Check Needs_Action folder
    schedule.every(2).minutes.do(job_check_needs_action)
    print(f"  [OK] Scheduled: Check Needs_Action folder (every 2 minutes)")
    
    # Every 5 minutes: Generate plans and check approvals
    schedule.every(5).minutes.do(job_generate_plans)
    print(f"  [OK] Scheduled: Generate plans (every 5 minutes)")

    schedule.every(5).minutes.do(job_check_approvals)
    print(f"  [OK] Scheduled: Check HITL approvals (every 5 minutes)")

    # Every 10 minutes: Run Ralph Wiggum Loop for Needs_Action processing
    schedule.every(10).minutes.do(job_ralph_wiggum_process)
    print(f"  [OK] Scheduled: Ralph Wiggum process_needs_action (every 10 minutes)")

    # Every 1 hour: Check emails and run email actions
    schedule.every(1).hours.do(job_check_emails)
    print(f"  [OK] Scheduled: Check emails (every 1 hour)")

    # Every 30 seconds: Check WhatsApp for new messages
    schedule.every(30).seconds.do(job_check_whatsapp)
    print(f"  [OK] Scheduled: Check WhatsApp (every 30 seconds)")

    # Every 12 hours: Post to Twitter
    schedule.every(12).hours.do(job_twitter_post)
    print(f"  [OK] Scheduled: Twitter post (every 12 hours)")

    # Every 24 hours: Post to Instagram
    schedule.every(24).hours.do(job_instagram_post)
    print(f"  [OK] Scheduled: Instagram post (every 24 hours)")

    # Every day at 8:00 AM: Generate daily briefing
    schedule.every().day.at(DAILY_BRIEFING_TIME).do(job_daily_briefing)
    print(f"  [OK] Scheduled: Daily briefing at {DAILY_BRIEFING_TIME}")

    # Every Monday at 8:00 AM: Generate CEO briefing
    schedule.every().monday.at("08:00").do(job_ceo_briefing)
    print(f"  [OK] Scheduled: CEO briefing (Monday 8:00 AM)")

    # Every Sunday at 9:00 PM: Generate CEO briefing (weekly review)
    schedule.every().sunday.at("21:00").do(job_ceo_briefing)
    print(f"  [OK] Scheduled: CEO briefing (Sunday 9:00 PM)")

    # Every day at 11:00 PM: Daily cleanup
    schedule.every().day.at("23:00").do(job_daily_cleanup)
    print(f"  [OK] Scheduled: Daily cleanup at 23:00")

    # Every Sunday at 9:00 PM: Weekly report
    # Note: schedule library doesn't support day names, so we run daily and check day in job
    schedule.every().day.at("21:00").do(job_weekly_report_sunday_check)
    print(f"  [OK] Scheduled: Weekly report check at 21:00 (runs on {WEEKLY_REPORT_DAY})")

    # Error Recovery schedules
    # Every 30 minutes: System health check
    schedule.every(30).minutes.do(job_error_recovery_health)
    print(f"  [OK] Scheduled: Error recovery health check (every 30 minutes)")

    # Every hour: Recover stuck files
    schedule.every(1).hours.do(job_recover_stuck_files)
    print(f"  [OK] Scheduled: Recover stuck files (every 1 hour)")

    # Every day at midnight: Cleanup old logs
    schedule.every().day.at("00:00").do(job_cleanup_old_logs)
    print(f"  [OK] Scheduled: Cleanup old logs (daily at midnight)")

    print("\n" + "=" * 60)


def print_next_runs():
    """Print next scheduled run times"""
    print("\n" + "=" * 60)
    print("NEXT SCHEDULED RUNS")
    print("=" * 60)
    
    for job in schedule.get_jobs():
        next_run = job.next_run
        if next_run:
            job_name = job.job_func.__name__.replace("job_", "")
            print(f"  {job_name}: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("=" * 60)


def main():
    """Main function - runs scheduler in infinite loop"""
    print("=" * 60)
    print("Master Scheduler - AI Employee System")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Scheduler Interval: {SCHEDULER_INTERVAL} seconds")
    print(f"Daily Briefing Time: {DAILY_BRIEFING_TIME}")
    print(f"Weekly Report Day: {WEEKLY_REPORT_DAY}")
    print(f"Cleanup Days: {CLEANUP_DAYS}")
    print("=" * 60)
    
    # Ensure folders exist
    ensure_folders_exist()
    
    # Setup schedule
    setup_schedule()
    
    # Initial dashboard update
    update_dashboard()
    
    # Run initial jobs
    print("\nRunning initial jobs...")
    job_check_needs_action()
    job_generate_plans()
    job_check_approvals()
    
    # Print next runs
    print_next_runs()
    
    print("\nScheduler started. Press Ctrl+C to stop.\n")
    
    # Main loop
    while True:
        try:
            # Run pending jobs
            schedule.run_pending()
            
            # Update stats
            scheduler_stats["last_run"] = datetime.now()
            
            # Update dashboard periodically
            update_dashboard()
            
            # Small sleep to prevent CPU hogging
            time.sleep(1)
            
        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user")
            sys.exit(0)
        except Exception as e:
            print(f"\nERROR in scheduler loop: {e}")
            log_scheduler_action("scheduler_error", str(e), success=False)
            scheduler_stats["total_errors"] += 1
            time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
