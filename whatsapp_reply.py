#!/usr/bin/env python3
"""
WhatsApp Reply - Send approved WhatsApp replies
Monitors Approved folder for WhatsApp reply approvals
"""

import os
import sys
import time
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
APPROVED_FOLDER = VAULT_PATH / "Approved"
DONE_FOLDER = VAULT_PATH / "Done"
LOGS_FOLDER = VAULT_PATH / "Logs"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
SESSION_PATH = Path(os.getenv("WHATSAPP_SESSION_PATH", VAULT_PATH / "whatsapp_session"))

CHECK_INTERVAL = 30  # Check every 30 seconds

# Reply statistics
reply_stats = {
    "replies_sent_today": 0,
    "last_reply": None,
    "status": "Active"
}


def get_log_file_path():
    """Get JSON log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"whatsapp_reply_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"whatsapp_reply_activity_{date_str}.txt"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, DONE_FOLDER, SESSION_PATH]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True):
    """Log a WhatsApp reply action to log files"""
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
        log_data = load_json_log()
        log_data["actions"].append(json_entry)
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
            "total_replies": 0,
            "total_errors": 0
        }
    }


def save_json_log(log_data):
    """Save log data to JSON file"""
    try:
        log_data["summary"]["total_replies"] = reply_stats["replies_sent_today"]
        log_data["summary"]["total_errors"] = reply_stats.get("errors", 0)
        
        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR saving JSON log: {e}")
        return False


def parse_yaml_frontmatter(content):
    """Extract YAML frontmatter from markdown content"""
    frontmatter = {}
    
    match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if match:
        yaml_content = match.group(1)
        for line in yaml_content.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                value = value.strip().strip('"').strip("'")
                frontmatter[key.strip()] = value
    
    return frontmatter


def extract_reply_content(content):
    """Extract the reply message from approval file"""
    # Remove frontmatter
    content_no_fm = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL)
    
    # Look for reply section
    reply_match = re.search(r"## Reply\s*\n(.*?)(?=## |$)", content_no_fm, re.DOTALL | re.IGNORECASE)
    if reply_match:
        return reply_match.group(1).strip()
    
    # Look for message section
    message_match = re.search(r"## Message\s*\n(.*?)(?=## |$)", content_no_fm, re.DOTALL | re.IGNORECASE)
    if message_match:
        return message_match.group(1).strip()
    
    # Fallback: return first paragraph after frontmatter
    lines = content_no_fm.strip().split("\n")
    reply_lines = []
    for line in lines:
        if line.strip() and not line.startswith("#"):
            reply_lines.append(line)
        elif reply_lines:
            break
    
    return "\n".join(reply_lines).strip()


def initialize_whatsapp_session():
    """Initialize WhatsApp Web session and return context"""
    playwright = sync_playwright().start()
    
    # Launch browser with stealth settings
    browser = playwright.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage"
        ]
    )
    
    # Create context with anti-detection
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        locale="en-US",
        timezone_id="America/New_York"
    )
    
    # Add stealth script
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    # Load saved session cookies if available
    session_file = SESSION_PATH / "whatsapp_session.json"
    if session_file.exists():
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            context.add_cookies(cookies)
            log_action("session_loaded", "Loaded saved session cookies")
        except Exception as e:
            log_action("session_load_error", f"Failed to load session: {e}", success=False)
    
    return playwright, browser, context


def send_whatsapp_message(context, contact_name, message_text):
    """Send a WhatsApp message to a contact"""
    try:
        page = context.pages[0] if context.pages else context.new_page()
        
        # Navigate to WhatsApp Web
        if "web.whatsapp.com" not in page.url:
            page.goto("https://web.whatsapp.com", wait_until="networkidle")
            time.sleep(3)
        
        # Wait for chat list
        try:
            page.wait_for_selector('div[role="grid"]', timeout=10000)
        except PlaywrightTimeout:
            log_action("navigation_error", "Could not find chat list", success=False)
            return False
        
        # Search for contact
        search_box = page.query_selector('div[contenteditable="true"][data-tab="3"]')
        if not search_box:
            log_action("search_error", "Could not find search box", success=False)
            return False
        
        # Clear search and type contact name
        search_box.click()
        search_box.fill("")
        time.sleep(1)
        
        # Type contact name character by character (human-like)
        for char in contact_name:
            search_box.type(char)
            time.sleep(0.1)
        
        time.sleep(2)
        
        # Click on the contact
        contact_selector = f'span[title="{contact_name}"]'
        contact_elem = page.query_selector(contact_selector)
        
        if not contact_elem:
            # Try alternative selector
            contact_elem = page.query_selector(f'div[title*="{contact_name}"]')
        
        if contact_elem:
            contact_elem.click()
            time.sleep(2)
        else:
            log_action("contact_not_found", f"Could not find contact: {contact_name}", success=False)
            return False
        
        # Find message input box
        message_box = page.query_selector('div[contenteditable="true"][data-tab="10"]')
        if not message_box:
            log_action("message_box_error", "Could not find message input", success=False)
            return False
        
        # Type message
        message_box.click()
        time.sleep(1)
        
        # Type message character by character
        for char in message_text[:500]:  # Limit message length
            message_box.type(char)
            time.sleep(0.05)
        
        time.sleep(1)
        
        # Click send button
        send_button = page.query_selector('button[data-testid="compose-btn-send"]')
        if send_button:
            send_button.click()
            time.sleep(2)
            log_action("message_sent", f"Sent to {contact_name}: {message_text[:50]}...")
            return True
        else:
            # Try pressing Enter
            message_box.press("Enter")
            time.sleep(2)
            log_action("message_sent", f"Sent to {contact_name} (via Enter): {message_text[:50]}...")
            return True
        
    except Exception as e:
        log_action("send_error", f"Failed to send message: {e}", success=False)
        return False


def check_approved_folder():
    """Check Approved folder for WhatsApp reply approvals"""
    if not APPROVED_FOLDER.exists():
        return None
    
    # Find WhatsApp reply approval files
    for approval_file in APPROVED_FOLDER.glob("*.md"):
        try:
            with open(approval_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            frontmatter = parse_yaml_frontmatter(content)
            file_type = frontmatter.get("type", "").lower()
            
            # Check if this is a WhatsApp reply approval
            if file_type == "whatsapp_reply" or "whatsapp" in file_type:
                contact_name = frontmatter.get("to", frontmatter.get("contact", ""))
                reply_content = extract_reply_content(content)
                
                if contact_name and reply_content:
                    return {
                        "filepath": approval_file,
                        "contact": contact_name,
                        "message": reply_content,
                        "content": content
                    }
        except Exception as e:
            log_action("read_approval_error", f"Error reading {approval_file.name}: {e}", success=False)
            continue
    
    return None


def move_to_done(filepath):
    """Move processed approval file to Done folder"""
    try:
        dest_path = DONE_FOLDER / filepath.name
        
        # Handle duplicate filenames
        counter = 1
        while dest_path.exists():
            stem = filepath.stem
            suffix = filepath.suffix
            dest_path = DONE_FOLDER / f"{stem}_{counter}{suffix}"
            counter += 1
        
        shutil.move(str(filepath), str(dest_path))
        log_action("file_moved", f"Moved {filepath.name} to Done")
        return True
    except Exception as e:
        log_action("move_error", f"Failed to move file: {e}", success=False)
        return False


def update_dashboard():
    """Update Dashboard.md with WhatsApp reply status"""
    try:
        if not DASHBOARD_FILE.exists():
            return False
        
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Count pending WhatsApp approvals
        pending_count = 0
        if APPROVED_FOLDER.exists():
            for f in APPROVED_FOLDER.glob("*.md"):
                try:
                    with open(f, "r", encoding="utf-8") as file:
                        if "whatsapp" in file.read().lower():
                            pending_count += 1
                except Exception:
                    continue
        
        whatsapp_section = f"""## WhatsApp Status
- Watcher: {reply_stats['status']}
- Messages Detected Today: 0
- High Priority Messages: 0
- Pending Replies: {pending_count}
- Last Check: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        if "## WhatsApp Status" in content:
            pattern = r"## WhatsApp Status.*?(?=## |\Z)"
            content = re.sub(pattern, whatsapp_section, content, flags=re.DOTALL)
        else:
            if "---" in content:
                parts = content.rsplit("---", 1)
                content = parts[0] + whatsapp_section + "\n---" + parts[1] if len(parts) > 1 else content + "\n" + whatsapp_section
            else:
                content = content + "\n" + whatsapp_section
        
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
    except Exception as e:
        log_action("dashboard_error", f"Failed to update dashboard: {e}", success=False)
        return False


def main():
    """Main function - runs WhatsApp reply monitor"""
    print("=" * 60)
    print("WhatsApp Reply - AI Employee System")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Approved Folder: {APPROVED_FOLDER}")
    print(f"Check Interval: {CHECK_INTERVAL} seconds")
    print("=" * 60)
    print("\nNOTE: This script will only send messages with approved files.")
    print("      Place WhatsApp reply approvals in the Approved folder.\n")
    
    # Ensure folders exist
    ensure_folders_exist()
    
    # Initialize WhatsApp session
    print("Initializing WhatsApp session...")
    playwright, browser, context = initialize_whatsapp_session()
    
    try:
        page = context.new_page()
        page.goto("https://web.whatsapp.com", wait_until="networkidle")
        
        # Wait for connection
        print("Waiting for WhatsApp Web connection...")
        try:
            page.wait_for_selector('div[data-testid="default-user"]', timeout=30000)
            print("[OK] WhatsApp Web connected!")
            log_action("connected", "WhatsApp Reply connected")
        except PlaywrightTimeout:
            print("[WARN] May need QR scan for reply service")
            log_action("connection_warn", "QR scan may be needed", success=False)
        
        # Main monitoring loop
        print(f"\nMonitoring Approved folder every {CHECK_INTERVAL} seconds...")
        print("Press Ctrl+C to stop\n")
        
        while True:
            try:
                # Check for approved replies
                approval = check_approved_folder()
                
                if approval:
                    print(f"\n[OK] Found WhatsApp reply approval: {approval['filepath'].name}")
                    print(f"  To: {approval['contact']}")
                    print(f"  Message: {approval['message'][:100]}...")
                    
                    # Send the message
                    success = send_whatsapp_message(
                        context,
                        approval['contact'],
                        approval['message']
                    )
                    
                    if success:
                        reply_stats["replies_sent_today"] += 1
                        reply_stats["last_reply"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Move approval to Done
                        move_to_done(approval['filepath'])
                        
                        print(f"[OK] Message sent successfully!")
                        log_action("reply_sent", f"Sent to {approval['contact']}")
                    else:
                        print(f"[ERROR] Failed to send message")
                        log_action("reply_failed", f"Failed to send to {approval['contact']}", success=False)
                
                # Update dashboard
                update_dashboard()
                
                # Print status
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] Status: Replies sent today={reply_stats['replies_sent_today']}")
                
                # Wait for next check
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n\nReply monitor stopped by user")
                break
            except Exception as e:
                log_action("loop_error", str(e), success=False)
                time.sleep(5)
        
    except Exception as e:
        print(f"\nFatal error: {e}")
        log_action("fatal_error", str(e), success=False)
    finally:
        # Cleanup
        try:
            browser.close()
            playwright.stop()
        except Exception:
            pass
        
        print("\nWhatsApp Reply stopped")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nReply monitor stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
