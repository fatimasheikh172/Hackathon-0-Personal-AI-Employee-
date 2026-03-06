#!/usr/bin/env python3
"""
Instagram Manager - 2026 Updated Version
Auto-post images with captions using Playwright automation with session persistence
Supports DRY_RUN mode, rate limiting, and comprehensive logging
"""

import os
import sys
import time
import json
import random
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from PIL import Image, ImageDraw, ImageFont

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"
SESSION_FOLDER = VAULT_PATH / "sessions" / "instagram_session"
SOCIAL_PENDING = VAULT_PATH / "Social_Content" / "pending"
SOCIAL_POSTED = VAULT_PATH / "Social_Content" / "posted"
SOCIAL_FAILED = VAULT_PATH / "Social_Content" / "failed"
POSTS_FOLDER = VAULT_PATH / "Instagram_Posts"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
COMPANY_HANDBOOK = VAULT_PATH / "Company_Handbook.md"
BUSINESS_GOALS = VAULT_PATH / "Business_Goals.md"

# Environment settings
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
INSTAGRAM_EMAIL = os.getenv("INSTAGRAM_EMAIL", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")
INSTAGRAM_POST_INTERVAL = int(os.getenv("INSTAGRAM_POST_INTERVAL", "24"))

# Rate limiting: 5 posts per day
MAX_POSTS_PER_DAY = 5
MIN_POST_INTERVAL_HOURS = 3

# Statistics
instagram_stats = {
    "last_post": None,
    "next_scheduled": None,
    "total_today": 0,
    "last_post_time": None
}


def get_log_file_path():
    """Get log file path with current date"""
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"instagram_{date_str}.json"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, SESSION_FOLDER, SOCIAL_PENDING, SOCIAL_POSTED, SOCIAL_FAILED, POSTS_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True, data=None):
    """Log an Instagram action to JSON log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if action_type == "post_created":
        instagram_stats["last_post"] = timestamp
        instagram_stats["total_today"] += 1
        instagram_stats["last_post_time"] = datetime.now()

    status = "[OK]" if success else "[ERROR]"
    log_entry = f"[{timestamp}] {status} {action_type}: {details}"
    print(log_entry)

    # JSON logging
    json_entry = {
        "timestamp": timestamp,
        "type": action_type,
        "details": details,
        "success": success,
        "dry_run": DRY_RUN
    }
    if data:
        json_entry["data"] = data

    try:
        log_data = load_json_log()
        log_data["actions"].append(json_entry)
        
        # Update summary
        log_data["summary"]["total_actions"] = len(log_data["actions"])
        log_data["summary"]["total_posts"] = sum(
            1 for a in log_data["actions"] 
            if a["type"] == "post_created" and a["success"]
        )
        log_data["summary"]["total_errors"] = sum(
            1 for a in log_data["actions"] 
            if not a["success"]
        )
        
        save_json_log(log_data)
    except Exception as e:
        print(f"[ERROR] Failed to write JSON log: {e}")


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
        "platform": "Instagram",
        "actions": [],
        "summary": {
            "total_actions": 0,
            "total_posts": 0,
            "total_errors": 0
        }
    }


def save_json_log(log_data):
    """Save log data to JSON file"""
    try:
        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to save JSON log: {e}")
        return False


def get_session_file():
    """Get session file path"""
    SESSION_FOLDER.mkdir(parents=True, exist_ok=True)
    return SESSION_FOLDER / "instagram_session.json"


def save_session_cookies(context):
    """Save session cookies to file"""
    try:
        cookies = context.cookies()
        session_file = get_session_file()

        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)

        log_action("session_saved", f"Session saved to {session_file}")
        return True
    except Exception as e:
        log_action("session_save_error", f"Failed to save session: {e}", success=False)
        return False


def load_session_cookies():
    """Load session cookies from file"""
    session_file = get_session_file()

    if session_file.exists():
        try:
            with open(session_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            
            # Check if cookies are expired
            now = datetime.now().timestamp()
            valid_cookies = []
            for cookie in cookies:
                if "expiry" not in cookie or cookie["expiry"] > now:
                    valid_cookies.append(cookie)
            
            if valid_cookies:
                log_action("session_loaded", "Loaded valid session cookies")
                return valid_cookies
            else:
                log_action("session_expired", "Session cookies expired")
                return None
        except Exception as e:
            log_action("session_load_error", f"Failed to load session: {e}", success=False)

    return None


def take_screenshot(page, step_name):
    """Take screenshot and save to Logs folder"""
    try:
        LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
        screenshot_path = LOGS_FOLDER / f"instagram_{step_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(screenshot_path), full_page=False)
        return screenshot_path
    except Exception as e:
        print(f"[DEBUG] Screenshot failed: {e}")
        return None


def check_rate_limit():
    """Check if we're within rate limits (5 posts/day, min 3 hours between posts)"""
    now = datetime.now()
    
    # Check daily limit
    log_data = load_json_log()
    today_posts = []
    
    for action in log_data["actions"]:
        if action["type"] == "post_created" and action["success"]:
            try:
                post_time = datetime.strptime(action["timestamp"], "%Y-%m-%d %H:%M:%S")
                if post_time.date() == now.date():
                    today_posts.append(post_time)
            except Exception:
                pass
    
    instagram_stats["total_today"] = len(today_posts)
    
    if len(today_posts) >= MAX_POSTS_PER_DAY:
        log_action("rate_limit_hit", f"Daily limit reached ({MAX_POSTS_PER_DAY}/day)", success=False)
        return False, "daily_limit"
    
    # Check minimum interval
    if today_posts:
        last_post = max(today_posts)
        time_since_last = (now - last_post).total_seconds() / 3600  # hours
        
        if time_since_last < MIN_POST_INTERVAL_HOURS:
            wait_until = last_post + timedelta(hours=MIN_POST_INTERVAL_HOURS)
            log_action("rate_limit_hit", f"Wait {MIN_POST_INTERVAL_HOURS}h between posts. Until {wait_until.strftime('%H:%M:%S')}", success=False)
            return False, wait_until
    
    return True, None


def create_text_image(text, company_name="AI Employee"):
    """
    Create a professional text image for Instagram post using Pillow
    Returns path to saved image file
    """
    print("\n" + "=" * 60)
    print("CREATE TEXT IMAGE")
    print("=" * 60)

    try:
        # Image dimensions (Instagram square post)
        width, height = 1080, 1080

        # Create image with gradient background
        img = Image.new('RGB', (width, height), color=(20, 10, 40))
        draw = ImageDraw.Draw(img)

        # Create gradient from dark blue to purple
        for y in range(height):
            r = int(20 + (50 - 20) * y / height)
            g = int(10 + (10 - 10) * y / height)
            b = int(40 + (80 - 40) * y / height)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Try to use a professional font
        try:
            title_font = ImageFont.truetype("arial.ttf", 36)
            text_font = ImageFont.truetype("arial.ttf", 48)
            bottom_font = ImageFont.truetype("arial.ttf", 28)
        except Exception:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            bottom_font = ImageFont.load_default()

        # Add company name at top
        draw.text((width // 2, 40), company_name, fill='white', font=title_font, anchor="mm")

        # Wrap and add main text centered
        max_chars_per_line = 40
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line) + len(word) < max_chars_per_line:
                current_line += word + " "
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.strip())

        # Calculate text position for vertical centering
        line_height = 60
        total_text_height = len(lines) * line_height
        start_y = (height - total_text_height) // 2

        # Draw each line
        for i, line in enumerate(lines):
            y = start_y + i * line_height
            draw.text((width // 2, y), line, fill='white', font=text_font, anchor="mm")

        # Add date at bottom
        date_str = datetime.now().strftime("%B %d, %Y")
        draw.text((width // 2, height - 60), date_str, fill='white', font=bottom_font, anchor="mm")

        # Add decorative elements
        draw.line([(100, 80), (width - 100, 80)], fill='white', width=2)
        draw.line([(100, height - 100), (width - 100, height - 100)], fill='white', width=2)

        # Save image
        POSTS_FOLDER.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_path = POSTS_FOLDER / f"post_{timestamp}.png"

        img.save(str(image_path), "PNG", quality=95)

        print(f"Image created: {image_path}")
        print(f"Dimensions: {width}x{height}")
        log_action("image_created", f"Created {image_path.name}")

        return image_path

    except Exception as e:
        print(f"[ERROR] Failed to create image: {e}")
        log_action("image_error", str(e), success=False)

        # Fallback simple image
        try:
            img = Image.new('RGB', (width, height), color='black')
            draw = ImageDraw.Draw(img)
            draw.text((width // 2, height // 2), text[:50], fill='white', anchor="mm")
            
            POSTS_FOLDER.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = POSTS_FOLDER / f"post_{timestamp}_fallback.png"
            img.save(str(image_path), "PNG")

            return image_path
        except Exception:
            return None


def initialize_browser(playwright):
    """Initialize browser with anti-detection settings"""
    browser = playwright.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-infobars",
            "--window-size=1920,1080",
        ]
    )

    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York"
    )

    # Stealth scripts
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
        Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
    """)

    return browser, context


def handle_popups(page):
    """Handle Instagram popups (Save Login, Notifications)"""
    print("\nHandling popups...")
    
    # Handle "Save Login Info" popup
    not_now_selectors = [
        'button:has-text("Not now")',
        'button:has-text("Not Now")',
        'div[role="button"]:has-text("Not now")'
    ]
    
    for selector in not_now_selectors:
        try:
            btn = page.query_selector(selector)
            if btn:
                btn.click()
                time.sleep(2)
                print("  Dismissed save login popup")
                break
        except Exception:
            pass
    
    time.sleep(2)
    
    # Handle "Turn on Notifications" popup
    for selector in not_now_selectors:
        try:
            btn = page.query_selector(selector)
            if btn:
                btn.click()
                time.sleep(2)
                print("  Dismissed notifications popup")
                break
        except Exception:
            pass
    
    return True


def login_to_instagram(context, test_mode=False):
    """
    Login to Instagram with retry logic and session persistence
    Returns True if login successful
    """
    print("\n" + "=" * 60)
    print("INSTAGRAM LOGIN")
    print("=" * 60)

    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        retry_count += 1
        print(f"\nLogin attempt {retry_count}/{max_retries}")

        try:
            page = context.new_page()

            # Check for saved session
            cookies = load_session_cookies()

            if cookies and not test_mode:
                print("Loading saved session...")
                context.add_cookies(cookies)

                page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
                time.sleep(3)

                take_screenshot(page, "session_check")

                # Check if logged in
                if (page.query_selector('[aria-label="Profile"]') or 
                    page.query_selector('img[alt="Profile picture"]') or
                    page.query_selector('[aria-label="New post"]')):
                    print("[OK] Logged in with saved session!")
                    log_action("login_success", "Logged in with saved session")
                    handle_popups(page)
                    return True
                else:
                    print("Session expired, logging in again...")
                    context.clear_cookies()

            # Fresh login
            print("Opening Instagram login page...")
            page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)

            take_screenshot(page, "login_page")

            if test_mode:
                print("[TEST MODE] Skipping actual login")
                log_action("login_test", "Test mode - login skipped")
                return True

            if not INSTAGRAM_EMAIL or not INSTAGRAM_PASSWORD:
                print("[ERROR] Instagram credentials not found in .env file")
                log_action("login_error", "Credentials missing", success=False)
                return False

            # Enter username - 2026 selectors
            print("Entering username...")
            username_field = None
            username_selectors = [
                'input[name="username"]',
                'input[aria-label="Phone number, username, or email"]',
                'input[type="text"]'
            ]
            
            for selector in username_selectors:
                username_field = page.query_selector(selector)
                if username_field:
                    print(f"  Found username field: {selector}")
                    break

            if username_field:
                username_field.fill(INSTAGRAM_EMAIL)
                time.sleep(random.uniform(0.5, 1.5))

            # Enter password
            print("Entering password...")
            password_field = None
            password_selectors = [
                'input[name="password"]',
                'input[aria-label="Password"]',
                'input[type="password"]'
            ]
            
            for selector in password_selectors:
                password_field = page.query_selector(selector)
                if password_field:
                    print(f"  Found password field: {selector}")
                    break

            if password_field:
                password_field.fill(INSTAGRAM_PASSWORD)
                time.sleep(2)

            # Click Login
            print("Clicking login...")
            login_selectors = [
                'button[type="submit"]',
                'div[role="button"]:has-text("Log in")',
                'button:has-text("Log in")'
            ]
            
            login_button = None
            for selector in login_selectors:
                login_button = page.query_selector(selector)
                if login_button:
                    print(f"  Found login button: {selector}")
                    break

            if login_button:
                login_button.click()
                time.sleep(8)

            take_screenshot(page, "login_submitted")

            # Check for verification
            current_url = page.url
            if "challenge" in current_url.lower() or "checkpoint" in current_url.lower():
                print("[WARN] Verification challenge detected!")
                take_screenshot(page, "challenge")
                print("Please complete verification manually in the browser.")
                time.sleep(30)  # Wait for manual verification

            # Wait for home feed
            try:
                page.wait_for_selector('[aria-label="Profile"]', timeout=60000)
                time.sleep(3)

                take_screenshot(page, "login_success")
                print("[OK] Instagram login successful!")
                log_action("login_success", "Fresh login completed")

                handle_popups(page)
                save_session_cookies(context)
                return True

            except PlaywrightTimeout:
                # Check URL
                if "instagram.com" in current_url and "login" not in current_url.lower():
                    print("[OK] Login successful (URL check)!")
                    save_session_cookies(context)
                    return True

                print("[WARN] Login timeout")
                take_screenshot(page, "login_timeout")

                if retry_count < max_retries:
                    print(f"Retrying... ({retry_count}/{max_retries})")
                    time.sleep(2)
                    continue
                else:
                    log_action("login_timeout", "Login timed out after all retries", success=False)
                    return False

        except Exception as e:
            print(f"[ERROR] Login failed: {e}")
            log_action("login_error", str(e), success=False)

            if retry_count < max_retries:
                print(f"Retrying... ({retry_count}/{max_retries})")
                time.sleep(2)
            else:
                return False

    return False


def post_image(image_path, caption, context, test_mode=False):
    """
    Post an image with caption on Instagram
    Returns True if successful
    """
    print("\n" + "=" * 60)
    print("POST IMAGE")
    print("=" * 60)
    print(f"Image: {image_path}")
    print(f"Caption: {caption[:100]}...")
    print(f"DRY_RUN: {DRY_RUN or test_mode}")
    print("=" * 60)

    # Validate
    if not image_path or not Path(image_path).exists():
        log_action("post_error", f"Image not found: {image_path}", success=False)
        return False

    if not caption or not caption.strip():
        log_action("post_error", "Empty caption", success=False)
        return False

    # Check rate limit
    within_limit, reason = check_rate_limit()
    if not within_limit:
        print(f"[WARN] Rate limit: {reason}")
        return False

    if DRY_RUN or test_mode:
        print("[DRY_RUN] Skipping actual post")
        log_action("post_dry_run", f"Would post image: {image_path}")
        return True

    try:
        page = context.pages[0] if context.pages else context.new_page()

        if "instagram.com" not in page.url:
            page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

        take_screenshot(page, "before_create")

        # Click Create/New Post button - 2026 selectors
        print("Opening create post dialog...")
        create_selectors = [
            '[aria-label="New post"]',
            '[data-testid="new-post-button"]',
            'svg[aria-label="New post"]',
            'a[href="/create/"]',
            '[role="button"]:has-text("New")'
        ]
        
        create_button = None
        for selector in create_selectors:
            create_button = page.query_selector(selector)
            if create_button:
                print(f"  Found create button: {selector}")
                break

        if create_button:
            create_button.click()
            time.sleep(3)
        else:
            print("[ERROR] Create button not found")
            log_action("post_error", "Create button not found", success=False)
            take_screenshot(page, "create_error")
            return False

        take_screenshot(page, "create_opened")

        # Upload image - use hidden file input
        print("Uploading image...")
        upload_success = False

        # Method: Use JavaScript to trigger file input
        try:
            page.evaluate("""
                () => {
                    const input = document.querySelector('input[type="file"]');
                    if (input) {
                        input.style.display = 'block';
                        input.style.visibility = 'visible';
                        input.style.opacity = '1';
                    }
                }
            """)
            
            # Find and use file input
            file_input = page.query_selector('input[type="file"]')
            if file_input:
                file_input.set_input_files(str(image_path))
                time.sleep(3)
                upload_success = True
                print("  Image uploaded via file input")
            else:
                # Try drag-drop area
                drop_area = page.query_selector('[role="presentation"]')
                if drop_area:
                    drop_area.set_input_files(str(image_path))
                    time.sleep(3)
                    upload_success = True
                    print("  Image uploaded via drop area")
        except Exception as e:
            print(f"  Upload method failed: {e}")

        if not upload_success:
            # Fallback: Try alternative method
            print("  Trying alternative upload method...")
            try:
                page.set_input_files('input[type="file"]', str(image_path))
                time.sleep(3)
                upload_success = True
            except Exception as e:
                print(f"  Alternative upload failed: {e}")

        if not upload_success:
            log_action("post_error", "Failed to upload image", success=False)
            take_screenshot(page, "upload_error")
            return False

        take_screenshot(page, "image_uploaded")

        # Click Next
        print("Clicking Next...")
        next_selectors = [
            'button:has-text("Next")',
            'div[role="button"]:has-text("Next")',
            'button[aria-label="Next"]'
        ]
        
        next_button = None
        for selector in next_selectors:
            next_button = page.query_selector(selector)
            if next_button:
                next_button.click()
                time.sleep(2)
                print(f"  Clicked Next: {selector}")
                break

        take_screenshot(page, "filter_screen")

        # Click Next again (filter screen)
        for selector in next_selectors:
            next_button = page.query_selector(selector)
            if next_button:
                next_button.click()
                time.sleep(2)
                print(f"  Clicked Next (filters): {selector}")
                break

        take_screenshot(page, "caption_screen")

        # Enter caption
        print("Entering caption...")
        caption_selectors = [
            'textarea[aria-label="Write a caption..."]',
            'textarea[placeholder="Write a caption..."]',
            'div[contenteditable="true"][aria-label*="caption"]',
            'textarea'
        ]
        
        caption_field = None
        for selector in caption_selectors:
            caption_field = page.query_selector(selector)
            if caption_field:
                print(f"  Found caption field: {selector}")
                break

        if caption_field:
            caption_field.click()
            time.sleep(0.5)
            
            # Type caption
            for char in caption:
                caption_field.type(char, delay=random.uniform(10, 50))
                time.sleep(random.uniform(0.01, 0.03))

            time.sleep(2)
            take_screenshot(page, "caption_entered")
        else:
            print("[WARN] Caption field not found, proceeding without caption")

        # Click Share/Post button
        print("Posting...")
        share_selectors = [
            'button:has-text("Share")',
            'div[role="button"]:has-text("Share")',
            'button[aria-label="Share"]',
            'button:has-text("Post")'
        ]
        
        share_button = None
        for selector in share_selectors:
            share_button = page.query_selector(selector)
            if share_button:
                share_button.click()
                time.sleep(3)
                print(f"  Clicked Share: {selector}")
                break

        if share_button:
            time.sleep(5)
            take_screenshot(page, "post_submitted")
            
            print("[OK] Post created successfully!")
            log_action("post_created", f"Posted image: {Path(image_path).name}")
            return True
        else:
            print("[ERROR] Share button not found")
            log_action("post_error", "Share button not found", success=False)
            take_screenshot(page, "share_error")
            return False

    except Exception as e:
        print(f"[ERROR] Post failed: {e}")
        log_action("post_error", str(e), success=False)
        take_screenshot(page, "post_error")
        return False


def get_recent_comments(context, max_comments=10):
    """
    Get recent comments on posts
    Returns list of comment data
    """
    print("\n" + "=" * 60)
    print("GET RECENT COMMENTS")
    print("=" * 60)

    comments = []

    try:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # Look for notification/comment elements
        comment_selectors = [
            '[aria-label="Comment"]',
            'div[role="button"] span',
            'article span'
        ]
        
        elements = []
        for selector in comment_selectors:
            elements = page.query_selector_all(selector)
            if elements:
                break

        for elem in elements[:max_comments]:
            try:
                text = elem.inner_text()
                if text.strip():
                    comments.append({
                        "text": text[:280],
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception:
                pass

        log_action("comments_fetched", f"Found {len(comments)} comments")
        return comments

    except Exception as e:
        log_action("comments_error", str(e), success=False)
        return []


def generate_caption(topic, hashtag_count=15):
    """
    Generate an Instagram caption with hashtags from a topic
    Returns caption string
    """
    print("\n" + "=" * 60)
    print("GENERATE CAPTION")
    print("=" * 60)
    print(f"Topic: {topic}")

    # Read company context
    company_name = "AI Employee"
    
    if COMPANY_HANDBOOK.exists():
        try:
            with open(COMPANY_HANDBOOK, "r", encoding="utf-8") as f:
                content = f.read()
            name_match = re.search(r'#?\s*(\w+\s*Employee)', content)
            if name_match:
                company_name = name_match.group(1)
        except Exception:
            pass

    topic = topic.strip()
    
    # Generate caption with emojis and hashtags
    intro_templates = [
        f"✨ {topic}",
        f"🚀 Exciting updates: {topic}",
        f"💡 Innovation in action: {topic}",
        f"🎯 Focus on excellence: {topic}",
    ]
    
    body_templates = [
        f"Driving forward with dedication and creativity. {company_name} continues to deliver exceptional results.",
        f"Committed to excellence in every task. Together we achieve more.",
        f"Building the future through smart automation and innovative solutions.",
        f"Success comes from consistent effort and attention to detail.",
    ]
    
    # Common business hashtags
    hashtags = [
        "#BusinessGrowth", "#Innovation", "#Success", "#Entrepreneur", 
        "#Motivation", "#Leadership", "#Productivity", "#AI", "#Automation",
        "#DigitalTransformation", "#BusinessStrategy", "#Growth", "#Mindset",
        "#ProfessionalDevelopment", "#TeamWork", "#Excellence", "#FutureOfWork",
        "#Technology", "#BusinessSuccess", "#Inspiration"
    ]
    
    caption = f"{random.choice(intro_templates)}\n\n{random.choice(body_templates)}\n\n"
    
    # Add hashtags
    selected_hashtags = random.sample(hashtags, min(hashtag_count, len(hashtags)))
    caption += " ".join(selected_hashtags)
    
    # Ensure under 2200 chars (Instagram limit)
    if len(caption) > 2200:
        caption = caption[:2197] + "..."
    
    print(f"Generated caption: {len(caption)} characters")
    print(f"Hashtags: {len(selected_hashtags)}")

    log_action("caption_generated", f"Caption: {caption[:100]}...")
    return caption


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Instagram Manager')
    parser.add_argument('--test', action='store_true', help='Test mode')
    parser.add_argument('--image', type=str, help='Image path to post')
    parser.add_argument('--caption', type=str, help='Caption content')
    parser.add_argument('--topic', type=str, help='Topic for auto-generation')
    parser.add_argument('--comments', action='store_true', help='Get recent comments')
    args = parser.parse_args()

    print("=" * 60)
    print("Instagram Manager - AI Employee System (2026)")
    print("=" * 60)
    print(f"Vault: {VAULT_PATH}")
    print(f"DRY_RUN: {DRY_RUN or args.test}")
    print("=" * 60)

    ensure_folders_exist()

    if not args.test and (not INSTAGRAM_EMAIL or not INSTAGRAM_PASSWORD):
        print("\n[ERROR] Instagram credentials not set in .env")
        sys.exit(1)

    try:
        playwright = sync_playwright().start()
        browser, context = initialize_browser(playwright)

        try:
            # Login
            login_success = login_to_instagram(context, args.test)
            
            if not login_success and not args.test:
                print("\n[ERROR] Login failed")
                sys.exit(1)

            # Get comments
            if args.comments:
                comments = get_recent_comments(context)
                print(f"\nRecent comments: {len(comments)}")
                for c in comments[:5]:
                    print(f"  - {c['text'][:80]}...")

            # Post image
            if args.image:
                caption = args.caption or generate_caption(args.topic or "Business update")
                success = post_image(args.image, caption, context, args.test)
            elif args.topic:
                # Create text image and post
                caption = generate_caption(args.topic)
                image_path = create_text_image(args.topic)
                if image_path:
                    success = post_image(str(image_path), caption, context, args.test)
                else:
                    print("[ERROR] Failed to create image")
                    success = False
            else:
                content = generate_caption("Business automation and productivity")
                image_path = create_text_image("Driving innovation through automation")
                if image_path:
                    success = post_image(str(image_path), content, context, args.test)
                else:
                    print("[ERROR] Failed to create image")
                    success = False

            if success:
                print("\n" + "=" * 60)
                print("INSTAGRAM OPERATION SUCCESSFUL")
                print("=" * 60)
            else:
                print("\n[ERROR] Operation failed")
                sys.exit(1)

        finally:
            try:
                browser.close()
                playwright.stop()
            except Exception:
                pass

        return success

    except Exception as e:
        print(f"\n[ERROR] Fatal: {e}")
        log_action("fatal_error", str(e), success=False)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nStopped by user")
        sys.exit(0)
