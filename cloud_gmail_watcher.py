#!/usr/bin/env python3
"""
Cloud Gmail Watcher - Platinum Tier
Monitors Gmail for new important emails and creates markdown files in GitHub repo

Key Differences from Local Version:
- Writes files to GitHub repo via GitHub API instead of local vault
- Uses GITHUB_TOKEN and GITHUB_REPO environment variables
- Creates files in Needs_Action/ folder in GitHub repository
- Full error handling with retry logic
- Runs continuously, checking every 2 minutes (configurable)

Environment Variables:
    GITHUB_TOKEN: GitHub personal access token (required)
    GITHUB_REPO: GitHub repository in format user/repo (required)
    GITHUB_BRANCH: GitHub branch name (default: main)
    GMAIL_CHECK_INTERVAL: Check interval in seconds (default: 120)
    DRY_RUN: Enable dry run mode (default: true)
"""

import os
import sys
import time
import json
import base64
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests

# Load environment variables
load_dotenv()

# Configuration from environment
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
CHECK_INTERVAL = int(os.getenv("GMAIL_CHECK_INTERVAL", "120"))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# Local paths for credentials and logs
VAULT_PATH = os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault")
CREDENTIALS_FILE = os.path.join(VAULT_PATH, "credentials.json")
TOKEN_FILE = os.path.join(VAULT_PATH, "token.json")
LOGS_FOLDER = os.path.join(VAULT_PATH, "Logs")

# Ensure logs folder exists
os.makedirs(LOGS_FOLDER, exist_ok=True)

# Gmail API scopes
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# GitHub API endpoints
GITHUB_API_BASE = "https://api.github.com"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_FOLDER, f"cloud_gmail_watcher_{datetime.now().strftime('%Y-%m-%d')}.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cloud_gmail_watcher")


# =============================================================================
# RETRY DECORATOR
# =============================================================================

def with_retry(max_attempts: int = 3, base_delay: float = 2.0, name: str = ""):
    """Decorator for retry with exponential backoff"""
    def decorator(func):
        import functools
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = name or func.__name__
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    logger.debug(f"[{func_name}] Attempt {attempt}/{max_attempts}")
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    # Don't retry on auth errors
                    if isinstance(e, (AuthError,)) or "401" in str(e):
                        logger.error(f"[{func_name}] Auth error, not retrying: {e}")
                        raise
                    
                    if attempt >= max_attempts:
                        logger.error(f"[{func_name}] All {max_attempts} attempts failed: {e}")
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(f"[{func_name}] Attempt {attempt} failed: {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
            
            if last_exception:
                raise last_exception
        return wrapper
    return decorator


class AuthError(Exception):
    """Authentication error"""
    pass


# =============================================================================
# GITHUB API CLIENT
# =============================================================================

class GitHubClient:
    """Simple GitHub API client for file operations"""
    
    def __init__(self, token: str, repo: str, branch: str = "main"):
        """
        Initialize GitHub client
        
        Args:
            token: GitHub personal access token
            repo: Repository in format user/repo
            branch: Branch name
        """
        self.token = token
        self.repo = repo
        self.branch = branch
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        })
        
        # Cache for file SHAs
        self._sha_cache: Dict[str, str] = {}
    
    def _get_repo_path(self, path: str) -> str:
        """Get full API path for repository file"""
        return f"{GITHUB_API_BASE}/repos/{self.repo}/contents/{path}"
    
    @with_retry(max_attempts=3, base_delay=1.0, name="github_get_file")
    def get_file(self, path: str) -> Optional[Dict[str, Any]]:
        """
        Get file content from GitHub
        
        Args:
            path: File path in repository
            
        Returns:
            Dict with content and metadata, or None if not found
        """
        try:
            response = self.session.get(self._get_repo_path(path), params={"ref": self.branch})
            
            if response.status_code == 404:
                return None
            elif response.status_code != 200:
                logger.error(f"GitHub API error ({response.status_code}): {response.text[:200]}")
                return None
            
            data = response.json()
            
            # Decode content if present
            if "content" in data and data.get("encoding") == "base64":
                data["decoded_content"] = base64.b64decode(data["content"]).decode("utf-8")
            
            # Cache SHA for updates
            self._sha_cache[path] = data.get("sha", "")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"Failed to get file {path}: {e}")
            return None
    
    @with_retry(max_attempts=3, base_delay=2.0, name="github_create_file")
    def create_file(self, path: str, content: str, message: str) -> bool:
        """
        Create a new file in GitHub repository
        
        Args:
            path: File path in repository
            content: File content
            message: Commit message
            
        Returns:
            True if successful
        """
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Would create file: {path}")
            return True
        
        try:
            # Encode content to base64
            content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            
            payload = {
                "message": message,
                "content": content_b64,
                "branch": self.branch
            }
            
            response = self.session.put(self._get_repo_path(path), json=payload)
            
            if response.status_code in (200, 201):
                logger.info(f"Created file: {path}")
                return True
            else:
                logger.error(f"Failed to create file {path}: {response.status_code} - {response.text[:200]}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to create file {path}: {e}")
            return False
    
    @with_retry(max_attempts=3, base_delay=2.0, name="github_update_file")
    def update_file(self, path: str, content: str, message: str, sha: Optional[str] = None) -> bool:
        """
        Update an existing file in GitHub repository
        
        Args:
            path: File path in repository
            content: New file content
            message: Commit message
            sha: File SHA (required for updates)
            
        Returns:
            True if successful
        """
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Would update file: {path}")
            return True
        
        # Get SHA if not provided
        if not sha:
            file_data = self.get_file(path)
            if not file_data:
                logger.error(f"Cannot update {path}: file not found")
                return False
            sha = file_data.get("sha")
        
        try:
            content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            
            payload = {
                "message": message,
                "content": content_b64,
                "branch": self.branch,
                "sha": sha
            }
            
            response = self.session.put(self._get_repo_path(path), json=payload)
            
            if response.status_code in (200, 201):
                logger.info(f"Updated file: {path}")
                # Update cache
                result = response.json()
                if "content" in result and "sha" in result["content"]:
                    self._sha_cache[path] = result["content"]["sha"]
                return True
            else:
                logger.error(f"Failed to update file {path}: {response.status_code} - {response.text[:200]}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to update file {path}: {e}")
            return False
    
    @with_retry(max_attempts=3, base_delay=2.0, name="github_delete_file")
    def delete_file(self, path: str, message: str, sha: Optional[str] = None) -> bool:
        """
        Delete a file from GitHub repository
        
        Args:
            path: File path in repository
            message: Commit message
            sha: File SHA (required)
            
        Returns:
            True if successful
        """
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Would delete file: {path}")
            return True
        
        # Get SHA if not provided
        if not sha:
            file_data = self.get_file(path)
            if not file_data:
                logger.warning(f"File not found for deletion: {path}")
                return False
            sha = file_data.get("sha")
        
        try:
            payload = {
                "message": message,
                "branch": self.branch,
                "sha": sha
            }
            
            response = self.session.delete(self._get_repo_path(path), json=payload)
            
            if response.status_code in (200, 201):
                logger.info(f"Deleted file: {path}")
                # Remove from cache
                self._sha_cache.pop(path, None)
                return True
            else:
                logger.error(f"Failed to delete file {path}: {response.status_code} - {response.text[:200]}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to delete file {path}: {e}")
            return False
    
    @with_retry(max_attempts=3, base_delay=2.0, name="github_list_folder")
    def list_folder(self, path: str) -> List[Dict[str, Any]]:
        """
        List contents of a folder in GitHub repository
        
        Args:
            path: Folder path in repository
            
        Returns:
            List of file/folder metadata
        """
        try:
            response = self.session.get(self._get_repo_path(path), params={"ref": self.branch})
            
            if response.status_code == 404:
                return []
            elif response.status_code != 200:
                logger.error(f"GitHub API error ({response.status_code}): {response.text[:200]}")
                return []
            
            data = response.json()
            if isinstance(data, list):
                return data
            return []
            
        except requests.RequestException as e:
            logger.error(f"Failed to list folder {path}: {e}")
            return []
    
    def clear_sha_cache(self):
        """Clear the SHA cache"""
        self._sha_cache.clear()


# =============================================================================
# GMAIL SERVICE
# =============================================================================

@dataclass
class EmailData:
    """Email data structure"""
    message_id: str
    subject: str
    from_email: str
    snippet: str
    body: str
    received_date: str


class GmailService:
    """Gmail API service with authentication"""
    
    def __init__(self, credentials_file: str, token_file: str):
        """
        Initialize Gmail service
        
        Args:
            credentials_file: Path to credentials.json
            token_file: Path to token.json
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.service = None
        self.processed_message_ids: set = set()
    
    def authenticate(self) -> bool:
        """
        Authenticate with Gmail API
        
        Returns:
            True if authentication successful
        """
        try:
            creds = None
            
            # Load existing token
            if os.path.exists(self.token_file):
                try:
                    creds = Credentials.from_authorized_user_file(self.token_file, SCOPES)
                except Exception as e:
                    logger.warning(f"Failed to load token: {e}")
                    creds = None
            
            # Refresh or obtain new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as e:
                        logger.error(f"Token refresh failed: {e}")
                        creds = None
                
                if not creds:
                    if not os.path.exists(self.credentials_file):
                        logger.error(f"credentials.json not found at {self.credentials_file}")
                        return False
                    
                    logger.info("Starting OAuth flow. Please complete authentication...")
                    flow = InstalledAppFlow.from_client_secrets_file(self.credentials_file, SCOPES)
                    creds = flow.run_local_server(port=0)
                    
                    # Save token
                    os.makedirs(os.path.dirname(self.token_file), exist_ok=True)
                    with open(self.token_file, "w", encoding="utf-8") as f:
                        f.write(creds.to_json())
                    logger.info("OAuth token saved")
            
            self.service = build("gmail", "v1", credentials=creds)
            logger.info("Gmail service authenticated")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def load_processed_ids(self, processed_file: str):
        """Load previously processed message IDs"""
        if os.path.exists(processed_file):
            try:
                with open(processed_file, "r", encoding="utf-8") as f:
                    self.processed_message_ids = set(json.load(f))
                logger.info(f"Loaded {len(self.processed_message_ids)} processed message IDs")
            except Exception as e:
                logger.warning(f"Failed to load processed IDs: {e}")
    
    def save_processed_ids(self, processed_file: str):
        """Save processed message IDs"""
        try:
            with open(processed_file, "w", encoding="utf-8") as f:
                json.dump(list(self.processed_message_ids), f)
        except Exception as e:
            logger.warning(f"Failed to save processed IDs: {e}")
    
    def _decode_email_part(self, part: Dict) -> str:
        """Decode email part data"""
        data = part.get("data", "")
        if data:
            try:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            except Exception:
                return ""
        return ""
    
    def extract_email_content(self, message: Dict) -> EmailData:
        """Extract email content from Gmail message"""
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
        
        # Extract body
        body = ""
        payload = message.get("payload", {})
        
        if "body" in payload and payload["body"].get("data"):
            body = self._decode_email_part(payload)
        elif "parts" in payload:
            for part in payload["parts"]:
                mime_type = part.get("mimeType", "")
                if mime_type == "text/plain":
                    body = self._decode_email_part(part)
                    break
                elif mime_type == "text/html" and not body:
                    body = self._decode_email_part(part)
        
        return EmailData(
            message_id=message.get("id", ""),
            subject=subject,
            from_email=from_email,
            snippet=snippet,
            body=body[:1000] if body else snippet,  # Limit body length
            received_date=""  # Will be set later
        )
    
    @with_retry(max_attempts=3, base_delay=2.0, name="gmail_list_messages")
    def list_unread_messages(self, max_results: int = 10) -> List[Dict]:
        """List unread Gmail messages"""
        if not self.service:
            return []
        
        try:
            results = self.service.users().messages().list(
                userId="me",
                labelIds=["UNREAD"],
                maxResults=max_results
            ).execute()
            
            return results.get("messages", [])
            
        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return []
        except Exception as e:
            logger.error(f"Failed to list messages: {e}")
            return []
    
    @with_retry(max_attempts=3, base_delay=2.0, name="gmail_get_message")
    def get_message(self, message_id: str, format_type: str = "full") -> Optional[Dict]:
        """Get full Gmail message"""
        if not self.service:
            return None
        
        try:
            msg = self.service.users().messages().get(
                userId="me",
                id=message_id,
                format=format_type
            ).execute()
            return msg
            
        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return None
        except Exception as e:
            logger.error(f"Failed to get message: {e}")
            return None


# =============================================================================
# CLOUD GMAIL WATCHER
# =============================================================================

class CloudGmailWatcher:
    """
    Cloud Gmail Watcher - Platinum Tier
    
    Monitors Gmail and creates markdown files in GitHub repository
    """
    
    def __init__(
        self,
        github_token: str,
        github_repo: str,
        github_branch: str = "main",
        check_interval: int = 120,
        dry_run: bool = True
    ):
        """
        Initialize Cloud Gmail Watcher
        
        Args:
            github_token: GitHub personal access token
            github_repo: GitHub repository (user/repo)
            github_branch: GitHub branch
            check_interval: Check interval in seconds
            dry_run: Enable dry run mode
        """
        self.github_token = github_token
        self.github_repo = github_repo
        self.github_branch = github_branch
        self.check_interval = check_interval
        self.dry_run = dry_run
        
        # Initialize clients
        self.github = None
        self.gmail = None
        
        # State
        self.iteration = 0
        self.running = False
        self.processed_file = os.path.join(VAULT_PATH, ".processed_emails_cloud.json")
        
        # Folder paths in GitHub
        self.needs_action_folder = "Needs_Action"
    
    def initialize(self) -> bool:
        """Initialize GitHub and Gmail clients"""
        # Validate configuration
        if not self.github_token:
            logger.error("GITHUB_TOKEN not set")
            return False
        
        if not self.github_repo:
            logger.error("GITHUB_REPO not set")
            return False
        
        # Initialize GitHub client
        try:
            self.github = GitHubClient(
                token=self.github_token,
                repo=self.github_repo,
                branch=self.github_branch
            )
            logger.info(f"GitHub client initialized for {self.github_repo}")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            return False
        
        # Initialize Gmail service
        try:
            self.gmail = GmailService(
                credentials_file=CREDENTIALS_FILE,
                token_file=TOKEN_FILE
            )
            
            if not self.gmail.authenticate():
                logger.error("Gmail authentication failed")
                return False
            
            # Load processed IDs
            self.gmail.load_processed_ids(self.processed_file)
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            return False
        
        return True
    
    def create_email_markdown(self, email: EmailData) -> str:
        """Create markdown content for email"""
        # Sanitize message_id for filename
        safe_id = email.message_id.replace("/", "_").replace("+", "_")
        
        # Create YAML frontmatter
        frontmatter = f"""---
type: email
from: {email.from_email}
subject: {email.subject}
received: {email.received_date}
status: pending
message_id: {email.message_id}
cloud_created: true
---

# Email: {email.subject}

**From:** {email.from_email}
**Received:** {email.received_date}
**Status:** Pending

---

## Email Content

{email.body if email.body else email.snippet}

---

## Suggested Actions

- [ ] Draft reply
- [ ] Flag for human review
- [ ] Mark as processed
- [ ] Create follow-up task

---

*Created by Cloud Gmail Watcher at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        return frontmatter
    
    def check_gmail(self) -> int:
        """
        Check Gmail for new unread emails and create files in GitHub
        
        Returns:
            Number of new emails processed
        """
        if not self.gmail or not self.github:
            logger.error("Services not initialized")
            return 0
        
        try:
            # List unread messages
            messages = self.gmail.list_unread_messages(max_results=10)
            
            if not messages:
                logger.info("No new unread emails found")
                return 0
            
            new_count = 0
            
            for message in messages:
                message_id = message["id"]
                
                # Skip if already processed
                if message_id in self.gmail.processed_message_ids:
                    continue
                
                # Get full message
                msg = self.gmail.get_message(message_id, format_type="metadata")
                if not msg:
                    continue
                
                # Get internal date
                internal_date = msg.get("internalDate", "")
                if internal_date:
                    received_date = datetime.fromtimestamp(
                        int(internal_date) / 1000
                    ).strftime("%Y-%m-%d %H:%M:%S")
                else:
                    received_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # Get full message content
                msg_full = self.gmail.get_message(message_id, format_type="full")
                if not msg_full:
                    continue
                
                # Extract email data
                email_data = self.gmail.extract_email_content(msg_full)
                email_data.received_date = received_date
                
                # Create markdown content
                markdown_content = self.create_email_markdown(email_data)
                
                # Create filename
                safe_id = message_id.replace("/", "_").replace("+", "_")
                filename = f"EMAIL_{safe_id}.md"
                filepath = f"{self.needs_action_folder}/{filename}"
                
                # Check if file already exists in GitHub
                existing = self.github.get_file(filepath)
                if existing:
                    logger.info(f"Email file already exists: {filename}")
                    self.gmail.processed_message_ids.add(message_id)
                    continue
                
                # Create file in GitHub
                commit_message = f"New email: {email_data.subject[:50]}"
                
                if self.github.create_file(filepath, markdown_content, commit_message):
                    self.gmail.processed_message_ids.add(message_id)
                    new_count += 1
                    logger.info(f"Created email file in GitHub: {filename}")
                else:
                    logger.error(f"Failed to create file in GitHub: {filename}")
            
            # Save processed IDs
            self.gmail.save_processed_ids(self.processed_file)
            
            return new_count
            
        except Exception as e:
            logger.error(f"Error checking Gmail: {e}")
            return 0
    
    def run(self):
        """Main run loop - continuous monitoring"""
        logger.info("=" * 60)
        logger.info("Cloud Gmail Watcher Started")
        logger.info(f"GitHub Repo: {self.github_repo}")
        logger.info(f"GitHub Branch: {self.github_branch}")
        logger.info(f"Check Interval: {self.check_interval} seconds")
        logger.info(f"DRY_RUN: {self.dry_run}")
        logger.info("=" * 60)
        
        # Initialize services
        if not self.initialize():
            logger.error("Failed to initialize services. Exiting.")
            return
        
        self.running = True
        self.iteration = 0
        
        logger.info("Starting continuous monitoring...")
        
        try:
            while self.running:
                self.iteration += 1
                logger.info(f"\n--- Check #{self.iteration} ---")
                
                try:
                    new_count = self.check_gmail()
                    logger.info(f"Processed {new_count} new email(s)")
                except Exception as e:
                    logger.error(f"Error in check cycle: {e}")
                
                # Wait for next check
                logger.info(f"Next check in {self.check_interval} seconds...")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.running = False
            logger.info("Cloud Gmail Watcher stopped")
    
    def stop(self):
        """Stop the watcher"""
        self.running = False


def main():
    """Main entry point"""
    print("=" * 60)
    print("Cloud Gmail Watcher - Platinum Tier")
    print("=" * 60)
    
    # Create and run watcher
    watcher = CloudGmailWatcher(
        github_token=GITHUB_TOKEN,
        github_repo=GITHUB_REPO,
        github_branch=GITHUB_BRANCH,
        check_interval=CHECK_INTERVAL,
        dry_run=DRY_RUN
    )
    
    try:
        watcher.run()
    except KeyboardInterrupt:
        print("\nStopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
