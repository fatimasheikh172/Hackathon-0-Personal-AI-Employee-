#!/usr/bin/env python3
"""
Gmail Watcher - Monitors Gmail for new important emails
Creates markdown files in Needs_Action folder for each new email
Updated with @with_retry decorator for resilient operations
"""

import os
import sys
import time
import json
import base64
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import retry handler
from retry_handler import with_retry, TransientError, AuthError, get_retry_stats

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
CREDENTIALS_FILE = VAULT_PATH / "credentials.json"
TOKEN_FILE = VAULT_PATH / "token.json"
NEEDS_ACTION_FOLDER = VAULT_PATH / "Needs_Action"
LOGS_FOLDER = VAULT_PATH / "Logs"
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "120"))

# Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Track processed message IDs to avoid duplicates
processed_message_ids = set()


def get_log_file_path():
    """Get log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"gmail_watcher_{date_str}.log"


def log_message(message):
    """Write log message to file and console"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    
    try:
        LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(get_log_file_path(), "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"Warning: Could not write to log file: {e}")


@with_retry(max_attempts=3, base_delay=2.0, name="get_gmail_service")
def get_gmail_service():
    """Authenticate and build Gmail API service"""
    creds = None
    
    # Load existing token if available
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # Refresh or obtain new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                log_message(f"Token refresh failed: {e}")
                creds = None
        
        if not creds:
            if not CREDENTIALS_FILE.exists():
                log_message(f"ERROR: credentials.json not found at {CREDENTIALS_FILE}")
                log_message("Please ensure credentials.json exists in the vault folder")
                return None
            
            log_message("Starting OAuth flow. Please complete authentication in your browser...")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
            # Save credentials for future use
            with open(TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            log_message("OAuth token saved to token.json")
    
    return build("gmail", "v1", credentials=creds)


def decode_email_part(part):
    """Decode email part data"""
    data = part.get("data", "")
    if data:
        try:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        except Exception:
            return ""
    return ""


def extract_email_content(message):
    """Extract subject, from, snippet, and body from Gmail message"""
    headers = message.get("payload", {}).get("headers", [])
    
    subject = ""
    from_email = ""
    
    for header in headers:
        name = header.get("name", "").lower()
        if name == "subject":
            subject = header.get("value", "")
        elif name == "from":
            from_email = header.get("value", "")
    
    snippet = message.get("snippet", "")
    
    # Try to extract body
    body = ""
    payload = message.get("payload", {})
    
    if "body" in payload and payload["body"].get("data"):
        body = decode_email_part(payload)
    elif "parts" in payload:
        for part in payload["parts"]:
            mime_type = part.get("mimeType", "")
            if mime_type == "text/plain":
                body = decode_email_part(part)
                break
            elif mime_type == "text/html" and not body:
                body = decode_email_part(part)
    
    return {
        "subject": subject,
        "from": from_email,
        "snippet": snippet,
        "body": body[:500] if body else snippet  # Limit body length
    }


def create_email_markdown_file(message_id, email_data, received_date):
    """Create markdown file in Needs_Action folder"""
    # Sanitize message_id for filename
    safe_id = message_id.replace("/", "_").replace("+", "_")
    filename = f"EMAIL_{safe_id}.md"
    filepath = NEEDS_ACTION_FOLDER / filename
    
    # Create YAML frontmatter
    frontmatter = f"""---
type: email
from: {email_data['from']}
subject: {email_data['subject']}
received: {received_date}
status: pending
message_id: {message_id}
---

# Email: {email_data['subject']}

**From:** {email_data['from']}  
**Received:** {received_date}  
**Status:** Pending

---

## Email Content

{email_data['body'] if email_data['body'] else email_data['snippet']}

---

## Suggested Actions

- [ ] Draft reply
- [ ] Flag for human review
- [ ] Mark as processed
- [ ] Create follow-up task

---

*Created by Gmail Watcher at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
    
    try:
        NEEDS_ACTION_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(frontmatter)
        log_message(f"Created email file: {filename}")
        return True
    except Exception as e:
        log_message(f"ERROR creating file {filename}: {e}")
        return False


def check_gmail(service):
    """Check Gmail for new unread important emails"""
    try:
        # Search for unread emails
        results = service.users().messages().list(
            userId="me",
            labelIds=["UNREAD"],
            maxResults=10
        ).execute()
        
        messages = results.get("messages", [])
        
        if not messages:
            log_message("No new unread emails found")
            return 0
        
        new_emails_count = 0
        
        for message in messages:
            message_id = message["id"]
            
            # Skip if already processed
            if message_id in processed_message_ids:
                continue
            
            # Get full message details
            msg = service.users().messages().get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=["From", "Subject"]
            ).execute()
            
            # Get internal date
            internal_date = msg.get("internalDate", "")
            if internal_date:
                received_date = datetime.fromtimestamp(int(internal_date) / 1000).strftime("%Y-%m-%d %H:%M:%S")
            else:
                received_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get full message for content
            msg_full = service.users().messages().get(
                userId="me",
                id=message_id,
                format="full"
            ).execute()
            
            email_data = extract_email_content(msg_full)
            
            # Create markdown file
            if create_email_markdown_file(message_id, email_data, received_date):
                processed_message_ids.add(message_id)
                new_emails_count += 1
        
        return new_emails_count
        
    except HttpError as error:
        log_message(f"Gmail API error: {error}")
        return 0
    except Exception as e:
        log_message(f"ERROR checking Gmail: {e}")
        return 0


def main():
    """Main function - runs Gmail watcher in infinite loop"""
    log_message("=" * 50)
    log_message("Gmail Watcher Started")
    log_message(f"Vault Path: {VAULT_PATH}")
    log_message(f"Check Interval: {CHECK_INTERVAL} seconds")
    log_message("=" * 50)
    
    # Ensure folders exist
    NEEDS_ACTION_FOLDER.mkdir(parents=True, exist_ok=True)
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Load previously processed message IDs if available
    processed_file = VAULT_PATH / ".processed_emails.json"
    if processed_file.exists():
        try:
            with open(processed_file, "r", encoding="utf-8") as f:
                processed_message_ids.update(json.load(f))
            log_message(f"Loaded {len(processed_message_ids)} previously processed email IDs")
        except Exception as e:
            log_message(f"Warning: Could not load processed emails file: {e}")
    
    iteration = 0
    
    while True:
        iteration += 1
        log_message(f"\n--- Check #{iteration} ---")
        
        try:
            service = get_gmail_service()
            
            if service:
                new_count = check_gmail(service)
                log_message(f"Processed {new_count} new email(s)")
                
                # Save processed message IDs
                try:
                    with open(processed_file, "w", encoding="utf-8") as f:
                        json.dump(list(processed_message_ids), f)
                except Exception as e:
                    log_message(f"Warning: Could not save processed emails: {e}")
            else:
                log_message("Gmail service not available, will retry...")
                
        except Exception as e:
            log_message(f"ERROR in main loop: {e}")
        
        # Wait for next check
        log_message(f"Next check in {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("\nGmail Watcher stopped by user")
        sys.exit(0)
    except Exception as e:
        log_message(f"Fatal error: {e}")
        sys.exit(1)
