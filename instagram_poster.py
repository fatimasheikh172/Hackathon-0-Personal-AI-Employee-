#!/usr/bin/env python3
"""
Instagram Poster - Auto-post on Instagram using Playwright automation
No API required - uses browser automation with anti-detection
Creates text images using Pillow for posts
"""

import os
import sys
import time
import json
import random
import re
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from PIL import Image, ImageDraw, ImageFont

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"
SESSION_FOLDER = VAULT_PATH / "instagram_session"
POSTS_FOLDER = VAULT_PATH / "Instagram_Posts"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
COMPANY_HANDBOOK = VAULT_PATH / "Company_Handbook.md"
BUSINESS_GOALS = VAULT_PATH / "Business_Goals.md"
INSTAGRAM_TEMPLATES = VAULT_PATH / "instagram_templates.md"

# Instagram credentials from .env
INSTAGRAM_EMAIL = os.getenv("INSTAGRAM_EMAIL", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")
INSTAGRAM_POST_INTERVAL = int(os.getenv("INSTAGRAM_POST_INTERVAL", "24"))

# Instagram statistics
instagram_stats = {
    "last_post": None,
    "next_scheduled": None,
    "total_this_week": 0,
    "auto_posting": "Active"
}


def get_log_file_path():
    """Get log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"instagram_poster_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"instagram_activity_{date_str}.txt"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, SESSION_FOLDER, POSTS_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True):
    """Log an Instagram action to log files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if action_type == "post_created":
        instagram_stats["last_post"] = timestamp
        instagram_stats["total_this_week"] += 1
    
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
            "total_posts": 0,
            "total_errors": 0
        }
    }


def save_json_log(log_data):
    """Save log data to JSON file"""
    try:
        log_data["summary"]["total_posts"] = instagram_stats["total_this_week"]
        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR saving JSON log: {e}")
        return False


def get_session_file():
    """Get session file path"""
    return SESSION_FOLDER / "instagram_session.json"


def save_session_cookies(context):
    """Save session cookies to file"""
    try:
        cookies = context.cookies()
        session_file = get_session_file()
        SESSION_FOLDER.mkdir(parents=True, exist_ok=True)
        
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
            log_action("session_loaded", "Loaded saved session cookies")
            return cookies
        except Exception as e:
            log_action("session_load_error", f"Failed to load session: {e}", success=False)
    
    return None


def take_screenshot(page, step_name):
    """Take screenshot and save to Logs folder"""
    try:
        screenshot_path = LOGS_FOLDER / f"instagram_{step_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(screenshot_path))
        print(f"Screenshot saved: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        print(f"Failed to take screenshot: {e}")
        return None


def create_text_image(text, company_name="AI Employee"):
    """
    Create a professional text image for Instagram post using Pillow
    
    Args:
        text: Text content for the image
        company_name: Company name to display at top
    
    Returns:
        Path to saved image file
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
        
        # Try to use a professional font, fallback to default
        try:
            title_font = ImageFont.truetype("arial.ttf", 36)
            text_font = ImageFont.truetype("arial.ttf", 48)
            bottom_font = ImageFont.truetype("arial.ttf", 28)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            bottom_font = ImageFont.load_default()
        
        # Add company name at top
        draw.text((width // 2, 40), company_name, fill='white', font=title_font, anchor="mm")
        
        # Add main text centered
        # Wrap text to fit width
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
        # Top border
        draw.line([(100, 80), (width - 100, 80)], fill='white', width=2)
        # Bottom border
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
        
        # Create a simple fallback image
        try:
            img = Image.new('RGB', (width, height), color='black')
            draw = ImageDraw.Draw(img)
            draw.text((width // 2, height // 2), text[:50], fill='white', anchor="mm")
            
            POSTS_FOLDER.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = POSTS_FOLDER / f"post_{timestamp}_fallback.png"
            img.save(str(image_path), "PNG")
            
            return image_path
        except:
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
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        timezone_id="America/New_York"
    )
    
    # Add stealth script
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})
    """)
    
    return browser, context


def handle_verification(page):
    """
    Handle Instagram verification challenge
    
    Args:
        page: Playwright page object
    
    Returns:
        True if verified, False if timeout
    """
    print("\n" + "=" * 60)
    print("VERIFICATION REQUIRED")
    print("=" * 60)
    print("\nInstagram requires verification. Please complete it in the browser window.")
    print("Check your phone or email for a verification code.")
    print("\nWaiting up to 120 seconds for you to complete verification...\n")
    
    start_time = time.time()
    max_wait = 120  # 2 minutes
    check_interval = 5  # Check every 5 seconds
    
    while time.time() - start_time < max_wait:
        time.sleep(check_interval)
        
        current_url = page.url
        
        # Check if verification is complete
        if "challenge" not in current_url.lower() and "checkpoint" not in current_url.lower():
            if "instagram.com" in current_url:
                print(f"[OK] Verification complete! Current URL: {current_url}")
                take_screenshot(page, "verified")
                return True
        
        # Show progress
        elapsed = int(time.time() - start_time)
        remaining = max_wait - elapsed
        print(f"  Waiting for verification... ({elapsed}s elapsed, {remaining}s remaining)", end='\r')
    
    print(f"\n\n[ERROR] Verification timeout after {max_wait} seconds")
    print("Please try logging in again later or complete verification manually in your browser.")
    take_screenshot(page, "verification_timeout")
    return False


def handle_onetap_popup(page):
    """
    Handle Instagram Save Login Info popup (accounts/onetap)
    
    Args:
        page: Playwright page object
    
    Returns:
        True if handled or skipped, False if error
    """
    print("\nHandling Save Login Info popup (onetap)...")
    take_screenshot(page, "onetap_popup")
    
    # Try multiple selectors for "Not Now" button
    selectors = [
        'button:has-text("Not now")',
        'button:has-text("Not Now")',
        'div[role="button"]:has-text("Not now")',
        'div[role="button"]:has-text("Not Now")',
        'a:has-text("Not now")',
        'a:has-text("Not Now")'
    ]
    
    for selector in selectors:
        try:
            print(f"  Trying selector: {selector}")
            not_now_btn = page.query_selector(selector)
            if not_now_btn:
                print(f"  Found 'Not Now' button with selector: {selector}")
                not_now_btn.click()
                time.sleep(3)
                take_screenshot(page, "onetap_dismissed")
                print("  [OK] Save Login popup dismissed")
                return True
        except Exception as e:
            print(f"  Selector failed: {selector} - {e}")
            continue
    
    # If all selectors fail, just navigate to home page
    print("  [INFO] Could not find 'Not Now' button, navigating to home page...")
    try:
        page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)
        take_screenshot(page, "onetap_navigated")
        print("  [OK] Navigated to home page directly")
        return True
    except Exception as e:
        print(f"  [ERROR] Failed to navigate: {e}")
        return False


def handle_notifications_popup(page):
    """
    Handle Instagram Turn on Notifications popup
    
    Args:
        page: Playwright page object
    
    Returns:
        True if handled or skipped
    """
    print("\nHandling Notifications popup...")
    
    # Try multiple selectors for "Not Now" button
    selectors = [
        'button:has-text("Not Now")',
        'button:has-text("Not now")',
        'div[role="button"]:has-text("Not Now")',
        'div[role="button"]:has-text("Not now")'
    ]
    
    for selector in selectors:
        try:
            print(f"  Trying selector: {selector}")
            not_now_btn = page.query_selector(selector)
            if not_now_btn:
                print(f"  Found 'Not Now' button with selector: {selector}")
                not_now_btn.click()
                time.sleep(3)
                take_screenshot(page, "notifications_dismissed")
                print("  [OK] Notifications popup dismissed")
                return True
        except Exception as e:
            print(f"  Selector failed: {selector} - {e}")
            continue
    
    print("  [INFO] Notifications popup not found or already dismissed")
    return True


def handle_popups(page):
    """
    Handle Instagram popups (Save Login, Notifications)
    
    Args:
        page: Playwright page object
    
    Returns:
        True if handled successfully
    """
    # Handle "Save Login Info" popup
    handle_onetap_popup(page)
    
    # Wait before checking notifications
    time.sleep(3)
    
    # Handle "Turn on Notifications" popup
    handle_notifications_popup(page)
    
    return True


def login_to_instagram(context, test_mode=False):
    """
    Login to Instagram with improved verification and popup handling
    """
    print("\n" + "=" * 60)
    print("INSTAGRAM LOGIN")
    print("=" * 60)
    
    try:
        page = context.new_page()
        
        # Check for saved session
        cookies = load_session_cookies()
        
        if cookies and not test_mode:
            print("Loading saved session...")
            context.add_cookies(cookies)
            
            page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            
            take_screenshot(page, "session_check")
            
            # Check if logged in by looking for profile icon
            if page.query_selector('[aria-label="Profile"]') or page.query_selector('img[alt="Profile picture"]'):
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
        time.sleep(5)  # Wait 5 seconds after page load
        
        take_screenshot(page, "login_page")
        
        if test_mode:
            print("[TEST MODE] Skipping actual login")
            log_action("login_test", "Test mode - login skipped")
            return True
        
        if not INSTAGRAM_EMAIL or not INSTAGRAM_PASSWORD:
            print("[ERROR] Instagram credentials not found in .env file")
            log_action("login_error", "Credentials missing", success=False)
            return False
        
        # Enter username/email - try multiple selectors
        print("Entering username...")
        username_field = None
        for selector in ['input[name="username"]', 'input[aria-label="Phone number, username, or email"]', 'input[type="text"]']:
            username_field = page.query_selector(selector)
            if username_field:
                print(f"  Found username field with selector: {selector}")
                break
        
        if username_field:
            username_field.fill(INSTAGRAM_EMAIL)
            time.sleep(random.uniform(0.5, 1.5))
        
        # Enter password - try multiple selectors
        print("Entering password...")
        password_field = None
        for selector in ['input[name="password"]', 'input[aria-label="Password"]', 'input[type="password"]']:
            password_field = page.query_selector(selector)
            if password_field:
                print(f"  Found password field with selector: {selector}")
                break
        
        if password_field:
            password_field.fill(INSTAGRAM_PASSWORD)
            time.sleep(2)  # Wait 2 seconds before clicking login
        
        # Click login - try multiple selectors
        print("Clicking login...")
        login_button = None
        for selector in ['button[type="submit"]', 'div[role="button"]:has-text("Log in")', 'button:has-text("Log in")']:
            login_button = page.query_selector(selector)
            if login_button:
                print(f"  Found login button with selector: {selector}")
                break
        
        if login_button:
            login_button.click()
            time.sleep(10)  # Wait 10 seconds after clicking login
        
        take_screenshot(page, "login_submitted")
        
        # Check current URL after login attempt
        current_url = page.url
        print(f"Current URL after login: {current_url}")
        
        # Check for verification challenge
        if "challenge" in current_url.lower() or "checkpoint" in current_url.lower():
            print("\n[WARN] Verification challenge detected!")
            take_screenshot(page, "challenge_detected")
            
            # Handle verification
            verified = handle_verification(page)
            
            if not verified:
                log_action("login_verification_failed", "User did not complete verification", success=False)
                return False
            
            # After verification, handle popups
            handle_popups(page)
        
        # Check for Save Login popup (onetap URL)
        elif "accounts/onetap" in current_url.lower():
            print("\n[INFO] Save Login Info page detected (onetap)")
            
            # Handle onetap popup
            handle_onetap_popup(page)
            
            # Navigate directly to home page after handling onetap
            print("\nNavigating to home page...")
            try:
                page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
                time.sleep(3)
                take_screenshot(page, "home_navigated")
            except Exception as e:
                print(f"Navigation warning: {e}")
            
            # Check for notifications popup after navigation
            handle_notifications_popup(page)
            
            # Save session cookies immediately
            save_session_cookies(context)
            
            print("\n[OK] Login successful! (onetap handled)")
        
        # Check if successfully logged in (normal case)
        elif "instagram.com" in current_url and "login" not in current_url.lower():
            print("\n[OK] Login successful!")
            handle_popups(page)
            save_session_cookies(context)
        
        # Wait for home feed and verify login
        try:
            # Check if already on home page
            if "instagram.com" in page.url and "login" not in page.url.lower() and "challenge" not in page.url.lower():
                print("[OK] Already on home page")
            else:
                page.wait_for_selector('[aria-label="Profile"]', timeout=60000)
            
            time.sleep(3)
            take_screenshot(page, "login_success")
            
            print("[OK] Instagram login successful!")
            log_action("login_success", "Fresh login completed")
            
            # Save session if not already saved
            if "accounts/onetap" not in current_url.lower():
                save_session_cookies(context)
            
            return True
            
        except PlaywrightTimeout:
            # Check URL again
            current_url = page.url
            
            # Consider successful if on instagram.com and not on login/challenge
            if "instagram.com" in current_url and "login" not in current_url.lower() and "challenge" not in current_url.lower():
                print("[OK] Login successful (URL check passed)!")
                save_session_cookies(context)
                return True
            
            if "challenge" in current_url.lower() or "checkpoint" in current_url.lower():
                print("[WARN] Still on challenge page - verification may be needed")
                verified = handle_verification(page)
                if verified:
                    handle_popups(page)
                    save_session_cookies(context)
                    return True
            
            print("[WARN] Login timeout - may need verification")
            take_screenshot(page, "login_timeout")
            log_action("login_timeout", "Login timed out", success=False)
            return False
        
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        log_action("login_error", str(e), success=False)
        return False


def create_post(caption, image_path, context, test_mode=False):
    """
    Create and post on Instagram with improved file upload handling

    Args:
        caption: Post caption text
        image_path: Path to image file to upload
        context: Playwright browser context
        test_mode: If True, don't actually post

    Returns:
        True if successful, False otherwise
    """
    print("\n" + "=" * 60)
    print("CREATE INSTAGRAM POST")
    print("=" * 60)
    print(f"Caption: {caption[:100]}...")
    print(f"Image: {image_path}")
    print("=" * 60)

    try:
        if test_mode:
            print("[TEST MODE] Skipping actual post")
            log_action("post_test", f"Test post: {caption[:100]}...")
            return True

        page = context.pages[0] if context.pages else context.new_page()

        if "instagram.com" not in page.url:
            page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

        take_screenshot(page, "before_create")

        # Click Create/Plus button
        print("Opening create post dialog...")
        create_button = None
        for selector in ['[aria-label="New post"]', '[data-testid="new-post-button"]', 'svg[aria-label="New post"]', 'a[href="/create/"]']:
            create_button = page.query_selector(selector)
            if create_button:
                print(f"  Found create button with selector: {selector}")
                break

        if create_button:
            create_button.click()
            time.sleep(3)  # Wait 3 seconds for dialog to appear
        else:
            # Try clicking the + icon in stories area
            plus_button = page.query_selector('[aria-label="Add to story"]')
            if plus_button:
                plus_button.click()
                time.sleep(3)

        take_screenshot(page, "create_opened")

        # Upload image with special handling for Instagram's hidden file input
        print("Uploading image...")
        upload_success = False
        
        # Method 1: Make hidden file input visible and upload
        print("\n  Method 1: Making file input visible...")
        try:
            # Use JavaScript to make all file inputs visible
            page.evaluate("""
                () => {
                    const inputs = document.querySelectorAll('input[type="file"]');
                    inputs.forEach(input => {
                        input.style.display = 'block';
                        input.style.opacity = '1'; 
                        input.style.visibility = 'visible';
                        input.style.position = 'fixed';
                        input.style.top = '0';
                        input.style.left = '0';
                        input.style.zIndex = '9999';
                        input.style.width = '100px';
                        input.style.height = '100px';
                    });
                }
            """)
            
            time.sleep(2)  # Wait 2 seconds after making visible
            take_screenshot(page, "input_made_visible")
            
            # Try upload using locator with extended timeout
            file_input = page.locator("input[type='file']")
            if file_input.count() > 0:
                file_input.first.set_input_files(str(image_path), timeout=60000)
                print(f"  [OK] Image uploaded via visible input: {image_path}")
                time.sleep(5)  # Wait 5 seconds for preview to load
                take_screenshot(page, "image_uploaded")
                upload_success = True
            else:
                print("  File input not found after making visible")
                
        except Exception as e:
            print(f"  Method 1 failed: {e}")
            take_screenshot(page, "method1_error")
        
        # Method 2: Try dispatch_event approach
        if not upload_success:
            print("\n  Method 2: Trying dispatch_event approach...")
            try:
                page.evaluate(f"""
                    () => {{
                        const input = document.querySelector('input[type="file"]');
                        if (input) {{
                            // Create a mock file object
                            const dataTransfer = new DataTransfer();
                            // Note: We can't directly set file path from security reasons
                            // But we can trigger the input
                            input.click();
                        }}
                    }}
                """)
                time.sleep(3)
                
                # Now try set_input_files
                file_input = page.locator("input[type='file']").first
                file_input.set_input_files(str(image_path), timeout=60000)
                print(f"  [OK] Image uploaded via dispatch_event: {image_path}")
                time.sleep(5)
                take_screenshot(page, "image_uploaded_method2")
                upload_success = True
                
            except Exception as e:
                print(f"  Method 2 failed: {e}")
                take_screenshot(page, "method2_error")
        
        # Method 3: Use expect_file_chooser approach
        if not upload_success:
            print("\n  Method 3: Trying expect_file_chooser approach...")
            try:
                # Close any open dialog first
                page.keyboard.press('Escape')
                time.sleep(1)
                
                # Click create button again with file chooser expectation
                with page.expect_file_chooser(timeout=30000) as fc_info:
                    create_button.click()
                
                file_chooser = fc_info.value
                file_chooser.set_files(str(image_path))
                print(f"  [OK] Image uploaded via file_chooser: {image_path}")
                time.sleep(5)
                take_screenshot(page, "image_uploaded_method3")
                upload_success = True
                
            except Exception as e:
                print(f"  Method 3 failed: {e}")
                take_screenshot(page, "method3_error")
        
        # Method 4: Click "Select from computer" button if it appears
        if not upload_success:
            print("\n  Method 4: Looking for 'Select from computer' button...")
            try:
                select_buttons = [
                    'button:has-text("Select from computer")',
                    'div:has-text("Select from computer")',
                    'button:has-text("Select From Computer")',
                    'button:has-text("Select from your computer")',
                    'div[role="button"]:has-text("Select")'
                ]
                
                for selector in select_buttons:
                    try:
                        select_btn = page.locator(selector).first
                        if select_btn and select_btn.is_visible(timeout=5000):
                            print(f"  Found select button: {selector}")
                            select_btn.click()
                            time.sleep(2)
                            
                            # Now try file upload
                            with page.expect_file_chooser(timeout=30000) as fc_info:
                                pass
                            file_chooser = fc_info.value
                            file_chooser.set_files(str(image_path))
                            print(f"  [OK] Image uploaded via select button: {image_path}")
                            time.sleep(5)
                            take_screenshot(page, "image_uploaded_method4")
                            upload_success = True
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"  Method 4 failed: {e}")
                take_screenshot(page, "method4_error")
        
        # Check if upload was successful
        if not upload_success:
            print("\n[ERROR] All upload methods failed")
            log_action("post_error", "All file upload methods failed", success=False)
            take_screenshot(page, "upload_all_failed")
            return False
        
        print("\n[OK] Image upload successful!")

        # Click First Next button
        print("Clicking Next (1/2)...")
        next_button = None
        next_selectors = [
            'button:has-text("Next")',
            'div[role="button"]:has-text("Next")',
            'button:has-text("Next")',
            '[aria-label="Next"]'
        ]
        
        for selector in next_selectors:
            try:
                next_button = page.locator(selector).first
                if next_button and next_button.is_visible(timeout=10000):
                    print(f"  Found Next button with selector: {selector}")
                    next_button.click()
                    time.sleep(3)
                    break
            except Exception as e:
                print(f"  Next selector failed: {selector} - {e}")
                continue
        
        take_screenshot(page, "next_1_clicked")

        # Click Second Next button (for filters/edit screen)
        print("Clicking Next (2/2)...")
        time.sleep(3)
        
        for selector in next_selectors:
            try:
                next_button = page.locator(selector).first
                if next_button and next_button.is_visible(timeout=10000):
                    print(f"  Found Next button with selector: {selector}")
                    next_button.click()
                    time.sleep(3)
                    break
            except Exception as e:
                print(f"  Next selector failed: {selector} - {e}")
                continue
        
        take_screenshot(page, "next_2_clicked")

        # Add caption
        print("Adding caption...")
        caption_field = None
        caption_selectors = [
            'textarea[aria-label="Write a caption..."]',
            'div[role="textbox"]',
            'textarea[placeholder="Write a caption..."]',
            'textarea[aria-label*="caption"]',
            'textarea'
        ]
        
        for selector in caption_selectors:
            try:
                caption_field = page.locator(selector).first
                if caption_field and caption_field.is_visible(timeout=10000):
                    print(f"  Found caption field with selector: {selector}")
                    caption_field.fill(caption)
                    time.sleep(2)
                    break
            except Exception as e:
                print(f"  Caption selector failed: {selector} - {e}")
                continue
        
        take_screenshot(page, "caption_added")

        # Click Share button
        print("Clicking Share...")
        share_button = None
        share_selectors = [
            'button:has-text("Share")',
            'div[role="button"]:has-text("Share")',
            'button:has-text("Share")',
            '[aria-label="Share"]'
        ]
        
        for selector in share_selectors:
            try:
                share_button = page.locator(selector).first
                if share_button and share_button.is_visible(timeout=10000):
                    print(f"  Found Share button with selector: {selector}")
                    share_button.click()
                    time.sleep(3)
                    break
            except Exception as e:
                print(f"  Share selector failed: {selector} - {e}")
                continue
        
        take_screenshot(page, "share_clicked")

        # Wait for confirmation
        try:
            page.wait_for_selector('img[alt*="Posted"]', timeout=10000)
            print("[OK] Post created successfully!")
            log_action("post_created", f"Posted: {caption[:100]}...")
            take_screenshot(page, "post_success")
            return True
        except PlaywrightTimeout:
            # Check for other success indicators
            if "instagram.com" in page.url:
                print("[WARN] Confirmation timeout, but post may have succeeded")
                log_action("post_uncertain", "Posted but no confirmation")
                take_screenshot(page, "post_uncertain")
                return True
            else:
                print("[ERROR] Post may have failed")
                log_action("post_error", "Post confirmation failed", success=False)
                return False

    except Exception as e:
        print(f"[ERROR] Post failed: {e}")
        log_action("post_error", str(e), success=False)

        try:
            page = context.pages[0] if context.pages else None
            if page:
                take_screenshot(page, "post_error")
        except Exception:
            pass

        return False


def generate_post_content():
    """Generate professional Instagram caption from business data"""
    print("\n" + "=" * 60)
    print("GENERATE INSTAGRAM CONTENT")
    print("=" * 60)
    
    content_parts = []
    hashtags = []
    
    if COMPANY_HANDBOOK.exists():
        try:
            with open(COMPANY_HANDBOOK, "r", encoding="utf-8") as f:
                handbook = f.read()[:1000]
            
            name_match = re.search(r'#?\s*(\w+\s*Employee)', handbook)
            if name_match:
                content_parts.append(f"{name_match.group(1)} AI")
                hashtags.extend(["#AIEmployee", "#Automation"])
        except Exception:
            pass
    
    if DASHBOARD_FILE.exists():
        try:
            with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
                dashboard = f.read()
            
            tasks_match = re.search(r'Completed Tasks:\s*(\d+)', dashboard)
            if tasks_match:
                count = tasks_match.group(1)
                content_parts.append(f"Completed {count} tasks this week")
                hashtags.append("#Productivity")
        except Exception:
            pass
    
    if BUSINESS_GOALS.exists():
        try:
            with open(BUSINESS_GOALS, "r", encoding="utf-8") as f:
                goals = f.read()
            
            revenue_match = re.search(r'Monthly goal:.*?\$?([\d,]+)', goals)
            if revenue_match:
                goal = revenue_match.group(1)
                content_parts.append(f"Target: ${goal}")
                hashtags.append("#BusinessGoals")
        except Exception:
            pass
    
    # Read templates
    templates = []
    if INSTAGRAM_TEMPLATES.exists():
        try:
            with open(INSTAGRAM_TEMPLATES, "r", encoding="utf-8") as f:
                template_content = f.read()
            
            template_matches = re.findall(r'Template \d+:.*?(?=Template \d+:|$)', template_content, re.DOTALL)
            templates = [t.strip() for t in template_matches if t.strip()]
        except Exception:
            pass
    
    # Generate caption
    if content_parts:
        caption = " | ".join(content_parts)
        caption += "\n\n" + " ".join(hashtags[:10])
    elif templates:
        caption = random.choice(templates)
    else:
        caption = "Working on automation tasks. #AI #Productivity #BusinessAutomation #TechInnovation #DigitalTransformation"
    
    # Ensure under 2200 characters
    if len(caption) > 2200:
        caption = caption[:2197] + "..."
    
    print(f"Generated caption: {caption[:200]}...")
    print(f"Length: {len(caption)} characters")
    print(f"Hashtags: {len([h for h in caption.split() if h.startswith('#')])}")
    
    log_action("content_generated", f"Caption: {caption[:100]}...")
    
    return caption


def update_dashboard():
    """Update Dashboard.md with Instagram status"""
    try:
        if not DASHBOARD_FILE.exists():
            return False
        
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        if instagram_stats["last_post"]:
            last = datetime.strptime(instagram_stats["last_post"], "%Y-%m-%d %H:%M:%S")
            next_post = last.replace(hour=(last.hour + INSTAGRAM_POST_INTERVAL) % 24)
            next_str = next_post.strftime("%I:%M %p")
        else:
            next_str = "Pending"
        
        instagram_section = f"""## Instagram Status
- Last Post: {instagram_stats['last_post'] or 'Never'}
- Next Scheduled Post: {next_str}
- Total Posts This Week: {instagram_stats['total_this_week']}
- Auto-posting: {instagram_stats['auto_posting']}
"""
        
        if "## Instagram Status" in content:
            pattern = r"## Instagram Status.*?(?=## |\Z)"
            content = re.sub(pattern, instagram_section, content, flags=re.DOTALL)
        else:
            if "---" in content:
                parts = content.rsplit("---", 1)
                content = parts[0] + instagram_section + "\n---" + parts[1] if len(parts) > 1 else content + "\n" + instagram_section
            else:
                content = content + "\n" + instagram_section
        
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
    except Exception as e:
        log_action("dashboard_error", f"Failed to update dashboard: {e}", success=False)
        return False


def main():
    """Main function - generate content, create image, login, and post"""
    parser = argparse.ArgumentParser(description='Instagram Poster - Auto-post on Instagram')
    parser.add_argument('--test', action='store_true', help='Test mode - don\'t actually post')
    args = parser.parse_args()
    
    test_mode = args.test
    
    print("=" * 60)
    print("Instagram Poster - AI Employee System")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Test Mode: {test_mode}")
    print(f"Post Interval: {INSTAGRAM_POST_INTERVAL} hours")
    print("=" * 60)
    
    ensure_folders_exist()
    
    if not test_mode and (not INSTAGRAM_EMAIL or not INSTAGRAM_PASSWORD):
        print("\n[ERROR] Instagram credentials not set in .env file")
        print("Please add INSTAGRAM_EMAIL and INSTAGRAM_PASSWORD to .env")
        sys.exit(1)
    
    try:
        # Generate caption
        caption = generate_post_content()
        
        # Create text image
        print("\nCreating text image for post...")
        image_path = create_text_image(caption.split('\n')[0][:100])
        
        if not image_path:
            print("[ERROR] Failed to create image")
            sys.exit(1)
        
        print(f"\nInitializing browser...")
        playwright = sync_playwright().start()
        
        browser, context = initialize_browser(playwright)
        
        try:
            # Login to Instagram
            login_success = login_to_instagram(context, test_mode)
            
            if not login_success and not test_mode:
                print("\n[ERROR] Login failed - cannot post")
                sys.exit(1)
            
            # Create post
            if test_mode:
                print("\n[TEST MODE] Would post:")
                print(f"Image: {image_path}")
                print(f"Caption: {caption[:200]}...")
                success = True
            else:
                success = create_post(caption, image_path, context, test_mode)
            
            update_dashboard()
            
            if success:
                print("\n" + "=" * 60)
                print("POST CREATED SUCCESSFULLY")
                print("=" * 60)
                print(f"Image: {image_path}")
                print(f"Caption: {caption[:100]}...")
                print(f"Next scheduled: {INSTAGRAM_POST_INTERVAL} hours")
                print("=" * 60)
            else:
                print("\n[ERROR] Post creation failed")
                sys.exit(1)
            
        finally:
            try:
                browser.close()
                playwright.stop()
            except Exception:
                pass
        
        return success
        
    except Exception as e:
        print(f"\n[ERROR] Fatal error: {e}")
        log_action("fatal_error", str(e), success=False)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nInstagram Poster stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
