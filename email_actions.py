#!/usr/bin/env python3
"""
Email Actions - Process plans and create email drafts/responses
Reads Plans folder and creates appropriate email actions based on priority
"""

import os
import sys
import re
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Import email MCP server functions
from email_mcp_server import (
    draft_email,
    send_email,
    search_emails,
    get_email_content,
    reply_to_email,
    update_dashboard,
    log_action,
    ensure_folders_exist
)

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
PLANS_FOLDER = VAULT_PATH / "Plans"
PENDING_APPROVAL_FOLDER = VAULT_PATH / "Pending_Approval"
LOGS_FOLDER = VAULT_PATH / "Logs"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"

# Email action statistics
email_actions_stats = {
    "plans_processed": 0,
    "emails_draft_created": 0,
    "approvals_created": 0,
    "errors": 0
}


def get_log_file_path():
    """Get JSON log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"email_actions_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"email_actions_activity_{date_str}.txt"


def log_email_action(action_type, details, success=True):
    """Log an email action to log files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Text log entry
    status = "✓" if success else "✗"
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
        log_data = load_email_actions_json_log()
        log_data["actions"].append(json_entry)
        save_email_actions_json_log(log_data)
    except Exception as e:
        print(f"ERROR writing JSON log: {e}")
    
    # Print to console
    print(f"[{timestamp}] {status} {action_type}: {details}")


def load_email_actions_json_log():
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
            "total_plans_processed": 0,
            "total_drafts_created": 0,
            "total_approvals_created": 0,
            "total_errors": 0
        }
    }


def save_email_actions_json_log(log_data):
    """Save log data to JSON file"""
    try:
        log_data["summary"]["total_plans_processed"] = email_actions_stats["plans_processed"]
        log_data["summary"]["total_drafts_created"] = email_actions_stats["emails_draft_created"]
        log_data["summary"]["total_approvals_created"] = email_actions_stats["approvals_created"]
        log_data["summary"]["total_errors"] = email_actions_stats["errors"]
        
        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR saving JSON log: {e}")
        return False


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


def read_plan_file(filepath):
    """Read and parse a plan file"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        frontmatter = parse_yaml_frontmatter(content)
        
        # Get body content (after frontmatter)
        body = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL).strip()
        
        return {
            "filepath": filepath,
            "filename": filepath.name,
            "frontmatter": frontmatter,
            "body": body,
            "content": content
        }
    except Exception as e:
        log_email_action("plan_read_error", f"Failed to read {filepath.name}: {e}", success=False)
        return None


def extract_email_info(plan):
    """Extract email-related information from a plan"""
    frontmatter = plan.get("frontmatter", {})
    body = plan.get("body", "")
    
    # Get email details from frontmatter
    email_to = frontmatter.get("email_to", frontmatter.get("to", ""))
    email_subject = frontmatter.get("email_subject", frontmatter.get("subject", ""))
    email_type = frontmatter.get("type", "")
    
    # Try to extract from body if not in frontmatter
    if not email_to:
        to_match = re.search(r"To:\s*(.+)", body, re.IGNORECASE)
        if to_match:
            email_to = to_match.group(1).strip()
    
    if not email_subject:
        subject_match = re.search(r"Subject:\s*(.+)", body, re.IGNORECASE)
        if subject_match:
            email_subject = subject_match.group(1).strip()
    
    # Extract email body content
    email_body = ""
    body_lines = body.split("\n")
    in_email_section = False
    
    for line in body_lines:
        if "email content" in line.lower() or "message:" in line.lower():
            in_email_section = True
            continue
        if in_email_section:
            if line.startswith("#") and line.strip():
                break
            email_body += line + "\n"
    
    if not email_body.strip():
        email_body = body
    
    return {
        "to": email_to,
        "subject": email_subject,
        "type": email_type,
        "body": email_body.strip()
    }


def generate_email_response(plan, email_info):
    """Generate an appropriate email response based on plan content"""
    frontmatter = plan.get("frontmatter", {})
    body = plan.get("body", "")
    priority = frontmatter.get("priority", "medium").lower()
    
    # Generate subject if not provided
    subject = email_info.get("subject", "")
    if not subject:
        # Extract from plan title or first line
        title = frontmatter.get("title", "")
        if title:
            subject = title
        else:
            first_line = body.split("\n")[0].strip() if body else "Email Response"
            subject = first_line[:50]
    
    # Generate body if not provided
    email_body = email_info.get("body", "")
    if not email_body.strip():
        email_body = f"""Dear Recipient,

Thank you for your message. This is an automated response generated based on the following plan:

{body[:500]}

Please let us know if you need any further assistance.

Best regards,
AI Employee System
"""
    
    return {
        "to": email_info.get("to", ""),
        "subject": subject,
        "body": email_body
    }


def create_email_approval_request(email_data, plan_filename):
    """Create an approval request file for sending email"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    now = datetime.now()
    from datetime import timedelta
    expires = now + timedelta(hours=24)
    
    approval_filename = f"APPROVAL_EMAIL_{timestamp}.md"
    approval_path = PENDING_APPROVAL_FOLDER / approval_filename
    
    to_email = email_data.get("to", "Unknown")
    subject = email_data.get("subject", "No Subject")
    body = email_data.get("body", "")
    
    # Truncate body for display
    body_preview = body[:500] + "..." if len(body) > 500 else body
    
    approval_content = f"""---
type: approval_request
action: send_email
to: {to_email}
subject: {subject}
source_plan: {plan_filename}
created: {now.strftime("%Y-%m-%d %H:%M:%S")}
expires: {expires.strftime("%Y-%m-%d %H:%M:%S")}
status: pending
requires_approval: yes
---

## Email Approval Request

**To:** {to_email}  
**Subject:** {subject}  
**Source Plan:** {plan_filename}  
**Created:** {now.strftime("%Y-%m-%d %H:%M:%S")}  
**Expires:** {expires.strftime("%Y-%m-%d %H:%M:%S")}

---

## Email Content

{body_preview}

---

## To Approve
Move this file to F:\\AI_Employee_Vault\\Approved folder to send this email.

## To Reject
Move this file to F:\\AI_Employee_Vault\\Rejected folder to cancel this email.

---

*Created by Email Actions at {now.strftime("%Y-%m-%d %H:%M:%S")}*
"""
    
    try:
        PENDING_APPROVAL_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(approval_path, "w", encoding="utf-8") as f:
            f.write(approval_content)
        
        return approval_path
    except Exception as e:
        log_email_action("approval_create_error", f"Failed to create approval file: {e}", success=False)
        return None


def process_high_priority_plan(plan):
    """Process a HIGH priority plan - create draft and approval request"""
    plan_filename = plan.get("filename", "unknown")
    frontmatter = plan.get("frontmatter", {})
    
    log_email_action("processing_high_priority", f"Processing HIGH priority plan: {plan_filename}")
    
    # Extract email info
    email_info = extract_email_info(plan)
    
    if not email_info.get("to"):
        log_email_action("skip_no_recipient", f"No recipient found in {plan_filename}", success=False)
        email_actions_stats["errors"] += 1
        return False
    
    # Generate email response
    email_data = generate_email_response(plan, email_info)
    
    # Create draft email
    print(f"\nCreating draft for HIGH priority plan: {plan_filename}")
    draft_result = draft_email(
        to=email_data["to"],
        subject=email_data["subject"],
        body=email_data["body"]
    )
    
    if draft_result.get("success"):
        email_actions_stats["emails_draft_created"] += 1
        log_email_action("draft_created", f"Draft created for {plan_filename}: {email_data['subject'][:50]}")
    else:
        log_email_action("draft_failed", f"Failed to create draft for {plan_filename}: {draft_result.get('error')}", success=False)
        email_actions_stats["errors"] += 1
    
    # Create approval request
    approval_path = create_email_approval_request(email_data, plan_filename)
    
    if approval_path:
        email_actions_stats["approvals_created"] += 1
        log_email_action("approval_created", f"Created approval request: {approval_path.name}")
        print(f"APPROVAL CREATED: {approval_path.name}")
        print("Move to Approved folder to send this email")
    else:
        log_email_action("approval_failed", f"Failed to create approval for {plan_filename}", success=False)
        email_actions_stats["errors"] += 1
    
    return True


def process_medium_priority_plan(plan):
    """Process a MEDIUM priority plan - create draft only, no immediate approval"""
    plan_filename = plan.get("filename", "unknown")
    
    log_email_action("processing_medium_priority", f"Processing MEDIUM priority plan: {plan_filename}")
    
    # Extract email info
    email_info = extract_email_info(plan)
    
    if not email_info.get("to"):
        log_email_action("skip_no_recipient", f"No recipient found in {plan_filename}", success=False)
        email_actions_stats["errors"] += 1
        return False
    
    # Generate email response
    email_data = generate_email_response(plan, email_info)
    
    # Create draft email only (no approval request yet)
    print(f"\nCreating draft for MEDIUM priority plan: {plan_filename}")
    draft_result = draft_email(
        to=email_data["to"],
        subject=email_data["subject"],
        body=email_data["body"]
    )
    
    if draft_result.get("success"):
        email_actions_stats["emails_draft_created"] += 1
        log_email_action("draft_created_medium", f"Draft created for {plan_filename}: {email_data['subject'][:50]}")
        print(f"DRAFT CREATED: Email saved in Gmail drafts")
    else:
        log_email_action("draft_failed", f"Failed to create draft for {plan_filename}: {draft_result.get('error')}", success=False)
        email_actions_stats["errors"] += 1
    
    return True


def process_low_priority_plan(plan):
    """Process a LOW priority plan - log only, no action"""
    plan_filename = plan.get("filename", "unknown")
    
    log_email_action("processing_low_priority", f"Logging LOW priority plan: {plan_filename} (no action)")
    print(f"\nLOW priority plan logged: {plan_filename} (no email action)")
    
    return True


def scan_and_process_plans():
    """Scan Plans folder and process all email-related plans"""
    ensure_folders_exist()
    
    if not PLANS_FOLDER.exists():
        print("Plans folder does not exist. Creating...")
        PLANS_FOLDER.mkdir(parents=True, exist_ok=True)
        return 0, 0
    
    # Get all markdown files in Plans folder
    plan_files = list(PLANS_FOLDER.glob("*.md"))
    
    if not plan_files:
        print("No plans found in Plans folder")
        return 0, 0
    
    print(f"\n{'='*60}")
    print(f"Email Actions - Processing {len(plan_files)} plan(s)")
    print(f"{'='*60}\n")
    
    high_priority_count = 0
    medium_priority_count = 0
    low_priority_count = 0
    
    for plan_file in plan_files:
        print(f"\nProcessing: {plan_file.name}")
        
        plan = read_plan_file(plan_file)
        if not plan:
            email_actions_stats["errors"] += 1
            continue
        
        email_actions_stats["plans_processed"] += 1
        
        frontmatter = plan.get("frontmatter", {})
        priority = frontmatter.get("priority", "medium").lower()
        plan_type = frontmatter.get("type", "").lower()
        
        # Check if this is an email-related plan
        is_email_plan = (
            plan_type == "email" or
            "email" in plan_type or
            frontmatter.get("email_to") or
            frontmatter.get("to") or
            "send email" in plan.get("body", "").lower() or
            "reply to" in plan.get("body", "").lower()
        )
        
        if not is_email_plan:
            print(f"  Skipping: Not an email-related plan")
            continue
        
        print(f"  Priority: {priority}")
        print(f"  Type: {plan_type}")
        
        # Process based on priority
        if priority == "high":
            success = process_high_priority_plan(plan)
            if success:
                high_priority_count += 1
        elif priority == "medium":
            success = process_medium_priority_plan(plan)
            if success:
                medium_priority_count += 1
        else:  # low or unknown
            process_low_priority_plan(plan)
            low_priority_count += 1
    
    return high_priority_count + medium_priority_count, low_priority_count


def update_email_dashboard():
    """Update Dashboard.md with email actions status"""
    try:
        if not DASHBOARD_FILE.exists():
            return False
        
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Count pending email approvals
        pending_count = len(list(PENDING_APPROVAL_FOLDER.glob("APPROVAL_EMAIL_*.md")))
        
        email_section = f"""## Email MCP Status
- Emails Drafted Today: {email_actions_stats["emails_draft_created"]}
- Emails Sent Today: 0
- Pending Email Approvals: {pending_count}
- Last Email Action: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
        
        if "## Email MCP Status" in content:
            pattern = r"## Email MCP Status.*?(?=## |\Z)"
            content = re.sub(pattern, email_section, content, flags=re.DOTALL)
        else:
            if "---" in content:
                parts = content.rsplit("---", 1)
                content = parts[0] + email_section + "\n---" + parts[1] if len(parts) > 1 else content + "\n" + email_section
            else:
                content = content + "\n" + email_section
        
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
    except Exception as e:
        log_email_action("dashboard_error", f"Failed to update dashboard: {e}", success=False)
        return False


def main():
    """Main function - process all email plans"""
    print("=" * 60)
    print("Email Actions - Plan-Based Email Processor")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Plans Folder: {PLANS_FOLDER}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    ensure_folders_exist()
    
    # Process plans
    email_count, logged_count = scan_and_process_plans()
    
    # Update dashboard
    update_email_dashboard()
    
    # Print summary
    print(f"\n{'='*60}")
    print("EMAIL ACTIONS SUMMARY")
    print(f"{'='*60}")
    print(f"Plans Processed: {email_actions_stats['plans_processed']}")
    print(f"Email Plans Found: {email_count}")
    print(f"Drafts Created: {email_actions_stats['emails_draft_created']}")
    print(f"Approvals Created: {email_actions_stats['approvals_created']}")
    print(f"Errors: {email_actions_stats['errors']}")
    print(f"{'='*60}")
    
    log_email_action("summary", f"Processed {email_actions_stats['plans_processed']} plans, created {email_actions_stats['emails_draft_created']} drafts")
    
    print("\nTASK_COMPLETE")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nEmail Actions stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
