#!/usr/bin/env python3
"""
GitHub Sync - Platinum Tier
Bidirectional sync between local vault and GitHub repository

Features:
- Pull: Download new files from GitHub to local vault
- Push: Upload local changes to GitHub
- Conflict resolution:
  - Cloud wins for Needs_Action/ folder
  - Local wins for Approved/ and Rejected/ folders
- Runs every 5 minutes (configurable)
- Skips: .env, credentials.json, sessions/ folder

Environment Variables:
    GITHUB_TOKEN: GitHub personal access token (required)
    GITHUB_REPO: GitHub repository in format user/repo (required)
    GITHUB_BRANCH: GitHub branch name (default: main)
    SYNC_INTERVAL: Sync interval in seconds (default: 300)
    VAULT_PATH: Local vault path (default: F:\AI_Employee_Vault)
    DRY_RUN: Enable dry run mode (default: true)
"""

import os
import sys
import time
import json
import base64
import hashlib
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any, Set, Tuple
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
SYNC_INTERVAL = int(os.getenv("SYNC_INTERVAL", "300"))
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
        logging.FileHandler(LOGS_FOLDER / f"github_sync_{datetime.now().strftime('%Y-%m-%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("github_sync")


# =============================================================================
# FILES/FOLDERS TO SKIP
# =============================================================================

SKIP_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    "credentials.json",
    "token.json",
    "github_token.txt",
    ".gitignore",
    ".git"
}

SKIP_FOLDERS = {
    "sessions",
    "whatsapp_session",
    "__pycache__",
    ".git",
    ".qwen",
    "node_modules",
    "venv",
    ".venv",
    "env"
}

SKIP_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".exe"
}


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
    """GitHub API client for sync operations"""
    
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
    
    @with_retry(max_attempts=3, base_delay=2.0, name="github_create_file")
    def create_file(self, path: str, content: str, message: str) -> bool:
        """Create file in GitHub"""
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Would create: {path}")
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
                logger.info(f"Created: {path}")
                return True
            else:
                logger.error(f"Failed to create {path}: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to create {path}: {e}")
            return False
    
    @with_retry(max_attempts=3, base_delay=2.0, name="github_update_file")
    def update_file(self, path: str, content: str, message: str, sha: Optional[str] = None) -> bool:
        """Update file in GitHub"""
        if DRY_RUN:
            logger.info(f"[DRY_RUN] Would update: {path}")
            return True
        
        if not sha:
            file_data = self.get_file(path)
            if not file_data:
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
                logger.info(f"Updated: {path}")
                return True
            else:
                logger.error(f"Failed to update {path}: {response.status_code}")
                return False
                
        except requests.RequestException as e:
            logger.error(f"Failed to update {path}: {e}")
            return False
    
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
    
    @with_retry(max_attempts=3, base_delay=2.0, name="github_list_tree")
    def list_tree(self, path: str = "") -> List[str]:
        """Recursively list all files in a GitHub folder"""
        files = []
        items = self.list_folder(path)
        
        for item in items:
            item_path = item.get("path", "")
            item_type = item.get("type", "")
            
            # Skip folders to skip
            folder_name = item_path.split("/")[-1]
            if item_type == "dir" and folder_name in SKIP_FOLDERS:
                continue
            
            if item_type == "file":
                # Skip files to skip
                file_name = item_path.split("/")[-1]
                ext = os.path.splitext(file_name)[1].lower()
                
                if file_name in SKIP_FILES or ext in SKIP_EXTENSIONS:
                    continue
                
                files.append(item_path)
            elif item_type == "dir":
                # Recurse into subfolder
                files.extend(self.list_tree(item_path))
        
        return files


# =============================================================================
# SYNC ITEM
# =============================================================================

@dataclass
class SyncItem:
    """Represents a file to sync"""
    path: str
    local_path: Optional[Path]
    remote_sha: Optional[str]
    local_hash: Optional[str]
    exists_local: bool
    exists_remote: bool
    conflict: bool
    resolution: str  # "cloud", "local", "skip"


# =============================================================================
# GITHUB SYNC MANAGER
# =============================================================================

class GitHubSyncManager:
    """
    Bidirectional sync between local vault and GitHub
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
        self.vault_path = VAULT_PATH
        
        self.github = None
        self.running = False
        self.iteration = 0
        
        # Statistics
        self.stats = {
            "files_pulled": 0,
            "files_pushed": 0,
            "conflicts_resolved": 0,
            "files_skipped": 0,
            "errors": 0,
            "cycles": 0
        }
        
        # Sync state file
        self.sync_state_file = self.vault_path / ".sync_state.json"
        self.sync_state: Dict[str, Dict[str, Any]] = {}
    
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
        
        self._load_sync_state()
        return True
    
    def _load_sync_state(self):
        """Load sync state from file"""
        if self.sync_state_file.exists():
            try:
                with open(self.sync_state_file, "r", encoding="utf-8") as f:
                    self.sync_state = json.load(f)
                logger.info(f"Loaded sync state ({len(self.sync_state)} entries)")
            except Exception as e:
                logger.warning(f"Failed to load sync state: {e}")
                self.sync_state = {}
    
    def _save_sync_state(self):
        """Save sync state to file"""
        try:
            with open(self.sync_state_file, "w", encoding="utf-8") as f:
                json.dump(self.sync_state, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save sync state: {e}")
    
    def _should_skip(self, path: str) -> bool:
        """Check if a path should be skipped"""
        # Check file name
        file_name = os.path.basename(path)
        if file_name in SKIP_FILES:
            return True
        
        # Check extension
        ext = os.path.splitext(file_name)[1].lower()
        if ext in SKIP_EXTENSIONS:
            return True
        
        # Check folder names
        path_parts = path.split("/")
        for part in path_parts:
            if part in SKIP_FOLDERS:
                return True
        
        return False
    
    def _get_local_hash(self, local_path: Path) -> Optional[str]:
        """Get MD5 hash of local file"""
        if not local_path.exists():
            return None
        
        try:
            with open(local_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to hash {local_path}: {e}")
            return None
    
    def _get_local_path(self, remote_path: str) -> Path:
        """Convert remote path to local path"""
        return self.vault_path / remote_path.replace("/", os.sep)
    
    def _get_remote_path(self, local_path: Path) -> str:
        """Convert local path to remote path"""
        rel_path = local_path.relative_to(self.vault_path)
        return str(rel_path).replace(os.sep, "/")
    
    def _determine_resolution(self, path: str) -> str:
        """
        Determine conflict resolution strategy based on path
        
        Rules:
        - Needs_Action/ → Cloud wins
        - Approved/ → Local wins
        - Rejected/ → Local wins
        - Done/ → Local wins
        - Pending_Approval/ → Cloud wins
        - Others → Skip (manual resolution)
        """
        if path.startswith("Needs_Action/"):
            return "cloud"
        elif path.startswith("Pending_Approval/"):
            return "cloud"
        elif path.startswith("Updates/"):
            return "cloud"
        elif path.startswith("Approved/"):
            return "local"
        elif path.startswith("Rejected/"):
            return "local"
        elif path.startswith("Done/"):
            return "local"
        elif path.startswith("Logs/"):
            return "skip"  # Don't sync logs
        elif path.startswith("sessions/"):
            return "skip"  # Don't sync sessions
        else:
            # Default: cloud wins for new files, skip for conflicts
            return "cloud"
    
    def _list_local_files(self) -> Set[str]:
        """List all syncable files in local vault"""
        local_files = set()
        
        for root, dirs, files in os.walk(self.vault_path):
            # Skip hidden directories and skip folders
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_FOLDERS]
            
            for file in files:
                file_path = Path(root) / file
                
                # Skip hidden files
                if file.startswith("."):
                    continue
                
                # Check skip list
                rel_path = self._get_remote_path(file_path)
                if self._should_skip(rel_path):
                    continue
                
                local_files.add(rel_path)
        
        return local_files
    
    def _scan_remote(self) -> Dict[str, Dict[str, Any]]:
        """Scan GitHub for all files"""
        remote_files = {}
        
        try:
            file_paths = self.github.list_tree("")
            
            for path in file_paths:
                if self._should_skip(path):
                    continue
                
                file_info = self.github.get_file(path)
                if file_info:
                    remote_files[path] = {
                        "sha": file_info.get("sha", ""),
                        "size": file_info.get("size", 0),
                        "path": path
                    }
        except Exception as e:
            logger.error(f"Failed to scan remote: {e}")
        
        return remote_files
    
    def _pull_file(self, path: str, remote_info: Dict[str, Any]) -> bool:
        """Pull a file from GitHub to local"""
        try:
            local_path = self._get_local_path(path)
            
            # Get file content
            file_data = self.github.get_file(path)
            if not file_data or "decoded_content" not in file_data:
                logger.error(f"Failed to get content for {path}")
                return False
            
            content = file_data["decoded_content"]
            
            # Create directory if needed
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            if not DRY_RUN:
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(content)
            
            # Update sync state
            self.sync_state[path] = {
                "remote_sha": remote_info.get("sha", ""),
                "local_hash": self._get_local_hash(local_path),
                "last_sync": datetime.now().isoformat(),
                "last_action": "pull"
            }
            
            logger.info(f"Pulled: {path}")
            self.stats["files_pulled"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to pull {path}: {e}")
            self.stats["errors"] += 1
            return False
    
    def _push_file(self, path: str, local_path: Path) -> bool:
        """Push a file from local to GitHub"""
        try:
            # Read local content
            with open(local_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check if file exists remotely
            remote_file = self.github.get_file(path)
            
            if remote_file:
                # Update existing file
                message = f"Sync: Update {path}"
                success = self.github.update_file(path, content, message)
            else:
                # Create new file
                message = f"Sync: Add {path}"
                success = self.github.create_file(path, content, message)
            
            if success:
                # Update sync state
                self.sync_state[path] = {
                    "remote_sha": self.github._sha_cache.get(path, ""),
                    "local_hash": self._get_local_hash(local_path),
                    "last_sync": datetime.now().isoformat(),
                    "last_action": "push"
                }
                
                logger.info(f"Pushed: {path}")
                self.stats["files_pushed"] += 1
                return True
            else:
                logger.error(f"Failed to push {path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to push {path}: {e}")
            self.stats["errors"] += 1
            return False
    
    def sync_cycle(self) -> Dict[str, int]:
        """
        Run one sync cycle
        
        Returns:
            Statistics for this cycle
        """
        cycle_stats = {
            "pulled": 0,
            "pushed": 0,
            "conflicts": 0,
            "skipped": 0,
            "errors": 0
        }
        
        logger.info("Starting sync cycle...")
        
        # Scan remote
        logger.info("Scanning GitHub repository...")
        remote_files = self._scan_remote()
        logger.info(f"Found {len(remote_files)} files in GitHub")
        
        # Scan local
        logger.info("Scanning local vault...")
        local_files = self._list_local_files()
        logger.info(f"Found {len(local_files)} files locally")
        
        # All known paths
        all_paths = set(remote_files.keys()) | local_files
        
        logger.info(f"Total unique paths: {len(all_paths)}")
        
        # Process each path
        for path in all_paths:
            exists_remote = path in remote_files
            exists_local = path in local_files
            
            local_path = self._get_local_path(path) if exists_local else None
            remote_sha = remote_files.get(path, {}).get("sha") if exists_remote else None
            local_hash = self._get_local_hash(local_path) if exists_local else None
            
            # Get previous state
            prev_state = self.sync_state.get(path, {})
            prev_remote_sha = prev_state.get("remote_sha", "")
            prev_local_hash = prev_state.get("local_hash", "")
            
            # Determine if changed
            remote_changed = exists_remote and remote_sha != prev_remote_sha
            local_changed = exists_local and local_hash != prev_local_hash
            
            # Determine action
            if exists_remote and not exists_local:
                # New remote file - pull
                logger.info(f"New remote file: {path}")
                if self._pull_file(path, remote_files[path]):
                    cycle_stats["pulled"] += 1
                    
            elif exists_local and not exists_remote:
                # New local file - push
                logger.info(f"New local file: {path}")
                if self._push_file(path, local_path):
                    cycle_stats["pushed"] += 1
                    
            elif exists_remote and exists_local:
                # Both exist - check for changes
                if remote_changed and local_changed:
                    # Conflict!
                    logger.warning(f"Conflict detected: {path}")
                    resolution = self._determine_resolution(path)
                    
                    if resolution == "cloud":
                        logger.info(f"Resolving conflict (cloud wins): {path}")
                        if self._pull_file(path, remote_files[path]):
                            cycle_stats["conflicts"] += 1
                    elif resolution == "local":
                        logger.info(f"Resolving conflict (local wins): {path}")
                        if self._push_file(path, local_path):
                            cycle_stats["conflicts"] += 1
                    else:
                        logger.info(f"Skipping conflict (manual resolution needed): {path}")
                        cycle_stats["skipped"] += 1
                        
                elif remote_changed:
                    # Only remote changed - pull
                    logger.info(f"Remote changed: {path}")
                    if self._pull_file(path, remote_files[path]):
                        cycle_stats["pulled"] += 1
                        
                elif local_changed:
                    # Only local changed - push
                    logger.info(f"Local changed: {path}")
                    if self._push_file(path, local_path):
                        cycle_stats["pushed"] += 1
                        
                else:
                    # No changes
                    pass
        
        # Save sync state
        self._save_sync_state()
        
        return cycle_stats
    
    def run(self):
        """Main run loop"""
        logger.info("=" * 60)
        logger.info("GitHub Sync Started")
        logger.info(f"GitHub Repo: {self.github_repo}")
        logger.info(f"GitHub Branch: {self.github_branch}")
        logger.info(f"Sync Interval: {self.sync_interval} seconds")
        logger.info(f"DRY_RUN: {self.dry_run}")
        logger.info(f"Vault Path: {self.vault_path}")
        logger.info("=" * 60)
        
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
                    logger.info(f"  Files Pulled: {cycle_stats['pulled']}")
                    logger.info(f"  Files Pushed: {cycle_stats['pushed']}")
                    logger.info(f"  Conflicts Resolved: {cycle_stats['conflicts']}")
                    logger.info(f"  Files Skipped: {cycle_stats['skipped']}")
                    logger.info(f"  Errors: {cycle_stats['errors']}")
                    
                    self.stats["files_pulled"] += cycle_stats["pulled"]
                    self.stats["files_pushed"] += cycle_stats["pushed"]
                    self.stats["conflicts_resolved"] += cycle_stats["conflicts"]
                    self.stats["files_skipped"] += cycle_stats["skipped"]
                    self.stats["errors"] += cycle_stats["errors"]
                    
                except Exception as e:
                    logger.error(f"Error in sync cycle: {e}")
                    self.stats["errors"] += 1
                
                logger.info(f"\nNext sync in {self.sync_interval} seconds...")
                time.sleep(self.sync_interval)
                
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
            logger.info(f"Files Pulled: {self.stats['files_pulled']}")
            logger.info(f"Files Pushed: {self.stats['files_pushed']}")
            logger.info(f"Conflicts Resolved: {self.stats['conflicts_resolved']}")
            logger.info(f"Files Skipped: {self.stats['files_skipped']}")
            logger.info(f"Errors: {self.stats['errors']}")
            logger.info("=" * 60)
    
    def stop(self):
        """Stop the sync"""
        self.running = False


def main():
    """Main entry point"""
    print("=" * 60)
    print("GitHub Sync - Platinum Tier")
    print("=" * 60)
    
    sync_manager = GitHubSyncManager(
        github_token=GITHUB_TOKEN,
        github_repo=GITHUB_REPO,
        github_branch=GITHUB_BRANCH,
        sync_interval=SYNC_INTERVAL,
        dry_run=DRY_RUN
    )
    
    try:
        sync_manager.run()
    except KeyboardInterrupt:
        print("\nStopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
