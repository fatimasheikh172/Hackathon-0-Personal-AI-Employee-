#!/usr/bin/env python3
"""
Twitter/X Manager - 2026 Updated Version
Auto-post tweets using Playwright automation with session persistence
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
SESSION_FOLDER = VAULT_PATH / "sessions" / "twitter_session"
SOCIAL_PENDING = VAULT_PATH / "Social_Content" / "pending"
SOCIAL_POSTED = VAULT_PATH / "Social_Content" / "posted"
SOCIAL_FAILED = VAULT_PATH / "Social_Content" / "failed"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
COMPANY_HANDBOOK = VAULT_PATH / "Company_Handbook.md"
BUSINESS_GOALS = VAULT_PATH / "Business_Goals.md"

# Environment settings
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
TWITTER_EMAIL = os.getenv("TWITTER_EMAIL", "")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD", "")
TWITTER_POST_INTERVAL = int(os.getenv("TWITTER_POST_INTERVAL", "12"))

# Rate limiting: 5 posts per hour
MAX_POSTS_PER_HOUR = 5
POSTS_WINDOW_MINUTES = 60

# Statistics
twitter_stats = {
    "last_tweet": None,
    "next_scheduled": None,
    "total_today": 0,
    "total_this_hour": 0,
    "last_post_time": None
}


def get_log_file_path():
    """Get log file path with current date"""
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"twitter_{date_str}.json"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, SESSION_FOLDER, SOCIAL_PENDING, SOCIAL_POSTED, SOCIAL_FAILED]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True, data=None):
    """Log a Twitter action to JSON log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if action_type == "tweet_posted":
        twitter_stats["last_tweet"] = timestamp
        twitter_stats["total_today"] += 1
        twitter_stats["last_post_time"] = datetime.now()

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
        log_data["summary"]["total_tweets"] = sum(
            1 for a in log_data["actions"] 
            if a["type"] == "tweet_posted" and a["success"]
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
        "platform": "Twitter/X",
        "actions": [],
        "summary": {
            "total_actions": 0,
            "total_tweets": 0,
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
    return SESSION_FOLDER / "twitter_session.json"


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
        screenshot_path = LOGS_FOLDER / f"twitter_{step_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(screenshot_path), full_page=False)
        return screenshot_path
    except Exception as e:
        print(f"[DEBUG] Screenshot failed: {e}")
        return None


def check_rate_limit():
    """Check if we're within rate limits (5 posts/hour)"""
    now = datetime.now()
    
    # Load recent posts from log
    log_data = load_json_log()
    recent_posts = []
    
    for action in log_data["actions"]:
        if action["type"] == "tweet_posted" and action["success"]:
            try:
                post_time = datetime.strptime(action["timestamp"], "%Y-%m-%d %H:%M:%S")
                if (now - post_time).total_seconds() < POSTS_WINDOW_MINUTES * 60:
                    recent_posts.append(post_time)
            except Exception:
                pass
    
    twitter_stats["total_this_hour"] = len(recent_posts)
    
    if len(recent_posts) >= MAX_POSTS_PER_HOUR:
        oldest_recent = min(recent_posts)
        wait_until = oldest_recent + timedelta(minutes=POSTS_WINDOW_MINUTES)
        log_action("rate_limit_hit", f"Wait until {wait_until.strftime('%H:%M:%S')}", success=False)
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


def login_to_twitter(context, test_mode=False):
    """
    Login to X/Twitter with retry logic and session persistence
    Returns True if login successful
    """
    print("\n" + "=" * 60)
    print("TWITTER/X LOGIN")
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

                page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
                time.sleep(3)

                take_screenshot(page, "session_check")

                # Check if logged in
                if (page.query_selector('[data-testid="SideNav_NewTweet_Button"]') or 
                    page.query_selector('[aria-label="Compose"]') or
                    page.query_selector('[data-testid="tweetButtonInline"]')):
                    print("[OK] Logged in with saved session!")
                    log_action("login_success", "Logged in with saved session")
                    return True
                else:
                    print("Session expired, logging in again...")
                    context.clear_cookies()

            # Fresh login
            print("Opening X.com login page...")
            page.goto("https://x.com/login", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

            take_screenshot(page, "login_page")

            if test_mode:
                print("[TEST MODE] Skipping actual login")
                log_action("login_test", "Test mode - login skipped")
                return True

            if not TWITTER_EMAIL or not TWITTER_PASSWORD:
                print("[ERROR] Twitter credentials not found in .env file")
                log_action("login_error", "Credentials missing", success=False)
                return False

            # Enter email/username - 2026 updated selectors
            print("Entering email...")
            email_field = None
            email_selectors = [
                'input[autocomplete="username"]',
                'input[name="text"]',
                'input[type="text"]',
                'input[aria-label="Phone, email, or username"]'
            ]
            
            for selector in email_selectors:
                email_field = page.query_selector(selector)
                if email_field:
                    print(f"  Found email field: {selector}")
                    break

            if email_field:
                email_field.fill(TWITTER_EMAIL)
                time.sleep(random.uniform(0.5, 1.5))

            # Click Next
            next_button = page.query_selector('div[role="button"]:has-text("Next")')
            if next_button:
                next_button.click()
                time.sleep(random.uniform(1, 2))

            # Enter password
            print("Entering password...")
            password_field = None
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[aria-label="Password"]'
            ]
            
            for selector in password_selectors:
                password_field = page.query_selector(selector)
                if password_field:
                    print(f"  Found password field: {selector}")
                    break

            if password_field:
                password_field.fill(TWITTER_PASSWORD)
                time.sleep(random.uniform(0.5, 1.5))

            # Click Login
            print("Clicking login...")
            login_button = page.query_selector('div[role="button"]:has-text("Log in")')
            if login_button:
                login_button.click()
                time.sleep(3)

            # Wait for home feed
            try:
                page.wait_for_selector('[data-testid="primaryColumn"]', timeout=60000)
                time.sleep(3)

                take_screenshot(page, "login_success")
                print("[OK] Twitter login successful!")
                log_action("login_success", "Fresh login completed")

                save_session_cookies(context)
                return True

            except PlaywrightTimeout:
                print("[WARN] Login timeout - may need verification")
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


def post_tweet(content, context, test_mode=False):
    """
    Create and post a tweet with 2026 updated selectors
    Returns True if successful
    """
    print("\n" + "=" * 60)
    print("POST TWEET")
    print("=" * 60)
    print(f"Content: {content}")
    print(f"Length: {len(content)} characters")
    print(f"DRY_RUN: {DRY_RUN or test_mode}")
    print("=" * 60)

    # Validate content
    if not content or not content.strip():
        log_action("tweet_error", "Empty content", success=False)
        return False

    if len(content) > 280:
        log_action("tweet_error", f"Content too long: {len(content)} > 280", success=False)
        return False

    # Check rate limit
    within_limit, wait_until = check_rate_limit()
    if not within_limit:
        print(f"[WARN] Rate limit hit. Wait until {wait_until.strftime('%H:%M:%S')}")
        return False

    if DRY_RUN or test_mode:
        print("[DRY_RUN] Skipping actual tweet posting")
        log_action("tweet_dry_run", f"Would post: {content[:100]}...")
        return True

    try:
        page = context.pages[0] if context.pages else context.new_page()

        if "x.com" not in page.url and "twitter.com" not in page.url:
            page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

        take_screenshot(page, "before_compose")

        # Click compose button - 2026 selectors
        print("Opening compose box...")
        compose_selectors = [
            'a[data-testid="SideNav_NewTweet_Button"]',
            'a[href="/compose/tweet"]',
            '[aria-label="Compose"]',
            '[data-testid="SideNav_NewTweet_Button"]'
        ]
        
        compose_button = None
        for selector in compose_selectors:
            compose_button = page.query_selector(selector)
            if compose_button:
                print(f"  Found compose button: {selector}")
                break

        if compose_button:
            compose_button.click()
            time.sleep(2)
        else:
            # Try clicking tweet box directly
            tweet_box = page.query_selector('[data-testid="tweetTextarea_0"]')
            if tweet_box:
                tweet_box.click()
                time.sleep(1)

        take_screenshot(page, "compose_opened")

        # Type tweet content
        print("Typing tweet...")
        tweet_box = None
        tweet_selectors = [
            'div[data-testid="tweetTextarea_0"]',
            'div[role="textbox"]',
            'div.public-DraftEditor-content',
            '[data-testid="tweetTextarea_0"] textarea'
        ]
        
        for selector in tweet_selectors:
            tweet_box = page.query_selector(selector)
            if tweet_box:
                print(f"  Found tweet box: {selector}")
                break

        if tweet_box:
            # Clear and type
            tweet_box.click()
            time.sleep(0.5)
            
            # Use keyboard type for realism
            for char in content:
                tweet_box.type(char, delay=random.uniform(10, 50))
                time.sleep(random.uniform(0.01, 0.05))

            time.sleep(2)
            take_screenshot(page, "tweet_typed")

            # Click Post button - 2026 selectors
            print("Posting tweet...")
            post_selectors = [
                'div[data-testid="tweetButtonInline"]',
                'button[data-testid="tweetButton"]',
                'div[role="button"]:has-text("Post")',
                '[data-testid="tweetButton"]'
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
                    page.wait_for_selector('[data-testid="tweetTextarea_0"]', timeout=10000, state="detached")
                    print("[OK] Tweet posted successfully!")
                    log_action("tweet_posted", f"Posted: {content[:100]}...")
                    take_screenshot(page, "tweet_posted")
                    return True
                except PlaywrightTimeout:
                    print("[WARN] Confirmation timeout, but tweet may have posted")
                    log_action("tweet_uncertain", "Posted but no confirmation")
                    take_screenshot(page, "tweet_uncertain")
                    return True
            else:
                print("[ERROR] Post button not found")
                log_action("tweet_error", "Post button not found", success=False)
                take_screenshot(page, "post_button_error")
                return False
        else:
            print("[ERROR] Tweet box not found")
            log_action("tweet_error", "Tweet box not found", success=False)
            take_screenshot(page, "tweet_box_error")
            return False

    except Exception as e:
        print(f"[ERROR] Tweet failed: {e}")
        log_action("tweet_error", str(e), success=False)
        return False


def get_mentions(context, max_mentions=10):
    """
    Get recent mentions/notifications
    Returns list of mention data
    """
    print("\n" + "=" * 60)
    print("GET MENTIONS")
    print("=" * 60)

    mentions = []

    try:
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("https://x.com/notifications", wait_until="domcontentloaded", timeout=60000)
        time.sleep(3)

        # Look for mention notifications - 2026 selectors
        mention_selectors = [
            '[data-testid="notification"]',
            'article[role="article"]',
            '[data-testid="cellInnerDiv"]'
        ]
        
        elements = []
        for selector in mention_selectors:
            elements = page.query_selector_all(selector)
            if elements:
                break

        for elem in elements[:max_mentions]:
            try:
                text = elem.inner_text()
                if "@" in text or "mentioned" in text.lower():
                    mentions.append({
                        "text": text[:280],
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception:
                pass

        log_action("mentions_fetched", f"Found {len(mentions)} mentions")
        return mentions

    except Exception as e:
        log_action("mentions_error", str(e), success=False)
        return []


def generate_business_post(topic, context=None):
    """
    Generate a professional business tweet from a topic
    Returns tweet content (max 280 chars)
    """
    print("\n" + "=" * 60)
    print("GENERATE BUSINESS TWEET")
    print("=" * 60)
    print(f"Topic: {topic}")

    # Read company context
    context_parts = []
    
    if COMPANY_HANDBOOK.exists():
        try:
            with open(COMPANY_HANDBOOK, "r", encoding="utf-8") as f:
                content = f.read()
            name_match = re.search(r'#?\s*(\w+\s*Employee)', content)
            if name_match:
                context_parts.append(name_match.group(1))
        except Exception:
            pass

    if BUSINESS_GOALS.exists():
        try:
            with open(BUSINESS_GOALS, "r", encoding="utf-8") as f:
                content = f.read()
            # Extract key goals
            goal_match = re.search(r'Monthly goal:.*?\$?([\d,]+)', content)
            if goal_match:
                context_parts.append(f"Target: ${goal_match.group(1)}")
        except Exception:
            pass

    # Generate tweet based on topic
    topic = topic.strip()[:200]
    
    templates = [
        f"🚀 {topic}\n\nDriving innovation and excellence in every task. #BusinessGrowth #AI #Automation",
        f"💼 Update: {topic}\n\nCommitted to delivering value through smart automation. #Productivity #Innovation",
        f"📈 {topic}\n\nBuilding the future of work, one task at a time. #FutureOfWork #AI #Business",
        f"✨ {topic}\n\nExcellence is our standard. #ProfessionalExcellence #Automation #Success",
    ]

    tweet = random.choice(templates)
    
    # Ensure under 280 chars
    if len(tweet) > 280:
        tweet = tweet[:277] + "..."

    print(f"Generated: {tweet}")
    print(f"Length: {len(tweet)} chars")

    log_action("content_generated", f"Tweet: {tweet[:100]}...")
    return tweet


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Twitter/X Manager')
    parser.add_argument('--test', action='store_true', help='Test mode')
    parser.add_argument('--content', type=str, help='Tweet content')
    parser.add_argument('--topic', type=str, help='Topic for auto-generation')
    parser.add_argument('--mentions', action='store_true', help='Get mentions')
    args = parser.parse_args()

    print("=" * 60)
    print("Twitter/X Manager - AI Employee System (2026)")
    print("=" * 60)
    print(f"Vault: {VAULT_PATH}")
    print(f"DRY_RUN: {DRY_RUN or args.test}")
    print("=" * 60)

    ensure_folders_exist()

    if not args.test and (not TWITTER_EMAIL or not TWITTER_PASSWORD):
        print("\n[ERROR] Twitter credentials not set in .env")
        sys.exit(1)

    try:
        playwright = sync_playwright().start()
        browser, context = initialize_browser(playwright)

        try:
            # Login
            login_success = login_to_twitter(context, args.test)
            
            if not login_success and not args.test:
                print("\n[ERROR] Login failed")
                sys.exit(1)

            # Get mentions
            if args.mentions:
                mentions = get_mentions(context)
                print(f"\nRecent mentions: {len(mentions)}")
                for m in mentions[:5]:
                    print(f"  - {m['text'][:80]}...")

            # Post tweet
            if args.content:
                success = post_tweet(args.content, context, args.test)
            elif args.topic:
                content = generate_business_post(args.topic, context)
                success = post_tweet(content, context, args.test)
            else:
                # Generate and post from topic
                content = generate_business_post("Business automation update", context)
                success = post_tweet(content, context, args.test)

            if success:
                print("\n" + "=" * 60)
                print("TWITTER OPERATION SUCCESSFUL")
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
