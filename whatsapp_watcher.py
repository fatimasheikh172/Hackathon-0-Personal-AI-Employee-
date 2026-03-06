#!/usr/bin/env python3
"""
WhatsApp Watcher - Monitor WhatsApp Web for important messages
Uses Playwright with Chromium browser for automation
Updated with @with_retry decorator for resilient operations
"""

import os
import sys
import time
import json
import random
import re
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Import retry handler
from retry_handler import with_retry, TransientError, SystemError, get_retry_stats

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
NEEDS_ACTION_FOLDER = VAULT_PATH / "Needs_Action"
LOGS_FOLDER = VAULT_PATH / "Logs"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
SESSION_PATH = Path(os.getenv("WHATSAPP_SESSION_PATH", VAULT_PATH / "whatsapp_session"))
CHECK_INTERVAL = int(os.getenv("WHATSAPP_CHECK_INTERVAL", "30"))
KEYWORDS_STR = os.getenv("WHATSAPP_KEYWORDS", "urgent,asap,invoice,payment,help,price,quote,order")

# Parse keywords
KEYWORDS = [k.strip().lower() for k in KEYWORDS_STR.split(",")]

# Priority mapping
HIGH_PRIORITY_KEYWORDS = ["urgent", "asap", "payment", "invoice"]
MEDIUM_PRIORITY_KEYWORDS = ["help", "price", "quote"]
LOW_PRIORITY_KEYWORDS = ["order"]

# WhatsApp statistics
whatsapp_stats = {
    "messages_detected_today": 0,
    "high_priority_messages": 0,
    "pending_replies": 0,
    "last_check": None,
    "status": "Active"
}

# Processed messages tracking
processed_messages = set()


def get_log_file_path():
    """Get JSON log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"whatsapp_watcher_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"whatsapp_activity_{date_str}.txt"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, NEEDS_ACTION_FOLDER, SESSION_PATH]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True):
    """Log a WhatsApp action to log files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    whatsapp_stats["last_check"] = timestamp

    status = "[OK]" if success else "[ERROR]"
    log_entry = f"[{timestamp}] {status} {action_type}: {details}\n"

    try:
        with open(get_text_log_file_path(), "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"ERROR writing text log: {e}")

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
            "total_messages": 0,
            "total_high_priority": 0,
            "total_errors": 0
        }
    }


def save_json_log(log_data):
    """Save log data to JSON file"""
    try:
        log_data["summary"]["total_messages"] = whatsapp_stats["messages_detected_today"]
        log_data["summary"]["total_high_priority"] = whatsapp_stats["high_priority_messages"]
        log_data["summary"]["total_errors"] = whatsapp_stats.get("errors", 0)

        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR saving JSON log: {e}")
        return False


def load_processed_messages():
    """Load set of processed message IDs"""
    global processed_messages
    processed_file = VAULT_PATH / ".processed_whatsapp.json"

    if processed_file.exists():
        try:
            with open(processed_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                processed_messages = set(data.get("messages", []))
        except Exception:
            processed_messages = set()


def save_processed_message(message_id):
    """Save a processed message ID"""
    processed_messages.add(message_id)

    if len(processed_messages) > 1000:
        processed_messages = set(list(processed_messages)[-1000:])

    processed_file = VAULT_PATH / ".processed_whatsapp.json"
    try:
        with open(processed_file, "w", encoding="utf-8") as f:
            json.dump({"messages": list(processed_messages)}, f, indent=2)
    except Exception as e:
        log_action("save_error", f"Failed to save processed messages: {e}", success=False)


def get_priority(message_text):
    """Determine message priority based on keywords"""
    message_lower = message_text.lower()

    for keyword in HIGH_PRIORITY_KEYWORDS:
        if keyword in message_lower:
            return "high", keyword

    for keyword in MEDIUM_PRIORITY_KEYWORDS:
        if keyword in message_lower:
            return "medium", keyword

    for keyword in LOW_PRIORITY_KEYWORDS:
        if keyword in message_lower:
            return "low", keyword

    return "low", None


def create_whatsapp_action_file(contact_name, message_text, received_time, priority, keyword):
    """Create an action file in Needs_Action folder for WhatsApp message"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    message_id = f"wa_{timestamp}_{random.randint(1000, 9999)}"

    safe_name = re.sub(r'[^\w\s-]', '', contact_name)[:20].replace(" ", "_")
    filename = f"WHATSAPP_{safe_name}_{timestamp}.md"
    filepath = NEEDS_ACTION_FOLDER / filename

    message_preview = message_text[:200].replace("\n", " ")

    action_content = f"""---
type: whatsapp
from: {contact_name}
message: {message_preview}
received: {received_time}
priority: {priority}
status: pending
keyword_matched: {keyword if keyword else "none"}
message_id: {message_id}
---

## Message Content

{message_text}

---

## Suggested Actions

- [ ] Review message
- [ ] Draft reply
- [ ] Get human approval
- [ ] Send approved reply

---

## Notes

*Add your response and notes here*

---

*Created by WhatsApp Watcher at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""

    try:
        NEEDS_ACTION_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(action_content)

        whatsapp_stats["messages_detected_today"] += 1
        if priority == "high":
            whatsapp_stats["high_priority_messages"] += 1

        log_action("message_detected", f"From {contact_name} [{priority}]: {message_preview[:50]}...")
        save_processed_message(message_id)

        return filepath
    except Exception as e:
        log_action("create_action_error", f"Failed to create action file: {e}", success=False)
        return None


def human_like_delay(min_seconds=1, max_seconds=3):
    """Add human-like random delay"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)


def take_screenshot(page, step_name):
    """Take screenshot and save to Logs folder"""
    try:
        screenshot_path = LOGS_FOLDER / f"whatsapp_{step_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(screenshot_path))
        print(f"Screenshot saved: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        print(f"Failed to take screenshot: {e}")
        return None


def initialize_whatsapp_session():
    """Initialize WhatsApp Web session with improved connection handling"""
    playwright = sync_playwright().start()

    # Launch browser with improved stealth settings
    browser = playwright.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--window-size=1920,1080",
        ]
    )

    # Create context with user agent and viewport
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York"
    )

    # Add stealth script
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
    """)

    return playwright, browser, context


def connect_to_whatsapp(context):
    """Connect to WhatsApp Web with improved QR code handling"""
    print("\n" + "=" * 60)
    print("WHATSAPP WEB CONNECTION")
    print("=" * 60)

    page = context.new_page()

    # Try to load saved session
    session_file = SESSION_PATH / "whatsapp_session.json"
    if session_file.exists():
        print("Loading saved session...")
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            context.add_cookies(cookies)
            print("Session loaded, checking if still valid...")
        except Exception as e:
            print(f"Failed to load session: {e}")

    # Navigate to WhatsApp Web
    print("\nOpening WhatsApp Web...")
    try:
        page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)
        take_screenshot(page, "page_loaded")
    except Exception as e:
        print(f"[ERROR] Failed to load WhatsApp Web: {e}")
        log_action("connection_error", f"Failed to load page: {e}", success=False)
        return None

    # Wait 5 seconds after page load
    print("Waiting for page to stabilize...")
    time.sleep(5)
    take_screenshot(page, "page_stabilized")

    # Check if already logged in
    print("\nChecking if already logged in...")
    logged_in_selectors = [
        'div[data-testid="chat-list"]',
        'div[aria-label="Chat list"]',
        'div[data-testid="default-user"]'
    ]

    for selector in logged_in_selectors:
        try:
            if page.query_selector(selector):
                print(f"[OK] Already logged in (found: {selector})")
                take_screenshot(page, "already_logged_in")
                log_action("connected", "Connected with saved session")
                return page
        except Exception:
            continue

    print("Not logged in, waiting for QR code...")

    # Wait for QR code with multiple selectors
    qr_selectors = [
        'canvas[aria-label="Scan this QR code to link a device"]',
        'div[data-testid="qrcode"]',
        'canvas'
    ]

    qr_found = False
    for selector in qr_selectors:
        try:
            print(f"  Trying selector: {selector}")
            if page.wait_for_selector(selector, timeout=30000):
                print(f"  [OK] QR code found with selector: {selector}")
                qr_found = True
                take_screenshot(page, "qr_code_found")
                break
        except PlaywrightTimeout:
            print(f"  Selector failed: {selector}")
            continue
        except Exception as e:
            print(f"  Error: {e}")
            continue

    if not qr_found:
        print("\n[ERROR] Could not find QR code")
        log_action("qr_not_found", "QR code not found", success=False)
        take_screenshot(page, "qr_not_found")
        return None

    # QR code found - prompt user to scan
    print("\n" + "=" * 60)
    print("QR CODE READY - Please scan with your phone!")
    print("=" * 60)
    print("\nPlease scan the QR code with your WhatsApp mobile app:")
    print("1. Open WhatsApp on your phone")
    print("2. Go to Settings > Linked Devices")
    print("3. Tap 'Link a Device'")
    print("4. Point your camera at the QR code")
    print("\nWaiting for you to scan QR code (60 seconds)...")
    print("=" * 60 + "\n")

    # Wait for QR scan (up to 60 seconds)
    print("Waiting for login confirmation...")
    max_wait = 60
    check_interval = 5
    elapsed = 0

    while elapsed < max_wait:
        time.sleep(check_interval)
        elapsed += check_interval

        # Check if logged in
        for selector in logged_in_selectors:
            try:
                if page.query_selector(selector):
                    print(f"\n[OK] WhatsApp Web connected successfully!")
                    take_screenshot(page, "login_success")
                    log_action("connected", "WhatsApp Web connected after QR scan")

                    # Save session
                    save_whatsapp_session(context)

                    return page
            except Exception:
                continue

        print(f"  Waiting... ({elapsed}s/{max_wait}s)", end='\r')

    # Timeout
    print(f"\n\n[ERROR] QR scan timeout after {max_wait} seconds")
    print("Please try again or check your internet connection.")
    take_screenshot(page, "qr_timeout")
    log_action("qr_timeout", f"QR scan timeout after {max_wait}s", success=False)
    return None


def save_whatsapp_session(context):
    """Save WhatsApp session cookies"""
    try:
        SESSION_PATH.mkdir(parents=True, exist_ok=True)
        session_file = SESSION_PATH / "whatsapp_session.json"

        cookies = context.cookies()
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)

        print(f"\n[OK] Session saved to {session_file}")
        log_action("session_saved", f"Saved to {session_file}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save session: {e}")
        log_action("session_save_error", str(e), success=False)
        return False


def check_whatsapp_messages(context):
    """Check WhatsApp Web for new messages"""
    try:
        page = context.pages[0] if context.pages else context.new_page()

        if "web.whatsapp.com" not in page.url:
            page.goto("https://web.whatsapp.com", wait_until="domcontentloaded", timeout=60000)
            human_like_delay(2, 4)

        try:
            page.wait_for_selector('div[role="grid"]', timeout=10000)
        except PlaywrightTimeout:
            log_action("navigation_error", "Could not find chat list", success=False)
            return False

        chat_selectors = [
            'div[role="grid"] > div[role="row"]',
            'div[data-testid="chat-list"] > div',
            'div[id="pane-side"] > div > div > div'
        ]

        chats = []
        for selector in chat_selectors:
            try:
                chats = page.query_selector_all(selector)
                if chats:
                    break
            except Exception:
                continue

        if not chats:
            log_action("no_chats", "No chats found")
            return False

        for chat in chats:
            try:
                contact_elem = chat.query_selector('span[title]')
                contact_name = contact_elem.get_attribute("title") if contact_elem else "Unknown"

                unread_elem = chat.query_selector('span[data-testid="unread-msg-count"]')
                if not unread_elem:
                    continue

                message_elem = chat.query_selector('span[data-testid="message-preview"]')
                message_text = message_elem.inner_text() if message_elem else ""

                time_elem = chat.query_selector('span[data-testid="message-timestamp"]')
                timestamp = time_elem.get_attribute("title") if time_elem else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if not message_text:
                    continue

                message_hash = hash(f"{contact_name}:{message_text[:50]}")
                if message_hash in processed_messages:
                    continue

                priority, keyword = get_priority(message_text)

                if keyword or priority == "high":
                    create_whatsapp_action_file(
                        contact_name=contact_name,
                        message_text=message_text,
                        received_time=timestamp,
                        priority=priority,
                        keyword=keyword
                    )
                    human_like_delay(0.5, 1)

            except Exception as e:
                continue

        return True

    except Exception as e:
        log_action("check_error", f"Error checking messages: {e}", success=False)
        return False


def update_dashboard():
    """Update Dashboard.md with WhatsApp status"""
    try:
        if not DASHBOARD_FILE.exists():
            return False

        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            content = f.read()

        whatsapp_section = f"""## WhatsApp Status
- Watcher: {whatsapp_stats['status']}
- Messages Detected Today: {whatsapp_stats['messages_detected_today']}
- High Priority Messages: {whatsapp_stats['high_priority_messages']}
- Pending Replies: {whatsapp_stats['pending_replies']}
- Last Check: {whatsapp_stats['last_check'] or 'Never'}
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
    """Main function - runs WhatsApp watcher"""
    print("=" * 60)
    print("WhatsApp Watcher - AI Employee System")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Session Path: {SESSION_PATH}")
    print(f"Check Interval: {CHECK_INTERVAL} seconds")
    print(f"Keywords: {', '.join(KEYWORDS)}")
    print("=" * 60)

    ensure_folders_exist()
    load_processed_messages()

    print("\nInitializing WhatsApp Web session...")
    playwright, browser, context = initialize_whatsapp_session()

    # Connect to WhatsApp
    page = connect_to_whatsapp(context)

    if not page:
        print("\n[ERROR] Failed to connect to WhatsApp Web")
        print("Please check your internet connection and try again.")
        browser.close()
        playwright.stop()
        sys.exit(1)

    # Initial monitoring delay
    human_like_delay(3, 5)

    # Start monitoring
    print("\n" + "=" * 60)
    print("MONITORING STARTED")
    print("=" * 60)
    print(f"Checking for messages every {CHECK_INTERVAL} seconds...")
    print("Press Ctrl+C to stop\n")

    log_action("monitoring_started", f"Monitoring started with {CHECK_INTERVAL}s interval")

    while True:
        try:
            check_whatsapp_messages(context)
            update_dashboard()

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Status: Detected={whatsapp_stats['messages_detected_today']}, "
                  f"High Priority={whatsapp_stats['high_priority_messages']}")

            human_like_delay(CHECK_INTERVAL - 2, CHECK_INTERVAL + 2)

        except KeyboardInterrupt:
            print("\n\nWatcher stopped by user")
            break
        except Exception as e:
            log_action("loop_error", str(e), success=False)
            time.sleep(5)

    browser.close()
    playwright.stop()
    print("\nWhatsApp Watcher stopped")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nWatcher stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
