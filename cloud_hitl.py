#!/usr/bin/env python3
"""
Cloud HITL (Human-In-The-Loop) Monitor - Platinum Tier
Monitors GitHub for approved files and creates signal files in local Updates/ folder

Features:
- Monitors GitHub Approved/ folder for newly approved files
- Creates signal files in local Updates/ folder when approvals detected
- Tracks all pending approvals
- Notifies local system of approval status changes
- Runs continuously, checking every 2 minutes (configurable)

Environment Variables:
    GITHUB_TOKEN: GitHub personal access token (required)
    GITHUB_REPO: GitHub repository in format user/repo (required)
    GITHUB_BRANCH: GitHub branch name (default: main)
    HITL_CHECK_INTERVAL: Check interval in seconds (default: 120)
    VAULT_PATH: Local vault path (default: F:\AI_Employee_Vault)
    DRY_RUN: Enable dry run mode (default: true)
"""

import os
import sys
import time
import json
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
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
CHECK_INTERVAL = int(os.getenv("HITL_CHECK_INTERVAL", "120"))
DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))

# GitHub API
GITHUB_API_BASE = "https://api.github.com"

# Setup logging
LOGS_FOLDER = VAULT_PATH / "Logs"
LOGS_FOLDER.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_FOLDER / f"cloud_hitl_{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cloud_hitl")


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
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if "401" in str(e) or "authentication" in str(e).lower():
                        logger.error(f"[{func_name}] Auth error, not retrying: {e}")
                        raise
                    
                    if attempt >= max_attempts:
                        logger.error(f"[{func_name}] All {max_attempts} attempts failed: {e}")
                        raise
                    
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(f"[{func_name}] Attempt {attempt} failed. Retrying in {delay:.1f}s...")
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
    """GitHub API client for HITL operations"""
    
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
        """Get file from GitHub"""
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
    
    @with_retry(max_attempts=3, base_delay=2.0, name="github_list_folder")
    def list_folder(self, path: str) -> List[Dict[str, Any]]:
        """List folder contents in GitHub"""
        try:
            response = self.session.get(self._get_repo_path(path), params={"ref": self.branch})
            
            if response.status_code == 404:
                return []
            elif response.status_code != 200:
                return []
            
            data = response.json()
            return data if isinstance(data, list) else []
            
        except requests.RequestException as e:
            logger.error(f"Failed to list folder {path}: {e}")
            return []


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ApprovalRecord:
    """Represents an approval record"""
    path: str
    name: str
    original_file: str
    status: str
    created_at: str
    content: str


@dataclass
class SignalFile:
    """Represents a signal file to create"""
    path: str
    content: str
    signal_type: str


# =============================================================================
# CLOUD HITL MONITOR
# =============================================================================

class CloudHITLMonitor:
    """
    Cloud HITL Monitor - Human-In-The-Loop for approval tracking
    
    Monitors GitHub Approved/ folder and creates local signal files
    """
    
    def __init__(
        self,
        github_token: str,
        github_repo: str,
        github_branch: str = "main",
        check_interval: int = 120,
        dry_run: bool = True
    ):
        self.github_token = github_token
        self.github_repo = github_repo
        self.github_branch = github_branch
        self.check_interval = check_interval
        self.dry_run = dry_run
        self.vault_path = VAULT_PATH
        
        self.github = None
        self.running = False
        self.iteration = 0
        
        # Tracking
        self.known_approvals: set = set()
        self.processed_approvals: set = set()
        
        # Statistics
        self.stats = {
            "approvals_detected": 0,
            "signals_created": 0,
            "pending_tracked": 0,
            "errors": 0,
            "cycles": 0
        }
        
        # State files
        self.state_file = self.vault_path / ".hitl_state.json"
        self.pending_file = self.vault_path / "pending_approvals.json"
        
        # Folder paths
        self.approved_folder = "Approved"
        self.pending_folder = "Pending_Approval"
        self.rejected_folder = "Rejected"
        self.updates_folder = "Updates"
    
    def initialize(self) -> bool:
        """Initialize GitHub client and load state"""
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
        
        self._load_state()
        self._ensure_local_folders()
        
        return True
    
    def _load_state(self):
        """Load HITL state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.known_approvals = set(state.get("known_approvals", []))
                    self.processed_approvals = set(state.get("processed_approvals", []))
                logger.info(f"Loaded HITL state ({len(self.known_approvals)} known approvals)")
            except Exception as e:
                logger.warning(f"Failed to load HITL state: {e}")
                self.known_approvals = set()
                self.processed_approvals = set()
    
    def _save_state(self):
        """Save HITL state to file"""
        try:
            state = {
                "known_approvals": list(self.known_approvals),
                "processed_approvals": list(self.processed_approvals),
                "last_updated": datetime.now().isoformat()
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save HITL state: {e}")
    
    def _ensure_local_folders(self):
        """Ensure local folders exist"""
        (self.vault_path / self.updates_folder).mkdir(parents=True, exist_ok=True)
        (self.vault_path / "Approved").mkdir(parents=True, exist_ok=True)
        (self.vault_path / "Rejected").mkdir(parents=True, exist_ok=True)
    
    def _scan_approved_folder(self) -> List[ApprovalRecord]:
        """Scan GitHub Approved/ folder for approved files"""
        approvals = []
        
        try:
            items = self.github.list_folder(self.approved_folder)
            
            for item in items:
                if item.get("type") != "file":
                    continue
                if not item.get("name", "").endswith(".md"):
                    continue
                
                path = item.get("path", "")
                name = item.get("name", "")
                
                # Get file content
                file_data = self.github.get_file(path)
                if not file_data or "decoded_content" not in file_data:
                    continue
                
                content = file_data["decoded_content"]
                
                # Parse frontmatter to get original file
                original_file = self._extract_original_file(content)
                status = self._extract_status(content)
                created_at = self._extract_created_at(content)
                
                approvals.append(ApprovalRecord(
                    path=path,
                    name=name,
                    original_file=original_file,
                    status=status,
                    created_at=created_at,
                    content=content
                ))
                
        except Exception as e:
            logger.error(f"Error scanning Approved folder: {e}")
        
        return approvals
    
    def _scan_pending_folder(self) -> List[ApprovalRecord]:
        """Scan GitHub Pending_Approval/ folder for pending approvals"""
        approvals = []
        
        try:
            items = self.github.list_folder(self.pending_folder)
            
            for item in items:
                if item.get("type") != "file":
                    continue
                if not item.get("name", "").endswith(".md"):
                    continue
                
                path = item.get("path", "")
                name = item.get("name", "")
                
                # Get file content
                file_data = self.github.get_file(path)
                if not file_data or "decoded_content" not in file_data:
                    continue
                
                content = file_data["decoded_content"]
                
                # Parse frontmatter
                original_file = self._extract_original_file(content)
                status = self._extract_status(content)
                created_at = self._extract_created_at(content)
                
                approvals.append(ApprovalRecord(
                    path=path,
                    name=name,
                    original_file=original_file,
                    status=status,
                    created_at=created_at,
                    content=content
                ))
                
        except Exception as e:
            logger.error(f"Error scanning Pending_Approval folder: {e}")
        
        return approvals
    
    def _scan_rejected_folder(self) -> List[ApprovalRecord]:
        """Scan GitHub Rejected/ folder for rejected files"""
        approvals = []
        
        try:
            items = self.github.list_folder(self.rejected_folder)
            
            for item in items:
                if item.get("type") != "file":
                    continue
                if not item.get("name", "").endswith(".md"):
                    continue
                
                path = item.get("path", "")
                name = item.get("name", "")
                
                # Get file content
                file_data = self.github.get_file(path)
                if not file_data or "decoded_content" not in file_data:
                    continue
                
                content = file_data["decoded_content"]
                
                # Parse frontmatter
                original_file = self._extract_original_file(content)
                status = self._extract_status(content)
                created_at = self._extract_created_at(content)
                
                approvals.append(ApprovalRecord(
                    path=path,
                    name=name,
                    original_file=original_file,
                    status=status,
                    created_at=created_at,
                    content=content
                ))
                
        except Exception as e:
            logger.error(f"Error scanning Rejected folder: {e}")
        
        return approvals
    
    def _extract_original_file(self, content: str) -> str:
        """Extract original_file from frontmatter"""
        import re
        match = re.search(r"original_file:\s*(.+)", content)
        if match:
            return match.group(1).strip()
        return ""
    
    def _extract_status(self, content: str) -> str:
        """Extract status from frontmatter"""
        import re
        match = re.search(r"status:\s*(.+)", content)
        if match:
            return match.group(1).strip()
        return "unknown"
    
    def _extract_created_at(self, content: str) -> str:
        """Extract created timestamp from frontmatter"""
        import re
        match = re.search(r"created:\s*(.+)", content)
        if match:
            return match.group(1).strip()
        return ""
    
    def _create_signal_file(self, approval: ApprovalRecord, signal_type: str) -> bool:
        """
        Create a signal file in local Updates/ folder
        
        Args:
            approval: Approval record
            signal_type: Type of signal (approved, rejected, pending)
            
        Returns:
            True if successful
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        signal_filename = f"SIGNAL_{signal_type}_{approval.name}_{timestamp}.md"
        signal_path = self.vault_path / self.updates_folder / signal_filename
        
        signal_content = f"""---
type: signal
signal_type: {signal_type}
original_approval: {approval.path}
original_file: {approval.original_file}
detected_at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
status: {approval.status}
---

# Signal: {signal_type.upper()}

**Original Approval:** `{approval.path}`
**Original File:** `{approval.original_file}`
**Detected At:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Status:** {approval.status}

---

## Signal Details

This signal file was created by the Cloud HITL Monitor to notify
the local system of an approval status change in the GitHub repository.

### Action Required

- For **approved** signals: Process the approved file
- For **rejected** signals: Review rejection reason
- For **pending** signals: Track and monitor

---

## Original Content

{approval.content[:1000]}...

---

*Signal created by Cloud HITL Monitor at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
        
        try:
            if not DRY_RUN:
                with open(signal_path, "w", encoding="utf-8") as f:
                    f.write(signal_content)
            
            logger.info(f"Created signal file: {signal_filename}")
            self.stats["signals_created"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to create signal file: {e}")
            self.stats["errors"] += 1
            return False
    
    def _update_pending_tracker(self, pending: List[ApprovalRecord]):
        """Update the pending approvals tracker file"""
        tracker_path = self.vault_path / self.pending_file
        
        tracker_data = {
            "last_updated": datetime.now().isoformat(),
            "total_pending": len(pending),
            "approvals": [
                {
                    "path": p.path,
                    "name": p.name,
                    "original_file": p.original_file,
                    "created_at": p.created_at,
                    "status": p.status
                }
                for p in pending
            ]
        }
        
        try:
            if not DRY_RUN:
                with open(tracker_path, "w", encoding="utf-8") as f:
                    json.dump(tracker_data, f, indent=2)
            
            logger.info(f"Updated pending tracker ({len(pending)} pending)")
            self.stats["pending_tracked"] = len(pending)
            
        except Exception as e:
            logger.error(f"Failed to update pending tracker: {e}")
    
    def _check_cycle(self):
        """Run one check cycle"""
        logger.info("Starting HITL check cycle...")
        
        # Scan all folders
        approved = self._scan_approved_folder()
        pending = self._scan_pending_folder()
        rejected = self._scan_rejected_folder()
        
        logger.info(f"Found {len(approved)} approved, {len(pending)} pending, {len(rejected)} rejected")
        
        # Update pending tracker
        self._update_pending_tracker(pending)
        
        # Check for new approvals
        for approval in approved:
            if approval.path not in self.known_approvals:
                # New approval detected!
                logger.info(f"New approval detected: {approval.name}")
                self.known_approvals.add(approval.path)
                self.stats["approvals_detected"] += 1
                
                # Create signal file
                self._create_signal_file(approval, "approved")
                
                # Mark as processed
                self.processed_approvals.add(approval.path)
        
        # Check for new rejections
        for approval in rejected:
            if approval.path not in self.processed_approvals:
                # New rejection detected!
                logger.info(f"New rejection detected: {approval.name}")
                
                # Create signal file
                self._create_signal_file(approval, "rejected")
                
                # Mark as processed
                self.processed_approvals.add(approval.path)
        
        # Save state
        self._save_state()
        
        logger.info(f"Cycle complete: {len(approved)} approved tracked, {len(pending)} pending")
    
    def run(self):
        """Main run loop"""
        logger.info("=" * 60)
        logger.info("Cloud HITL Monitor Started")
        logger.info(f"GitHub Repo: {self.github_repo}")
        logger.info(f"GitHub Branch: {self.github_branch}")
        logger.info(f"Check Interval: {self.check_interval} seconds")
        logger.info(f"DRY_RUN: {self.dry_run}")
        logger.info(f"Vault Path: {self.vault_path}")
        logger.info("=" * 60)
        
        if not self.initialize():
            logger.error("Failed to initialize. Exiting.")
            return
        
        self.running = True
        self.iteration = 0
        
        logger.info("Starting continuous monitoring...")
        
        try:
            while self.running:
                self.iteration += 1
                self.stats["cycles"] += 1
                
                logger.info(f"\n{'=' * 60}")
                logger.info(f"HITL CHECK #{self.iteration}")
                logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("=" * 60)
                
                try:
                    self._check_cycle()
                except Exception as e:
                    logger.error(f"Error in check cycle: {e}")
                    self.stats["errors"] += 1
                
                logger.info(f"\nNext check in {self.check_interval} seconds...")
                time.sleep(self.check_interval)
                
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.running = False
            
            logger.info("\n" + "=" * 60)
            logger.info("FINAL STATISTICS")
            logger.info("=" * 60)
            logger.info(f"Total Cycles: {self.stats['cycles']}")
            logger.info(f"Approvals Detected: {self.stats['approvals_detected']}")
            logger.info(f"Signals Created: {self.stats['signals_created']}")
            logger.info(f"Pending Tracked: {self.stats['pending_tracked']}")
            logger.info(f"Errors: {self.stats['errors']}")
            logger.info("=" * 60)
    
    def stop(self):
        """Stop the monitor"""
        self.running = False
    
    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """Get list of pending approvals"""
        pending = self._scan_pending_folder()
        return [
            {
                "path": p.path,
                "name": p.name,
                "original_file": p.original_file,
                "created_at": p.created_at,
                "status": p.status
            }
            for p in pending
        ]


def main():
    """Main entry point"""
    print("=" * 60)
    print("Cloud HITL Monitor - Platinum Tier")
    print("=" * 60)
    
    monitor = CloudHITLMonitor(
        github_token=GITHUB_TOKEN,
        github_repo=GITHUB_REPO,
        github_branch=GITHUB_BRANCH,
        check_interval=CHECK_INTERVAL,
        dry_run=DRY_RUN
    )
    
    try:
        monitor.run()
    except KeyboardInterrupt:
        print("\nStopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
