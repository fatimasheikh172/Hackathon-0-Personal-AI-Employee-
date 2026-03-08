#!/usr/bin/env python3
"""
Cloud Orchestrator - Platinum Tier
Main coordinator for AI Employee system running in the cloud

Key Differences from Local Version:
- Reads files from GitHub repository instead of local vault
- Writes approval requests to Pending_Approval/ via GitHub API
- Creates drafts only - NEVER sends directly
- Syncs every 5 minutes (configurable)
- All actions logged to GitHub and console

Environment Variables:
    GITHUB_TOKEN: GitHub personal access token (required)
    GITHUB_REPO: GitHub repository in format user/repo (required)
    GITHUB_BRANCH: GitHub branch name (default: main)
    ORCHESTRATOR_SYNC_INTERVAL: Sync interval in seconds (default: 300)
    DRY_RUN: Enable dry run mode (default: true)
"""

import os
import sys
import time
import json
import base64
import logging
import re
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Configuration from environment
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")
SYNC_INTERVAL = int(os.getenv("ORCHESTRATOR_SYNC_INTERVAL", "300"))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

# Local paths for logs
VAULT_PATH = os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault")
LOGS_FOLDER = os.path.join(VAULT_PATH, "Logs")

# Ensure logs folder exists
os.makedirs(LOGS_FOLDER, exist_ok=True)

# GitHub API endpoints
GITHUB_API_BASE = "https://api.github.com"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_FOLDER, f"cloud_orchestrator_{datetime.now().strftime('%Y-%m-%d')}.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cloud_orchestrator")


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
        self.token = token
        self.repo = repo
        self.branch = branch
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        })
        self._sha_cache: Dict[str, str] = {}
    
    def _get_repo_path(self, path: str) -> str:
        return f"{GITHUB_API_BASE}/repos/{self.repo}/contents/{path}"
    
    @with_retry(max_attempts=3, base_delay=1.0, name="github_get_file")
    def get_file(self, path: str) -> Optional[Dict[str, Any]]:
        """Get file content from GitHub"""
        try:
            response = self.session.get(self._get_repo_path(path), params={"ref": self.branch})
            
            if response.status_code == 404:
                return None
            elif response.status_code != 200:
                logger.error(f"GitHub API error ({response.status_code}): {response.text[:200]}")
                return None
            
            data = response.json()
            
            if "content" in data and data.get("encoding") == "base64":
                data["decoded_content"] = base64.b64decode(data["content"]).decode("utf-8")
            
            self._sha_cache[path] = data.get("sha", "")
            return data
            
        except requests.RequestException as e:
            logger.error(f"Failed to get file {path}: {e}")
            return None
    
    @with_retry(max_attempts=3, base_delay=2.0, name="github_create_file")
    def create_file(self, path: str, content: str, message: str) -> bool:
        """Create a new file in GitHub repository"""
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Would create file: {path}")
            return True
        
        try:
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
        """Update an existing file in GitHub repository"""
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Would update file: {path}")
            return True
        
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
    
    @with_retry(max_attempts=3, base_delay=2.0, name="github_list_folder")
    def list_folder(self, path: str) -> List[Dict[str, Any]]:
        """List contents of a folder in GitHub repository"""
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
# DATA STRUCTURES
# =============================================================================

class FileType(Enum):
    """Types of files in the vault"""
    EMAIL = "email"
    FILE = "file"
    APPROVAL = "approval"
    UNKNOWN = "unknown"


class FileStatus(Enum):
    """Status of files in the workflow"""
    PENDING = "pending"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    DONE = "done"


@dataclass
class VaultFile:
    """Represents a file in the vault"""
    path: str
    name: str
    content: str
    sha: str
    file_type: FileType
    status: FileStatus
    frontmatter: Dict[str, str]
    created_at: str
    updated_at: str


# =============================================================================
# CLOUD ORCHESTRATOR
# =============================================================================

class CloudOrchestrator:
    """
    Cloud Orchestrator - Platinum Tier
    
    Coordinates AI Employee system components via GitHub repository
    """
    
    def __init__(
        self,
        github_token: str,
        github_repo: str,
        github_branch: str = "main",
        sync_interval: int = 300,
        dry_run: bool = True
    ):
        self.github_token = github_token
        self.github_repo = github_repo
        self.github_branch = github_branch
        self.sync_interval = sync_interval
        self.dry_run = dry_run
        
        self.github = None
        self.iteration = 0
        self.running = False
        
        # Folder paths in GitHub
        self.needs_action_folder = "Needs_Action"
        self.pending_approval_folder = "Pending_Approval"
        self.approved_folder = "Approved"
        self.rejected_folder = "Rejected"
        self.done_folder = "Done"
        self.updates_folder = "Updates"
        
        # Statistics
        self.stats = {
            "files_processed": 0,
            "approvals_created": 0,
            "errors": 0,
            "cycles": 0
        }
    
    def initialize(self) -> bool:
        """Initialize GitHub client"""
        if not self.github_token:
            logger.error("GITHUB_TOKEN not set")
            return False
        
        if not self.github_repo:
            logger.error("GITHUB_REPO not set")
            return False
        
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
        
        return True
    
    def parse_yaml_frontmatter(self, content: str) -> Dict[str, str]:
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
    
    def detect_file_type(self, filename: str, content: str) -> FileType:
        """Detect file type from filename and content"""
        frontmatter = self.parse_yaml_frontmatter(content)
        
        if filename.startswith("EMAIL_"):
            return FileType.EMAIL
        elif filename.startswith("FILE_"):
            return FileType.FILE
        elif filename.startswith("APPROVAL_"):
            return FileType.APPROVAL
        
        file_type = frontmatter.get("type", "").lower()
        if file_type == "email":
            return FileType.EMAIL
        elif file_type == "file":
            return FileType.FILE
        elif file_type == "approval":
            return FileType.APPROVAL
        
        return FileType.UNKNOWN
    
    def detect_file_status(self, path: str, frontmatter: Dict[str, str]) -> FileStatus:
        """Detect file status from path and frontmatter"""
        if path.startswith(self.pending_approval_folder):
            return FileStatus.PENDING
        elif path.startswith(self.approved_folder):
            return FileStatus.APPROVED
        elif path.startswith(self.rejected_folder):
            return FileStatus.REJECTED
        elif path.startswith(self.done_folder):
            return FileStatus.DONE
        
        status = frontmatter.get("status", "pending").lower()
        if status == "pending":
            return FileStatus.PENDING
        elif status == "processing":
            return FileStatus.PROCESSING
        elif status == "approved":
            return FileStatus.APPROVED
        elif status == "rejected":
            return FileStatus.REJECTED
        
        return FileStatus.PENDING
    
    def read_vault_file(self, file_info: Dict[str, Any]) -> Optional[VaultFile]:
        """Read and parse a file from GitHub"""
        path = file_info.get("path", "")
        name = file_info.get("name", "")
        sha = file_info.get("sha", "")
        
        # Get file content
        file_data = self.github.get_file(path)
        if not file_data or "decoded_content" not in file_data:
            logger.error(f"Failed to read file content: {path}")
            return None
        
        content = file_data["decoded_content"]
        frontmatter = self.parse_yaml_frontmatter(content)
        file_type = self.detect_file_type(name, content)
        status = self.detect_file_status(path, frontmatter)
        
        return VaultFile(
            path=path,
            name=name,
            content=content,
            sha=sha,
            file_type=file_type,
            status=status,
            frontmatter=frontmatter,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
    
    def scan_needs_action(self) -> List[VaultFile]:
        """Scan Needs_Action folder for pending files"""
        files = []
        
        try:
            items = self.github.list_folder(self.needs_action_folder)
            
            for item in items:
                if item.get("type") == "file" and item.get("name", "").endswith(".md"):
                    vault_file = self.read_vault_file(item)
                    if vault_file:
                        files.append(vault_file)
                        
        except Exception as e:
            logger.error(f"Error scanning Needs_Action: {e}")
        
        return files
    
    def scan_pending_approvals(self) -> List[VaultFile]:
        """Scan Pending_Approval folder for files awaiting approval"""
        files = []
        
        try:
            items = self.github.list_folder(self.pending_approval_folder)
            
            for item in items:
                if item.get("type") == "file" and item.get("name", "").endswith(".md"):
                    vault_file = self.read_vault_file(item)
                    if vault_file:
                        files.append(vault_file)
                        
        except Exception as e:
            logger.error(f"Error scanning Pending_Approval: {e}")
        
        return files
    
    def requires_approval(self, content: str) -> bool:
        """Check if content requires human approval based on sensitive keywords"""
        sensitive_keywords = [
            "payment", "invoice", "urgent", "asap", "delete", "send money",
            "bank", "transfer", "wire", "refund", "cancel", "terminate",
            "contract", "legal", "settlement", "confidential"
        ]
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in sensitive_keywords)
    
    def create_approval_request(self, vault_file: VaultFile) -> bool:
        """
        Create an approval request in Pending_Approval folder
        
        Args:
            vault_file: File to create approval request for
            
        Returns:
            True if successful
        """
        # Create approval filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        approval_filename = f"APPROVAL_{vault_file.name}_{timestamp}.md"
        approval_path = f"{self.pending_approval_folder}/{approval_filename}"
        
        # Create approval request content
        approval_content = f"""---
type: approval_request
original_file: {vault_file.path}
original_type: {vault_file.file_type.value}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
status: pending
requires_action: true
---

# Approval Request

**Original File:** `{vault_file.path}`
**Type:** {vault_file.file_type.value.value if hasattr(vault_file.file_type, 'value') else vault_file.file_type.value}
**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Status:** Pending Review

---

## Action Required

This file requires human approval before processing.

### File Content Preview

```
{vault_file.content[:500]}...
```

---

## Approval Options

- [ ] **Approve** - Move to Approved/ folder for processing
- [ ] **Reject** - Move to Rejected/ folder with reason
- [ ] **Request Changes** - Add comments and return to sender

---

## Instructions

1. Review the file content above
2. Select an approval option
3. Move this file to the appropriate folder:
   - `Approved/` - File is approved for processing
   - `Rejected/` - File is rejected (add reason)
   - Add comments for requested changes

---

*Created by Cloud Orchestrator at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        
        commit_message = f"Approval request: {vault_file.name}"
        
        if self.github.create_file(approval_path, approval_content, commit_message):
            logger.info(f"Created approval request: {approval_filename}")
            self.stats["approvals_created"] += 1
            return True
        else:
            logger.error(f"Failed to create approval request: {approval_filename}")
            return False
    
    def process_email_file(self, vault_file: VaultFile) -> bool:
        """
        Process an email file from Needs_Action
        
        Args:
            vault_file: Email file to process
            
        Returns:
            True if processed successfully
        """
        logger.info(f"Processing email: {vault_file.name}")
        
        # Check if requires approval
        if self.requires_approval(vault_file.content):
            logger.info(f"Email requires approval: {vault_file.name}")
            return self.create_approval_request(vault_file)
        
        # For non-sensitive emails, create a draft response
        return self.create_draft_response(vault_file)
    
    def create_draft_response(self, vault_file: VaultFile) -> bool:
        """
        Create a draft response for an email
        
        Args:
            vault_file: Email file to create draft for
            
        Returns:
            True if successful
        """
        subject = vault_file.frontmatter.get("subject", "No Subject")
        from_email = vault_file.frontmatter.get("from", "Unknown")
        received = vault_file.frontmatter.get("received", "Unknown")
        
        # Create draft response
        draft_content = f"""---
type: draft_response
original_email: {vault_file.path}
to: {from_email}
subject: Re: {subject}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
status: draft
---

# Draft Response

**To:** {from_email}
**Subject:** Re: {subject}
**Created:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Draft Content

Dear Sender,

Thank you for your email regarding "{subject}".

This is an automated draft response generated by the AI Employee system.
Please review and customize before sending.

---

## Original Email

**From:** {from_email}
**Received:** {received}

{vault_file.content}

---

## Action Items

- [ ] Review and customize this draft
- [ ] Send response
- [ ] Mark original email as processed

---

*Draft created by Cloud Orchestrator at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        
        # Save draft to Pending_Approval for review
        draft_filename = f"DRAFT_{vault_file.name}"
        draft_path = f"{self.pending_approval_folder}/{draft_filename}"
        
        commit_message = f"Draft response: {vault_file.name}"
        
        if self.github.create_file(draft_path, draft_content, commit_message):
            logger.info(f"Created draft response: {draft_filename}")
            return True
        else:
            logger.error(f"Failed to create draft response: {draft_filename}")
            return False
    
    def process_file(self, vault_file: VaultFile) -> bool:
        """
        Process a single file based on its type
        
        Args:
            vault_file: File to process
            
        Returns:
            True if processed successfully
        """
        try:
            if vault_file.file_type == FileType.EMAIL:
                return self.process_email_file(vault_file)
            elif vault_file.file_type == FileType.FILE:
                # For generic files, check if approval needed
                if self.requires_approval(vault_file.content):
                    return self.create_approval_request(vault_file)
                else:
                    logger.info(f"File processed (no action needed): {vault_file.name}")
                    return True
            elif vault_file.file_type == FileType.APPROVAL:
                logger.info(f"Approval file already: {vault_file.name}")
                return True
            else:
                logger.warning(f"Unknown file type: {vault_file.name}")
                return True
                
        except Exception as e:
            logger.error(f"Error processing file {vault_file.name}: {e}")
            self.stats["errors"] += 1
            return False
    
    def sync_cycle(self) -> Dict[str, int]:
        """
        Run one sync cycle
        
        Returns:
            Statistics for this cycle
        """
        cycle_stats = {
            "files_scanned": 0,
            "files_processed": 0,
            "approvals_created": 0,
            "errors": 0
        }
        
        # Scan Needs_Action folder
        needs_action_files = self.scan_needs_action()
        cycle_stats["files_scanned"] += len(needs_action_files)
        
        logger.info(f"Found {len(needs_action_files)} files in Needs_Action")
        
        # Process each file
        for vault_file in needs_action_files:
            if self.process_file(vault_file):
                cycle_stats["files_processed"] += 1
            else:
                cycle_stats["errors"] += 1
        
        # Also check pending approvals
        pending_files = self.scan_pending_approvals()
        logger.info(f"Found {len(pending_files)} files in Pending_Approval")
        
        return cycle_stats
    
    def log_action(self, action_type: str, details: str, success: bool = True):
        """Log an action to console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = "✓" if success else "✗"
        log_entry = f"[{timestamp}] {status} {action_type}: {details}"
        
        if success:
            logger.info(log_entry)
        else:
            logger.error(log_entry)
    
    def run(self):
        """Main run loop - continuous syncing"""
        logger.info("=" * 60)
        logger.info("Cloud Orchestrator Started")
        logger.info(f"GitHub Repo: {self.github_repo}")
        logger.info(f"GitHub Branch: {self.github_branch}")
        logger.info(f"Sync Interval: {self.sync_interval} seconds")
        logger.info(f"DRY_RUN: {self.dry_run}")
        logger.info("=" * 60)
        
        # Initialize
        if not self.initialize():
            logger.error("Failed to initialize. Exiting.")
            return
        
        self.running = True
        self.iteration = 0
        
        logger.info("Starting continuous sync...")
        
        try:
            while self.running:
                self.iteration += 1
                self.stats["cycles"] += 1
                
                logger.info(f"\n{'=' * 60}")
                logger.info(f"SYNC CYCLE #{self.iteration}")
                logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("=" * 60)
                
                try:
                    cycle_stats = self.sync_cycle()
                    
                    logger.info(f"\nCycle Statistics:")
                    logger.info(f"  Files Scanned: {cycle_stats['files_scanned']}")
                    logger.info(f"  Files Processed: {cycle_stats['files_processed']}")
                    logger.info(f"  Approvals Created: {cycle_stats['approvals_created']}")
                    logger.info(f"  Errors: {cycle_stats['errors']}")
                    
                    self.stats["files_processed"] += cycle_stats["files_processed"]
                    self.stats["approvals_created"] += cycle_stats["approvals_created"]
                    self.stats["errors"] += cycle_stats["errors"]
                    
                except Exception as e:
                    logger.error(f"Error in sync cycle: {e}")
                    self.stats["errors"] += 1
                
                # Wait for next sync
                logger.info(f"\nNext sync in {self.sync_interval} seconds...")
                time.sleep(self.sync_interval)
                
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.running = False
            
            # Print final statistics
            logger.info("\n" + "=" * 60)
            logger.info("FINAL STATISTICS")
            logger.info("=" * 60)
            logger.info(f"Total Cycles: {self.stats['cycles']}")
            logger.info(f"Files Processed: {self.stats['files_processed']}")
            logger.info(f"Approvals Created: {self.stats['approvals_created']}")
            logger.info(f"Errors: {self.stats['errors']}")
            logger.info("=" * 60)
    
    def stop(self):
        """Stop the orchestrator"""
        self.running = False


def main():
    """Main entry point"""
    print("=" * 60)
    print("Cloud Orchestrator - Platinum Tier")
    print("=" * 60)
    
    # Create and run orchestrator
    orchestrator = CloudOrchestrator(
        github_token=GITHUB_TOKEN,
        github_repo=GITHUB_REPO,
        github_branch=GITHUB_BRANCH,
        sync_interval=SYNC_INTERVAL,
        dry_run=DRY_RUN
    )
    
    try:
        orchestrator.run()
    except KeyboardInterrupt:
        print("\nStopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
