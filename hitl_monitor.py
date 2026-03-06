#!/usr/bin/env python3
"""
HITL Monitor - Human-in-the-Loop Approval Monitor
Monitors Pending_Approval, Approved, and Rejected folders
Handles approval workflow with logging and dashboard updates
"""

import os
import sys
import time
import json
import shutil
import re
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
PENDING_APPROVAL_FOLDER = VAULT_PATH / "Pending_Approval"
APPROVED_FOLDER = VAULT_PATH / "Approved"
REJECTED_FOLDER = VAULT_PATH / "Rejected"
DONE_FOLDER = VAULT_PATH / "Done"
LOGS_FOLDER = VAULT_PATH / "Logs"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"

MONITOR_INTERVAL = 30  # Check every 30 seconds

# Statistics for dashboard
stats = {
    "pending_approvals": 0,
    "approved_today": 0,
    "rejected_today": 0,
    "auto_approved": 0
}


def get_log_file_path():
    """Get JSON log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"hitl_monitor_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"hitl_activity_{date_str}.txt"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [PENDING_APPROVAL_FOLDER, APPROVED_FOLDER, REJECTED_FOLDER, DONE_FOLDER, LOGS_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)


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
        "approvals": [],
        "rejections": [],
        "summary": {
            "total_pending": 0,
            "total_approved": 0,
            "total_rejected": 0
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


def log_to_text_file(message):
    """Append a log message to the text log file"""
    try:
        LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        with open(get_text_log_file_path(), "a", encoding="utf-8") as f:
            f.write(log_entry)
        return True
    except Exception as e:
        print(f"ERROR writing text log: {e}")
        return False


def log_approval(details, filename, action_type=""):
    """Log an approval action"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = {
        "timestamp": timestamp,
        "filename": filename,
        "action_type": action_type,
        "details": details,
        "status": "approved"
    }
    
    log_data = load_daily_log()
    log_data["approvals"].append(log_entry)
    log_data["summary"]["total_approved"] += 1
    save_daily_log(log_data)
    
    log_to_text_file(f"APPROVED: {filename} - {action_type} - {details}")
    
    # Update stats
    stats["approved_today"] += 1


def log_rejection(details, filename, action_type=""):
    """Log a rejection action"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = {
        "timestamp": timestamp,
        "filename": filename,
        "action_type": action_type,
        "details": details,
        "status": "rejected"
    }
    
    log_data = load_daily_log()
    log_data["rejections"].append(log_entry)
    log_data["summary"]["total_rejected"] += 1
    save_daily_log(log_data)
    
    log_to_text_file(f"REJECTED: {filename} - {action_type} - {details}")
    
    # Update stats
    stats["rejected_today"] += 1


def log_pending_approval(filename, action_type, details):
    """Log a pending approval notification"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_entry = {
        "timestamp": timestamp,
        "filename": filename,
        "action_type": action_type,
        "details": details,
        "status": "pending"
    }
    
    log_data = load_daily_log()
    log_data["summary"]["total_pending"] += 1
    save_daily_log(log_data)
    
    log_to_text_file(f"PENDING: {filename} - {action_type} - {details}")


def parse_yaml_frontmatter(content):
    """Extract YAML frontmatter from markdown content"""
    frontmatter = {}
    
    # Match YAML frontmatter between --- markers
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if match:
        yaml_content = match.group(1)
        for line in yaml_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                value = value.strip().strip('"').strip("'")
                frontmatter[key.strip()] = value
    
    return frontmatter


def extract_summary_from_content(content):
    """Extract a brief summary from the file content"""
    # Remove frontmatter
    content = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL)
    
    # Get first meaningful line
    lines = content.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            # Truncate if too long
            if len(line) > 100:
                return line[:97] + "..."
            return line
    
    return "No summary available"


def update_dashboard():
    """Update Dashboard.md with HITL approval status"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_only = datetime.now().strftime("%Y-%m-%d")
    
    # Count pending files
    pending_count = len(list(PENDING_APPROVAL_FOLDER.glob("*.md")))
    stats["pending_approvals"] = pending_count
    
    # Read existing dashboard to preserve other sections
    dashboard_content = ""
    if DASHBOARD_FILE.exists():
        try:
            with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
                dashboard_content = f.read()
        except Exception:
            pass
    
    # Check if HITL section exists
    hitl_section = f"""## Approval Status
- Pending Approvals: {stats['pending_approvals']}
- Approved Today: {stats['approved_today']}
- Rejected Today: {stats['rejected_today']}
- Auto-approved: {stats['auto_approved']}
"""
    
    if "## Approval Status" in dashboard_content:
        # Replace existing HITL section
        import re
        pattern = r"## Approval Status.*?(?=## |\Z)"
        dashboard_content = re.sub(pattern, hitl_section, dashboard_content, flags=re.DOTALL)
    else:
        # Add HITL section before the final separator
        if "---" in dashboard_content:
            parts = dashboard_content.rsplit("---", 1)
            dashboard_content = parts[0] + hitl_section + "\n---" + parts[1] if len(parts) > 1 else dashboard_content + "\n" + hitl_section
        else:
            dashboard_content = dashboard_content + "\n" + hitl_section
    
    try:
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(dashboard_content)
        return True
    except Exception as e:
        print(f"ERROR updating dashboard: {e}")
        return False


def process_pending_approval_file(filepath):
    """Process a file detected in Pending_Approval folder"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        frontmatter = parse_yaml_frontmatter(content)
        
        filename = filepath.name
        action_type = frontmatter.get("type", "unknown")
        action = frontmatter.get("action", "")
        amount = frontmatter.get("amount", "")
        recipient = frontmatter.get("recipient", "")
        
        # Build summary
        if action == "payment":
            summary = f"Payment of {amount} to {recipient}"
        elif action:
            summary = action
        else:
            summary = extract_summary_from_content(content)
        
        # Log pending approval
        log_pending_approval(filename, action_type, summary)
        
        # Print notification
        print("\n" + "=" * 50)
        print("ACTION REQUIRED - HUMAN APPROVAL NEEDED")
        print("=" * 50)
        print(f"File: {filename}")
        print(f"Type: {action_type}")
        print(f"Details: {summary}")
        print()
        print("To APPROVE: move file to F:\\AI_Employee_Vault\\Approved")
        print("To REJECT:  move file to F:\\AI_Employee_Vault\\Rejected")
        print("=" * 50 + "\n")
        
        # Update dashboard
        update_dashboard()
        
        return True
        
    except Exception as e:
        print(f"ERROR processing pending file {filepath.name}: {e}")
        log_to_text_file(f"ERROR processing pending file {filepath.name}: {e}")
        return False


def process_approved_file(filepath):
    """Process a file detected in Approved folder"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        frontmatter = parse_yaml_frontmatter(content)
        
        filename = filepath.name
        action_type = frontmatter.get("type", "unknown")
        action = frontmatter.get("action", "")
        amount = frontmatter.get("amount", "")
        recipient = frontmatter.get("recipient", "")
        original_file = frontmatter.get("original_file", frontmatter.get("source_file", ""))
        status = frontmatter.get("status", "")
        
        # Build details
        if action == "payment":
            details = f"Payment of {amount} to {recipient}"
        elif action:
            details = action
        else:
            details = extract_summary_from_content(content)
        
        # Log approval
        log_approval(details, filename, action_type)
        
        # Print confirmation
        print(f"\nAPPROVED: {details}")
        
        # Move to Done folder
        dest_path = DONE_FOLDER / filepath.name
        
        # Handle duplicate filenames
        counter = 1
        while dest_path.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            dest_path = DONE_FOLDER / f"{stem}_{counter}{suffix}"
            counter += 1
        
        shutil.move(str(filepath), str(dest_path))
        log_to_text_file(f"Moved {filename} to Done folder")
        
        # Update dashboard
        update_dashboard()
        
        return True
        
    except Exception as e:
        print(f"ERROR processing approved file {filepath.name}: {e}")
        log_to_text_file(f"ERROR processing approved file {filepath.name}: {e}")
        return False


def process_rejected_file(filepath):
    """Process a file detected in Rejected folder"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        frontmatter = parse_yaml_frontmatter(content)
        
        filename = filepath.name
        action_type = frontmatter.get("type", "unknown")
        action = frontmatter.get("action", "")
        amount = frontmatter.get("amount", "")
        recipient = frontmatter.get("recipient", "")
        
        # Build details
        if action == "payment":
            details = f"Payment of {amount} to {recipient}"
        elif action:
            details = action
        else:
            details = extract_summary_from_content(content)
        
        # Log rejection
        log_rejection(details, filename, action_type)
        
        # Print confirmation
        print(f"\nREJECTED: {details}")
        
        # Move to Done folder
        dest_path = DONE_FOLDER / filepath.name
        
        # Handle duplicate filenames
        counter = 1
        while dest_path.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            dest_path = DONE_FOLDER / f"{stem}_{counter}{suffix}"
            counter += 1
        
        shutil.move(str(filepath), str(dest_path))
        log_to_text_file(f"Moved {filename} to Done folder (rejected)")
        
        # Update dashboard
        update_dashboard()
        
        return True
        
    except Exception as e:
        print(f"ERROR processing rejected file {filepath.name}: {e}")
        log_to_text_file(f"ERROR processing rejected file {filepath.name}: {e}")
        return False


def monitor_pending_approval():
    """Monitor Pending_Approval folder for new files"""
    if not PENDING_APPROVAL_FOLDER.exists():
        return
    
    md_files = list(PENDING_APPROVAL_FOLDER.glob("*.md"))
    
    for filepath in md_files:
        # Check if file is new (modified within last monitor interval)
        try:
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            age = datetime.now() - mtime
            
            # Process files less than 2 minutes old to avoid reprocessing
            if age.total_seconds() < 120:
                print(f"\n[Pending] Detected: {filepath.name}")
                process_pending_approval_file(filepath)
        except Exception as e:
            print(f"ERROR checking file {filepath.name}: {e}")


def monitor_approved():
    """Monitor Approved folder for new files"""
    if not APPROVED_FOLDER.exists():
        return
    
    md_files = list(APPROVED_FOLDER.glob("*.md"))
    
    for filepath in md_files:
        # Check if file is new (modified within last monitor interval)
        try:
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            age = datetime.now() - mtime
            
            # Process files less than 2 minutes old to avoid reprocessing
            if age.total_seconds() < 120:
                print(f"\n[Approved] Detected: {filepath.name}")
                process_approved_file(filepath)
        except Exception as e:
            print(f"ERROR checking file {filepath.name}: {e}")


def monitor_rejected():
    """Monitor Rejected folder for new files"""
    if not REJECTED_FOLDER.exists():
        return
    
    md_files = list(REJECTED_FOLDER.glob("*.md"))
    
    for filepath in md_files:
        # Check if file is new (modified within last monitor interval)
        try:
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            age = datetime.now() - mtime
            
            # Process files less than 2 minutes old to avoid reprocessing
            if age.total_seconds() < 120:
                print(f"\n[Rejected] Detected: {filepath.name}")
                process_rejected_file(filepath)
        except Exception as e:
            print(f"ERROR checking file {filepath.name}: {e}")


def print_status():
    """Print current status"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pending_count = len(list(PENDING_APPROVAL_FOLDER.glob("*.md")))
    
    print(f"\n[{timestamp}] Status: Pending={pending_count} | Approved Today={stats['approved_today']} | Rejected Today={stats['rejected_today']}")


def main():
    """Main function - runs HITL monitor in infinite loop"""
    print("=" * 60)
    print("HITL Monitor - Human-in-the-Loop Approval System")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Monitor Interval: {MONITOR_INTERVAL} seconds")
    print(f"Pending Folder: {PENDING_APPROVAL_FOLDER}")
    print(f"Approved Folder: {APPROVED_FOLDER}")
    print(f"Rejected Folder: {REJECTED_FOLDER}")
    print("=" * 60)
    
    # Ensure all folders exist
    ensure_folders_exist()
    
    # Initial dashboard update
    update_dashboard()
    
    print("\nHITL Monitor started. Press Ctrl+C to stop.\n")
    
    iteration = 0
    
    while True:
        iteration += 1
        
        # Monitor all folders
        monitor_pending_approval()
        monitor_approved()
        monitor_rejected()
        
        # Print periodic status
        if iteration % 2 == 0:  # Every ~60 seconds
            print_status()
        
        # Wait for next cycle
        time.sleep(MONITOR_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nHITL Monitor stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
