#!/usr/bin/env python3
"""
LinkedIn Manager - 2026 Updated Version
Auto-post professional content using Playwright automation with session persistence
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

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"
SESSION_FOLDER = VAULT_PATH / "sessions" / "linkedin_session"
SOCIAL_PENDING = VAULT_PATH / "Social_Content" / "pending"
SOCIAL_POSTED = VAULT_PATH / "Social_Content" / "posted"
SOCIAL_FAILED = VAULT_PATH / "Social_Content" / "failed"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
COMPANY_HANDBOOK = VAULT_PATH / "Company_Handbook.md"
BUSINESS_GOALS = VAULT_PATH / "Business_Goals.md"

# Environment settings
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
LINKEDIN_POST_INTERVAL = int(os.getenv("LINKEDIN_POST_INTERVAL", "24"))

# Rate limiting: 3 posts per day (LinkedIn strict limits)
MAX_POSTS_PER_DAY = 3
MIN_POST_INTERVAL_HOURS = 4

# Statistics
linkedin_stats = {
    "last_post": None,
    "next_scheduled": None,
    "total_today": 0,
    "last_post_time": None
}


def get_log_file_path():
    """Get log file path with current date"""
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"linkedin_{date_str}.json"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, SESSION_FOLDER, SOCIAL_PENDING, SOCIAL_POSTED, SOCIAL_FAILED]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True, data=None):
    """Log a LinkedIn action to JSON log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if action_type == "post_created":
        linkedin_stats["last_post"] = timestamp
        linkedin_stats["total_today"] += 1
        linkedin_stats["last_post_time"] = datetime.now()

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
        "platform": "LinkedIn",
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
    return SESSION_FOLDER / "linkedin_session.json"


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
        screenshot_path = LOGS_FOLDER / f"linkedin_{step_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(screenshot_path), full_page=False)
        return screenshot_path
    except Exception as e:
        print(f"[DEBUG] Screenshot failed: {e}")
        return None


def check_rate_limit():
    """Check if we're within rate limits (3 posts/day, min 4 hours between posts)"""
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
    
    linkedin_stats["total_today"] = len(today_posts)
    
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


def enforce_professional_tone(content):
    """
    Ensure content has professional tone for LinkedIn
    Returns cleaned content
    """
    # Remove excessive emojis (keep 1-2 professional ones)
    emoji_pattern = re.compile(r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]{3,}")
    content = emoji_pattern.sub('', content)
    
    # Keep only 1-2 professional emojis
    professional_emojis = ['🚀', '💼', '📈', '✨', '💡', '🎯', '📊', '🏆']
    emoji_count = 0
    result = []
    for char in content:
        if any(char in emoji for emoji in professional_emojis):
            if emoji_count < 2:
                result.append(char)
                emoji_count += 1
        else:
            result.append(char)
    
    content = ''.join(result)
    
    # Ensure proper formatting
    content = re.sub(r'\n{3,}', '\n\n', content)  # Max 2 line breaks
    content = content.strip()
    
    return content


def login_to_linkedin(context, test_mode=False):
    """
    Login to LinkedIn with retry logic and session persistence
    Returns True if login successful
    """
    print("\n" + "=" * 60)
    print("LINKEDIN LOGIN")
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

                page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
                time.sleep(3)

                take_screenshot(page, "session_check")

                # Check if logged in
                if (page.query_selector('div.share-box-feed-entry') or 
                    page.query_selector('[aria-label="Start a post"]') or
                    page.query_selector('div.feed-shared-update-v2')):
                    print("[OK] Logged in with saved session!")
                    log_action("login_success", "Logged in with saved session")
                    return True
                else:
                    print("Session expired, logging in again...")
                    context.clear_cookies()

            # Fresh login
            print("Opening LinkedIn login page...")
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

            take_screenshot(page, "login_page")

            if test_mode:
                print("[TEST MODE] Skipping actual login")
                log_action("login_test", "Test mode - login skipped")
                return True

            if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
                print("[ERROR] LinkedIn credentials not found in .env file")
                log_action("login_error", "Credentials missing", success=False)
                return False

            # Enter email - 2026 updated selectors
            print("Entering email...")
            email_field = None
            email_selectors = [
                'input#username',
                'input[name="session_key"]',
                'input[autocomplete="username"]',
                'input[type="email"]',
                'input[aria-label="Email or phone"]'
            ]
            
            for selector in email_selectors:
                email_field = page.query_selector(selector)
                if email_field:
                    print(f"  Found email field: {selector}")
                    break

            if email_field:
                email_field.fill(LINKEDIN_EMAIL)
                time.sleep(random.uniform(0.5, 1.5))

            # Enter password
            print("Entering password...")
            password_field = None
            password_selectors = [
                'input#password',
                'input[name="session_password"]',
                'input[autocomplete="current-password"]',
                'input[type="password"]'
            ]
            
            for selector in password_selectors:
                password_field = page.query_selector(selector)
                if password_field:
                    print(f"  Found password field: {selector}")
                    break

            if password_field:
                password_field.fill(LINKEDIN_PASSWORD)
                time.sleep(random.uniform(0.5, 1.5))

            # Click Sign In
            print("Clicking Sign In...")
            signin_selectors = [
                'button[type="submit"]',
                'button.sign-in-form__submit-button',
                'button[aria-label="Sign in"]'
            ]
            
            signin_button = None
            for selector in signin_selectors:
                signin_button = page.query_selector(selector)
                if signin_button:
                    print(f"  Found sign in button: {selector}")
                    break

            if signin_button:
                signin_button.click()
                time.sleep(3)

            # Wait for feed
            try:
                page.wait_for_selector('div.share-box-feed-entry', timeout=60000)
                time.sleep(3)

                take_screenshot(page, "login_success")
                print("[OK] LinkedIn login successful!")
                log_action("login_success", "Fresh login completed")

                save_session_cookies(context)
                return True

            except PlaywrightTimeout:
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


def create_post(content, context, test_mode=False):
    """
    Create and post on LinkedIn with 2026 updated selectors
    Returns True if successful
    """
    print("\n" + "=" * 60)
    print("CREATE LINKEDIN POST")
    print("=" * 60)
    print(f"Content: {content[:200]}...")
    print(f"Length: {len(content)} characters")
    print(f"DRY_RUN: {DRY_RUN or test_mode}")
    print("=" * 60)

    # Validate content
    if not content or not content.strip():
        log_action("post_error", "Empty content", success=False)
        return False

    # Enforce professional tone
    content = enforce_professional_tone(content)
    
    # LinkedIn optimal length: 150-300 words
    word_count = len(content.split())
    if word_count < 50:
        print(f"[WARN] Content is short ({word_count} words). LinkedIn prefers 150-300 words.")
    if word_count > 500:
        print(f"[WARN] Content is long ({word_count} words). Consider shortening.")

    # Check rate limit
    within_limit, reason = check_rate_limit()
    if not within_limit:
        print(f"[WARN] Rate limit: {reason}")
        return False

    if DRY_RUN or test_mode:
        print("[DRY_RUN] Skipping actual post")
        log_action("post_dry_run", f"Would post: {content[:100]}...")
        return True

    try:
        page = context.pages[0] if context.pages else context.new_page()

        if "linkedin.com" not in page.url:
            page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

        take_screenshot(page, "before_compose")

        # Click "Start a post" - 2026 selectors
        print("Opening compose box...")
        compose_selectors = [
            'div[data-placeholder="Start a post"]',
            'button.share-box-feed-entry__trigger',
            '[aria-label="Start a post"]',
            'div.share-box-feed-entry__top-bar',
            'button:has-text("Start a post")'
        ]
        
        compose_button = None
        for selector in compose_selectors:
            compose_button = page.query_selector(selector)
            if compose_button:
                print(f"  Found compose button: {selector}")
                break

        if compose_button:
            compose_button.click()
            time.sleep(3)
        else:
            print("[ERROR] Compose button not found")
            log_action("post_error", "Compose button not found", success=False)
            take_screenshot(page, "compose_error")
            return False

        take_screenshot(page, "compose_opened")

        # Enter content - 2026 selectors
        print("Entering post content...")
        editor_selectors = [
            'div.ql-editor',
            'div[role="textbox"]',
            'div[contenteditable="true"]',
            'div.share-creation-state__text-editor div[contenteditable="true"]',
            '.editor-composer__content',
            'div[aria-label="What do you want to talk about?"]'
        ]
        
        editor = None
        for selector in editor_selectors:
            editor = page.query_selector(selector)
            if editor:
                print(f"  Found editor: {selector}")
                break

        if editor:
            editor.click()
            time.sleep(0.5)
            
            # Clear existing content
            page.keyboard.press('Control+A')
            time.sleep(0.3)
            page.keyboard.press('Delete')
            time.sleep(0.3)
            
            # Type content
            for char in content:
                editor.type(char, delay=random.uniform(10, 50))
                time.sleep(random.uniform(0.01, 0.03))

            time.sleep(2)
            take_screenshot(page, "content_entered")

            # Click Post button - 2026 selectors
            print("Posting...")
            post_selectors = [
                'button.share-actions__primary-action',
                'button[aria-label="Post"]',
                'div.share-actions button.artdeco-button--primary',
                'button:has-text("Post")'
            ]
            
            post_button = None
            for selector in post_selectors:
                post_button = page.query_selector(selector)
                if post_button:
                    print(f"  Found post button: {selector}")
                    break

            if post_button:
                post_button.click()
                time.sleep(3)

                # Wait for confirmation
                try:
                    page.wait_for_selector('button:has-text("Post")', timeout=10000, state="detached")
                    print("[OK] Post created successfully!")
                    log_action("post_created", f"Posted: {content[:100]}...")
                    take_screenshot(page, "post_success")
                    return True
                except PlaywrightTimeout:
                    print("[WARN] Confirmation timeout, but post may have been created")
                    log_action("post_uncertain", "Posted but no confirmation")
                    take_screenshot(page, "post_uncertain")
                    return True
            else:
                print("[ERROR] Post button not found")
                log_action("post_error", "Post button not found", success=False)
                take_screenshot(page, "post_button_error")
                return False
        else:
            print("[ERROR] Editor not found")
            log_action("post_error", "Editor not found", success=False)
            take_screenshot(page, "editor_error")
            return False

    except Exception as e:
        print(f"[ERROR] Post failed: {e}")
        log_action("post_error", str(e), success=False)
        return False


def get_feed_summary(context, max_posts=5):
    """
    Get summary of recent feed posts
    Returns list of post summaries
    """
    print("\n" + "=" * 60)
    print("GET FEED SUMMARY")
    print("=" * 60)

    posts = []

    try:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # Look for posts - 2026 selectors
        post_selectors = [
            'div.feed-shared-update-v2',
            'div.update-components-text',
            'div.share-body'
        ]
        
        elements = []
        for selector in post_selectors:
            elements = page.query_selector_all(selector)
            if elements:
                break

        for elem in elements[:max_posts]:
            try:
                text = elem.inner_text()[:500]
                posts.append({
                    "text": text,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception:
                pass

        log_action("feed_fetched", f"Found {len(posts)} posts")
        return posts

    except Exception as e:
        log_action("feed_error", str(e), success=False)
        return []


def generate_business_update(topic, context=None):
    """
    Generate a professional LinkedIn post from a topic
    Returns post content (150-300 words, professional tone)
    """
    print("\n" + "=" * 60)
    print("GENERATE BUSINESS UPDATE")
    print("=" * 60)
    print(f"Topic: {topic}")

    # Read company context
    company_name = "Our Company"
    achievements = []
    
    if COMPANY_HANDBOOK.exists():
        try:
            with open(COMPANY_HANDBOOK, "r", encoding="utf-8") as f:
                content = f.read()
            name_match = re.search(r'#?\s*(\w+\s*Employee)', content)
            if name_match:
                company_name = name_match.group(1)
        except Exception:
            pass

    if DASHBOARD_FILE.exists():
        try:
            with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            # Extract achievements
            tasks_match = re.search(r'Completed Tasks:\s*(\d+)', content)
            if tasks_match:
                achievements.append(f"completed {tasks_match.group(1)} tasks")
        except Exception:
            pass

    # Generate professional post
    topic = topic.strip()
    
    templates = [
        f"""🚀 Business Update

We're excited to share progress on {topic}. Our team at {company_name} continues to drive innovation through dedicated effort and strategic focus.

{f"Key achievements include: {', '.join(achievements)}." if achievements else "We remain committed to excellence in all our endeavors."}

Looking ahead, we're focused on delivering even greater value to our stakeholders and partners.

#BusinessGrowth #ProfessionalExcellence #Innovation #Leadership""",

        f"""💼 Professional Insight

Success in today's business landscape requires adaptability, innovation, and unwavering commitment to quality.

Our recent work on {topic} exemplifies these principles. We're proud of what we've accomplished and excited about the opportunities ahead.

Thank you to our team and partners for their continued support.

#ProfessionalDevelopment #BusinessSuccess #TeamWork #Growth""",

        f"""📈 Company Milestone

We're pleased to announce progress on {topic}. This achievement reflects our team's dedication and collaborative spirit.

{f"Recent highlights: {', '.join(achievements)}." if achievements else ""}

We look forward to continuing this momentum and creating lasting value.

#CompanyNews #Achievement #BusinessStrategy #Excellence""",
    ]

    post = random.choice(templates)
    
    # Clean up extra newlines
    post = re.sub(r'\n{3,}', '\n\n', post)
    
    word_count = len(post.split())
    print(f"Generated post: {word_count} words")

    log_action("content_generated", f"Post: {post[:100]}...")
    return post


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='LinkedIn Manager')
    parser.add_argument('--test', action='store_true', help='Test mode')
    parser.add_argument('--content', type=str, help='Post content')
    parser.add_argument('--topic', type=str, help='Topic for auto-generation')
    parser.add_argument('--feed', action='store_true', help='Get feed summary')
    args = parser.parse_args()

    print("=" * 60)
    print("LinkedIn Manager - AI Employee System (2026)")
    print("=" * 60)
    print(f"Vault: {VAULT_PATH}")
    print(f"DRY_RUN: {DRY_RUN or args.test}")
    print("=" * 60)

    ensure_folders_exist()

    if not args.test and (not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD):
        print("\n[ERROR] LinkedIn credentials not set in .env")
        sys.exit(1)

    try:
        playwright = sync_playwright().start()
        browser, context = initialize_browser(playwright)

        try:
            # Login
            login_success = login_to_linkedin(context, args.test)
            
            if not login_success and not args.test:
                print("\n[ERROR] Login failed")
                sys.exit(1)

            # Get feed
            if args.feed:
                posts = get_feed_summary(context)
                print(f"\nRecent posts: {len(posts)}")
                for p in posts[:3]:
                    print(f"  - {p['text'][:100]}...")

            # Create post
            if args.content:
                success = create_post(args.content, context, args.test)
            elif args.topic:
                content = generate_business_update(args.topic, context)
                success = create_post(content, context, args.test)
            else:
                content = generate_business_update("Business automation and productivity", context)
                success = create_post(content, context, args.test)

            if success:
                print("\n" + "=" * 60)
                print("LINKEDIN OPERATION SUCCESSFUL")
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
