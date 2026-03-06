#!/usr/bin/env python3
"""
File Watcher - Monitors Inbox folder for new files
Copies new files to Needs_Action and creates metadata files
"""

import os
import sys
import time
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
INBOX_FOLDER = VAULT_PATH / "Inbox"
NEEDS_ACTION_FOLDER = VAULT_PATH / "Needs_Action"
LOGS_FOLDER = VAULT_PATH / "Logs"

# Track processed files to avoid duplicates
processed_files = set()


def get_log_file_path():
    """Get log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"file_watcher_{date_str}.log"


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


def get_file_hash(filepath):
    """Calculate MD5 hash of file for tracking"""
    try:
        with open(filepath, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception:
        return None


def create_metadata_file(original_filename, source_path, dest_path):
    """Create metadata markdown file for the copied file"""
    try:
        file_size = os.path.getsize(dest_path)
    except Exception:
        file_size = 0
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    safe_name = Path(original_filename).stem.replace(" ", "_").replace(".", "_")
    metadata_filename = f"FILE_{safe_name}_metadata.md"
    metadata_path = NEEDS_ACTION_FOLDER / metadata_filename
    
    metadata_content = f"""---
type: file
original_filename: {original_filename}
source_path: {source_path}
dest_path: {dest_path}
file_size: {file_size} bytes
received: {timestamp}
status: pending
---

# File Processing: {original_filename}

**Original File:** {original_filename}  
**File Size:** {file_size} bytes  
**Received:** {timestamp}  
**Status:** Pending

---

## File Location

- **Source:** `{source_path}`
- **Copied to:** `{dest_path}`

---

## Suggested Actions

- [ ] Review file content
- [ ] Process file data
- [ ] Extract relevant information
- [ ] Mark as processed

---

## Notes

*Add any notes about this file here*

---

*Created by File Watcher at {timestamp}*
"""
    
    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            f.write(metadata_content)
        log_message(f"Created metadata file: {metadata_filename}")
        return True
    except Exception as e:
        log_message(f"ERROR creating metadata file: {e}")
        return False


def process_new_file(source_path):
    """Process a new file detected in Inbox"""
    try:
        filename = os.path.basename(source_path)
        
        # Skip hidden files and metadata files
        if filename.startswith(".") or filename.endswith("_metadata.md"):
            log_message(f"Skipping system/metadata file: {filename}")
            return False
        
        # Generate unique identifier for tracking
        file_hash = get_file_hash(source_path)
        file_id = f"{filename}_{file_hash}" if file_hash else filename
        
        # Skip if already processed
        if file_id in processed_files:
            log_message(f"File already processed: {filename}")
            return False
        
        # Create destination path
        dest_path = NEEDS_ACTION_FOLDER / filename
        
        # Handle duplicate filenames
        counter = 1
        while dest_path.exists():
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            dest_path = NEEDS_ACTION_FOLDER / f"{stem}_{counter}{suffix}"
            counter += 1
        
        # Copy file to Needs_Action
        log_message(f"Copying {filename} to Needs_Action...")
        shutil.copy2(source_path, dest_path)
        log_message(f"Copied to: {dest_path}")
        
        # Create metadata file
        create_metadata_file(filename, source_path, dest_path)
        
        # Mark as processed
        processed_files.add(file_id)
        
        return True
        
    except Exception as e:
        log_message(f"ERROR processing file {source_path}: {e}")
        return False


class InboxEventHandler(FileSystemEventHandler):
    """Handle file system events in Inbox folder"""
    
    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory:
            return
        
        source_path = event.src_path
        log_message(f"New file detected: {os.path.basename(source_path)}")
        
        # Small delay to ensure file is fully written
        time.sleep(0.5)
        
        try:
            process_new_file(source_path)
        except Exception as e:
            log_message(f"ERROR handling file event: {e}")
    
    def on_modified(self, event):
        """Handle file modification events (treat as new if not processed)"""
        if event.is_directory:
            return
        
        source_path = event.src_path
        filename = os.path.basename(source_path)
        
        # Skip hidden files
        if filename.startswith("."):
            return
        
        file_hash = get_file_hash(source_path)
        file_id = f"{filename}_{file_hash}" if file_hash else filename
        
        # Only process if not already tracked
        if file_id not in processed_files:
            log_message(f"Modified file detected: {filename}")
            time.sleep(0.5)
            try:
                process_new_file(source_path)
            except Exception as e:
                log_message(f"ERROR handling modified file: {e}")


def main():
    """Main function - runs file watcher continuously"""
    log_message("=" * 50)
    log_message("File Watcher Started")
    log_message(f"Monitoring: {INBOX_FOLDER}")
    log_message(f"Target: {NEEDS_ACTION_FOLDER}")
    log_message("=" * 50)
    
    # Ensure folders exist
    INBOX_FOLDER.mkdir(parents=True, exist_ok=True)
    NEEDS_ACTION_FOLDER.mkdir(parents=True, exist_ok=True)
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Load previously processed files if available
    processed_file = VAULT_PATH / ".processed_files.json"
    if processed_file.exists():
        try:
            import json
            with open(processed_file, "r", encoding="utf-8") as f:
                processed_files.update(json.load(f))
            log_message(f"Loaded {len(processed_files)} previously processed file IDs")
        except Exception as e:
            log_message(f"Warning: Could not load processed files: {e}")
    
    # Set up the observer
    event_handler = InboxEventHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INBOX_FOLDER), recursive=False)
    
    try:
        observer.start()
        log_message("File watcher is now running...")
        log_message(f"Watching folder: {INBOX_FOLDER}")
        log_message("Press Ctrl+C to stop")
        
        while True:
            time.sleep(1)
            
            # Periodically save processed files list
            if int(time.time()) % 300 == 0:  # Every 5 minutes
                try:
                    import json
                    with open(processed_file, "w", encoding="utf-8") as f:
                        json.dump(list(processed_files), f)
                except Exception as e:
                    log_message(f"Warning: Could not save processed files: {e}")
                    
    except KeyboardInterrupt:
        log_message("\nFile Watcher stopped by user")
        observer.stop()
    except Exception as e:
        log_message(f"ERROR in file watcher: {e}")
        observer.stop()
    
    observer.join()
    
    # Save processed files on exit
    try:
        import json
        with open(processed_file, "w", encoding="utf-8") as f:
            json.dump(list(processed_files), f)
        log_message("Saved processed files list")
    except Exception as e:
        log_message(f"Warning: Could not save processed files on exit: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("\nFile Watcher terminated")
        sys.exit(0)
    except Exception as e:
        log_message(f"Fatal error: {e}")
        sys.exit(1)
