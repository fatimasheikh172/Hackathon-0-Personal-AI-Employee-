#!/usr/bin/env python3
"""
Email MCP Server - Gmail API integration with HITL approval
All email send actions require human approval before execution
"""

import os
import sys
import base64
import json
import re
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
CREDENTIALS_FILE = VAULT_PATH / "credentials.json"
TOKEN_FILE = VAULT_PATH / "token.json"
LOGS_FOLDER = VAULT_PATH / "Logs"
PENDING_APPROVAL_FOLDER = VAULT_PATH / "Pending_Approval"
APPROVED_FOLDER = VAULT_PATH / "Approved"

# Gmail API scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.draft"
]

# Email statistics
email_stats = {
    "drafted_today": 0,
    "sent_today": 0,
    "pending_approvals": 0,
    "last_action": "Never",
    "last_action_time": None
}


def get_log_file_path():
    """Get JSON log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"email_mcp_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"email_activity_{date_str}.txt"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, PENDING_APPROVAL_FOLDER, APPROVED_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True):
    """Log an email action to log files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Update stats
    email_stats["last_action"] = f"{action_type}: {details[:50]}..."
    email_stats["last_action_time"] = timestamp

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
        log_data = load_json_log()
        log_data["actions"].append(json_entry)
        
        if action_type == "email_draft_created":
            email_stats["drafted_today"] += 1
        elif action_type == "email_sent":
            email_stats["sent_today"] += 1
        
        save_json_log(log_data)
    except Exception as e:
        print(f"ERROR writing JSON log: {e}")
    
    # Print to console
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
            "total_drafts": 0,
            "total_sent": 0,
            "total_errors": 0
        }
    }


def save_json_log(log_data):
    """Save log data to JSON file"""
    try:
        log_data["summary"]["total_drafts"] = email_stats["drafted_today"]
        log_data["summary"]["total_sent"] = email_stats["sent_today"]
        
        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR saving JSON log: {e}")
        return False


def get_gmail_service():
    """Get authenticated Gmail API service"""
    creds = None
    
    # Load existing token
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            log_action("auth_error", f"Failed to load token: {e}", success=False)
            creds = None
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                log_action("auth_error", f"Token refresh failed: {e}", success=False)
                creds = None
        
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                log_action("auth_error", f"Authentication failed: {e}", success=False)
                return None
    
    # Save token for future use
    try:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    except Exception as e:
        log_action("token_error", f"Failed to save token: {e}", success=False)
    
    try:
        service = build("gmail", "v1", credentials=creds)
        return service
    except Exception as e:
        log_action("service_error", f"Failed to build Gmail service: {e}", success=False)
        return None


def check_email_approval(to_email, subject):
    """Check if sending email to this recipient/subject is approved"""
    if not APPROVED_FOLDER.exists():
        return False, None
    
    # Look for approval files
    for approval_file in APPROVED_FOLDER.glob("APPROVAL_EMAIL_*.md"):
        try:
            with open(approval_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check if this approval matches
            if to_email in content and subject in content:
                return True, approval_file
        except Exception:
            continue
    
    return False, None


def create_email_approval_request(to_email, subject, body, action_type="send_email"):
    """Create an approval request file for sending email"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    now = datetime.now()
    from datetime import timedelta
    expires = now + timedelta(hours=24)
    
    approval_filename = f"APPROVAL_EMAIL_{timestamp}.md"
    approval_path = PENDING_APPROVAL_FOLDER / approval_filename
    
    # Truncate body for display
    body_preview = body[:500] + "..." if len(body) > 500 else body
    
    approval_content = f"""---
type: approval_request
action: {action_type}
to: {to_email}
subject: {subject}
created: {now.strftime("%Y-%m-%d %H:%M:%S")}
expires: {expires.strftime("%Y-%m-%d %H:%M:%S")}
status: pending
requires_approval: yes
---

## Email Approval Request

**To:** {to_email}  
**Subject:** {subject}  
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

*Created by Email MCP Server at {now.strftime("%Y-%m-%d %H:%M:%S")}*
"""
    
    try:
        PENDING_APPROVAL_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(approval_path, "w", encoding="utf-8") as f:
            f.write(approval_content)
        
        email_stats["pending_approvals"] += 1
        return approval_path
    except Exception as e:
        log_action("approval_create_error", f"Failed to create approval file: {e}", success=False)
        return None


def draft_email(to, subject, body, cc=None, bcc=None):
    """
    Create a draft email in Gmail (does NOT send)
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body (plain text or HTML)
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
    
    Returns:
        dict: {"success": bool, "draft_id": str or None, "error": str or None}
    """
    print(f"\n{'='*50}")
    print(f"DRAFT EMAIL")
    print(f"{'='*50}")
    print(f"To: {to}")
    print(f"Subject: {subject}")
    print(f"{'='*50}\n")
    
    try:
        service = get_gmail_service()
        if not service:
            log_action("draft_error", f"Failed to get Gmail service for draft to {to}", success=False)
            return {"success": False, "draft_id": None, "error": "Authentication failed"}
        
        # Create message
        message = MIMEMultipart("alternative")
        message["to"] = to
        message["subject"] = subject
        
        if cc:
            message["cc"] = cc
        if bcc:
            message["bcc"] = bcc
        
        # Add body (both plain text and HTML)
        message.attach(MIMEText(body, "plain"))
        message.attach(MIMEText(body.replace("\n", "<br>"), "html"))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        
        # Create draft
        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw_message}}
        ).execute()
        
        draft_id = draft.get("id")
        
        log_action("email_draft_created", f"Draft created for {to}: {subject[:50]}")
        
        return {
            "success": True,
            "draft_id": draft_id,
            "error": None,
            "message": f"Draft created successfully with ID: {draft_id}"
        }
        
    except HttpError as error:
        error_msg = f"Gmail API error: {error}"
        log_action("draft_error", error_msg, success=False)
        return {"success": False, "draft_id": None, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        log_action("draft_error", error_msg, success=False)
        return {"success": False, "draft_id": None, "error": error_msg}


def send_email(to, subject, body, cc=None, bcc=None, require_approval=True):
    """
    Send an email via Gmail API (requires approval)
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
        cc: CC recipients (optional)
        bcc: BCC recipients (optional)
        require_approval: If True, checks for approval file (default: True)
    
    Returns:
        dict: {"success": bool, "message_id": str or None, "error": str or None}
    """
    print(f"\n{'='*50}")
    print(f"SEND EMAIL")
    print(f"{'='*50}")
    print(f"To: {to}")
    print(f"Subject: {subject}")
    print(f"{'='*50}\n")
    
    # Check for approval
    if require_approval:
        is_approved, approval_file = check_email_approval(to, subject)
        
        if not is_approved:
            log_action("email_send_blocked", f"No approval found for email to {to}: {subject[:50]}")
            
            # Create approval request
            approval_path = create_email_approval_request(to, subject, body, "send_email")
            
            if approval_path:
                print(f"APPROVAL REQUIRED: Created {approval_path.name}")
                print("Move file to Approved folder to send this email")
                return {
                    "success": False,
                    "message_id": None,
                    "error": "Approval required",
                    "approval_file": str(approval_path)
                }
            else:
                return {
                    "success": False,
                    "message_id": None,
                    "error": "Failed to create approval request"
                }
    
    try:
        service = get_gmail_service()
        if not service:
            log_action("send_error", f"Failed to get Gmail service for email to {to}", success=False)
            return {"success": False, "message_id": None, "error": "Authentication failed"}
        
        # Create message
        message = MIMEMultipart("alternative")
        message["to"] = to
        message["subject"] = subject
        
        if cc:
            message["cc"] = cc
        if bcc:
            message["bcc"] = bcc
        
        # Add body
        message.attach(MIMEText(body, "plain"))
        message.attach(MIMEText(body.replace("\n", "<br>"), "html"))
        
        # Encode and send
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        
        sent_message = service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()
        
        message_id = sent_message.get("id")
        
        log_action("email_sent", f"Email sent to {to}: {subject[:50]} (ID: {message_id})")
        
        # Move approval file to Done if it exists
        if require_approval and approval_file:
            try:
                done_folder = VAULT_PATH / "Done"
                done_folder.mkdir(parents=True, exist_ok=True)
                import shutil
                shutil.move(str(approval_file), str(done_folder / approval_file.name))
                log_action("approval_archived", f"Moved approval file to Done: {approval_file.name}")
            except Exception as e:
                log_action("archive_error", f"Failed to archive approval file: {e}", success=False)
        
        return {
            "success": True,
            "message_id": message_id,
            "error": None,
            "message": f"Email sent successfully with ID: {message_id}"
        }
        
    except HttpError as error:
        error_msg = f"Gmail API error: {error}"
        log_action("send_error", error_msg, success=False)
        return {"success": False, "message_id": None, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        log_action("send_error", error_msg, success=False)
        return {"success": False, "message_id": None, "error": error_msg}


def search_emails(query, max_results=10):
    """
    Search Gmail for emails matching query
    
    Args:
        query: Gmail search query (e.g., "from:example@gmail.com", "subject:invoice")
        max_results: Maximum number of results (default: 10)
    
    Returns:
        dict: {"success": bool, "emails": list or None, "error": str or None}
    """
    print(f"\n{'='*50}")
    print(f"SEARCH EMAILS")
    print(f"{'='*50}")
    print(f"Query: {query}")
    print(f"Max Results: {max_results}")
    print(f"{'='*50}\n")
    
    try:
        service = get_gmail_service()
        if not service:
            log_action("search_error", f"Failed to get Gmail service for query: {query}", success=False)
            return {"success": False, "emails": None, "error": "Authentication failed"}
        
        # Search for messages
        results = service.users().messages().list(
            userId="me",
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get("messages", [])
        
        if not messages:
            log_action("search_result", f"No emails found for query: {query}")
            return {"success": True, "emails": [], "error": None, "message": "No emails found"}
        
        emails = []
        for msg in messages:
            try:
                # Get message details
                message = service.users().messages().get(
                    userId="me",
                    id=msg["id"],
                    format="metadata",
                    metadataHeaders=["From", "To", "Subject", "Date", "Snippet"]
                ).execute()
                
                headers = message.get("payload", {}).get("headers", [])
                
                email_data = {
                    "id": message["id"],
                    "from": next((h["value"] for h in headers if h["name"] == "From"), "Unknown"),
                    "to": next((h["value"] for h in headers if h["name"] == "To"), "Unknown"),
                    "subject": next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject"),
                    "date": next((h["value"] for h in headers if h["name"] == "Date"), "Unknown"),
                    "snippet": message.get("snippet", "")
                }
                
                emails.append(email_data)
                
            except Exception as e:
                log_action("search_parse_error", f"Failed to parse message {msg['id']}: {e}", success=False)
                continue
        
        log_action("search_result", f"Found {len(emails)} emails for query: {query}")
        
        return {
            "success": True,
            "emails": emails,
            "error": None,
            "message": f"Found {len(emails)} emails"
        }
        
    except HttpError as error:
        error_msg = f"Gmail API error: {error}"
        log_action("search_error", error_msg, success=False)
        return {"success": False, "emails": None, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        log_action("search_error", error_msg, success=False)
        return {"success": False, "emails": None, "error": error_msg}


def get_email_content(message_id):
    """
    Get full content of a specific email
    
    Args:
        message_id: Gmail message ID
    
    Returns:
        dict: {"success": bool, "email": dict or None, "error": str or None}
    """
    print(f"\n{'='*50}")
    print(f"GET EMAIL CONTENT")
    print(f"{'='*50}")
    print(f"Message ID: {message_id}")
    print(f"{'='*50}\n")
    
    try:
        service = get_gmail_service()
        if not service:
            log_action("get_content_error", f"Failed to get Gmail service for message: {message_id}", success=False)
            return {"success": False, "email": None, "error": "Authentication failed"}
        
        # Get full message
        message = service.users().messages().get(
            userId="me",
            id=message_id,
            format="full"
        ).execute()
        
        # Parse headers
        headers = message.get("payload", {}).get("headers", [])
        
        email_data = {
            "id": message["id"],
            "thread_id": message.get("threadId"),
            "label_ids": message.get("labelIds", []),
            "from": next((h["value"] for h in headers if h["name"] == "From"), "Unknown"),
            "to": next((h["value"] for h in headers if h["name"] == "To"), "Unknown"),
            "subject": next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject"),
            "date": next((h["value"] for h in headers if h["name"] == "Date"), "Unknown"),
            "snippet": message.get("snippet", "")
        }
        
        # Get body content
        body = ""
        payload = message.get("payload", {})
        
        if "body" in payload and "data" in payload["body"]:
            body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
        elif "parts" in payload:
            for part in payload["parts"]:
                if part.get("mimeType") == "text/plain" and "data" in part["body"]:
                    body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
                    break
        
        email_data["body"] = body
        
        log_action("get_content", f"Retrieved content for message: {message_id}")
        
        return {
            "success": True,
            "email": email_data,
            "error": None,
            "message": f"Retrieved email content for {message_id}"
        }
        
    except HttpError as error:
        error_msg = f"Gmail API error: {error}"
        log_action("get_content_error", error_msg, success=False)
        return {"success": False, "email": None, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        log_action("get_content_error", error_msg, success=False)
        return {"success": False, "email": None, "error": error_msg}


def reply_to_email(message_id, body, require_approval=True):
    """
    Create a draft reply to a specific email (requires approval to send)
    
    Args:
        message_id: Gmail message ID to reply to
        body: Reply body
        require_approval: If True, creates approval request (default: True)
    
    Returns:
        dict: {"success": bool, "draft_id": str or None, "error": str or None}
    """
    print(f"\n{'='*50}")
    print(f"REPLY TO EMAIL")
    print(f"{'='*50}")
    print(f"Message ID: {message_id}")
    print(f"{'='*50}\n")
    
    try:
        service = get_gmail_service()
        if not service:
            log_action("reply_error", f"Failed to get Gmail service for message: {message_id}", success=False)
            return {"success": False, "draft_id": None, "error": "Authentication failed"}
        
        # Get original message for reference
        original = service.users().messages().get(
            userId="me",
            id=message_id,
            format="metadata",
            metadataHeaders=["From", "To", "Subject"]
        ).execute()
        
        headers = original.get("payload", {}).get("headers", [])
        original_from = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
        original_subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        
        # Ensure subject has Re: prefix
        if not original_subject.lower().startswith("re:"):
            reply_subject = f"Re: {original_subject}"
        else:
            reply_subject = original_subject
        
        # Create reply message
        reply_message = MIMEMultipart("alternative")
        reply_message["to"] = original_from
        reply_message["subject"] = reply_subject
        reply_message["In-Reply-To"] = message_id
        reply_message["References"] = message_id
        
        # Add body with quoted original
        full_body = f"""{body}

---
On {datetime.now().strftime("%Y-%m-%d")}, you wrote:
"""
        
        reply_message.attach(MIMEText(full_body, "plain"))
        reply_message.attach(MIMEText(full_body.replace("\n", "<br>"), "html"))
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(reply_message.as_bytes()).decode("utf-8")
        
        # Check for approval
        if require_approval:
            is_approved, approval_file = check_email_approval(original_from, reply_subject)
            
            if not is_approved:
                # Create approval request
                approval_path = create_email_approval_request(
                    original_from,
                    reply_subject,
                    body,
                    "reply_to_email"
                )
                
                if approval_path:
                    log_action("reply_approval_required", f"Approval needed for reply to {original_from}")
                    print(f"APPROVAL REQUIRED: Created {approval_path.name}")
                    print("Move file to Approved folder to send this reply")
                    
                    # Still create the draft
                    draft = service.users().drafts().create(
                        userId="me",
                        body={"message": {"raw": raw_message}}
                    ).execute()
                    
                    return {
                        "success": True,
                        "draft_id": draft.get("id"),
                        "error": None,
                        "approval_required": True,
                        "approval_file": str(approval_path),
                        "message": f"Draft created. Approval required to send."
                    }
        
        # Create draft
        draft = service.users().drafts().create(
            userId="me",
            body={"message": {"raw": raw_message}}
        ).execute()
        
        draft_id = draft.get("id")
        
        log_action("reply_draft_created", f"Reply draft created for {original_from}: {reply_subject[:50]}")
        
        return {
            "success": True,
            "draft_id": draft_id,
            "error": None,
            "message": f"Reply draft created with ID: {draft_id}"
        }
        
    except HttpError as error:
        error_msg = f"Gmail API error: {error}"
        log_action("reply_error", error_msg, success=False)
        return {"success": False, "draft_id": None, "error": error_msg}
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        log_action("reply_error", error_msg, success=False)
        return {"success": False, "draft_id": None, "error": error_msg}


def get_email_stats():
    """Get current email statistics"""
    return {
        "drafted_today": email_stats["drafted_today"],
        "sent_today": email_stats["sent_today"],
        "pending_approvals": email_stats["pending_approvals"],
        "last_action": email_stats["last_action"],
        "last_action_time": email_stats["last_action_time"]
    }


def update_dashboard():
    """Update Dashboard.md with email MCP status"""
    dashboard_file = VAULT_PATH / "Dashboard.md"
    
    # Count pending email approvals
    pending_count = len(list(PENDING_APPROVAL_FOLDER.glob("APPROVAL_EMAIL_*.md")))
    email_stats["pending_approvals"] = pending_count
    
    if not dashboard_file.exists():
        return False
    
    try:
        with open(dashboard_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        email_section = f"""## Email MCP Status
- Emails Drafted Today: {email_stats["drafted_today"]}
- Emails Sent Today: {email_stats["sent_today"]}
- Pending Email Approvals: {email_stats["pending_approvals"]}
- Last Email Action: {email_stats["last_action"]}
"""
        
        if "## Email MCP Status" in content:
            import re
            pattern = r"## Email MCP Status.*?(?=## |\Z)"
            content = re.sub(pattern, email_section, content, flags=re.DOTALL)
        else:
            if "---" in content:
                parts = content.rsplit("---", 1)
                content = parts[0] + email_section + "\n---" + parts[1] if len(parts) > 1 else content + "\n" + email_section
            else:
                content = content + "\n" + email_section
        
        with open(dashboard_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
    except Exception as e:
        log_action("dashboard_error", f"Failed to update dashboard: {e}", success=False)
        return False


# Main entry point for MCP server mode
def main():
    """Main function - runs in MCP server mode or standalone"""
    ensure_folders_exist()
    
    print("=" * 60)
    print("Email MCP Server - Gmail Integration with HITL Approval")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Credentials: {CREDENTIALS_FILE.exists()}")
    print(f"Token: {TOKEN_FILE.exists()}")
    print("=" * 60)
    
    # Update dashboard
    update_dashboard()
    
    print("\nEmail MCP Server ready.")
    print("\nAvailable functions:")
    print("  - draft_email(to, subject, body)")
    print("  - send_email(to, subject, body)")
    print("  - search_emails(query, max_results)")
    print("  - get_email_content(message_id)")
    print("  - reply_to_email(message_id, body)")
    print("\nAll send actions require human approval.")
    print("Run test_email_mcp.py to test functions.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nEmail MCP Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
