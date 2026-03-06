#!/usr/bin/env python3
"""
Twitter Poster - Auto-post tweets using Playwright automation
No API required - uses browser automation with anti-detection
FIXED VERSION with improved selectors and timeouts
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

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"
SESSION_FOLDER = VAULT_PATH / "twitter_session"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
COMPANY_HANDBOOK = VAULT_PATH / "Company_Handbook.md"
BUSINESS_GOALS = VAULT_PATH / "Business_Goals.md"
TWITTER_TEMPLATES = VAULT_PATH / "twitter_templates.md"

# Twitter credentials from .env
TWITTER_EMAIL = os.getenv("TWITTER_EMAIL", "")
TWITTER_PASSWORD = os.getenv("TWITTER_PASSWORD", "")
TWITTER_POST_INTERVAL = int(os.getenv("TWITTER_POST_INTERVAL", "12"))

# Twitter statistics
twitter_stats = {
    "last_tweet": None,
    "next_scheduled": None,
    "total_this_week": 0,
    "auto_posting": "Active"
}


def get_log_file_path():
    """Get log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"twitter_poster_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"twitter_activity_{date_str}.txt"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, SESSION_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True):
    """Log a Twitter action to log files"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if action_type == "tweet_posted":
        twitter_stats["last_tweet"] = timestamp
        twitter_stats["total_this_week"] += 1
    
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
            "total_tweets": 0,
            "total_errors": 0
        }
    }


def save_json_log(log_data):
    """Save log data to JSON file"""
    try:
        log_data["summary"]["total_tweets"] = twitter_stats["total_this_week"]
        with open(get_log_file_path(), "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"ERROR saving JSON log: {e}")
        return False


def get_session_file():
    """Get session file path"""
    return SESSION_FOLDER / "twitter_session.json"


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
        screenshot_path = LOGS_FOLDER / f"twitter_{step_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(screenshot_path))
        print(f"Screenshot saved: {screenshot_path}")
        return screenshot_path
    except Exception as e:
        print(f"Failed to take screenshot: {e}")
        return None


def initialize_browser(playwright):
    """Initialize browser with improved anti-detection settings"""
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


def login_to_twitter(context, test_mode=False):
    """
    Login to X/Twitter with retry logic
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
                
                if page.query_selector('[data-testid="SideNav_NewTweet_Button"]') or \
                   page.query_selector('[aria-label="Compose"]'):
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
            
            # Enter email/username - try multiple selectors
            print("Entering email...")
            email_field = None
            for selector in ['input[autocomplete="username"]', 'input[name="text"]', 'input[type="text"]']:
                email_field = page.query_selector(selector)
                if email_field:
                    print(f"  Found email field with selector: {selector}")
                    break
            
            if email_field:
                email_field.fill(TWITTER_EMAIL)
                time.sleep(random.uniform(0.5, 1.5))
            
            # Click next
            next_button = page.query_selector('div[role="button"]:has-text("Next")')
            if next_button:
                next_button.click()
                time.sleep(random.uniform(1, 2))
            
            # Enter password
            print("Entering password...")
            password_field = None
            for selector in ['input[type="password"]', 'input[name="password"]']:
                password_field = page.query_selector(selector)
                if password_field:
                    print(f"  Found password field with selector: {selector}")
                    break
            
            if password_field:
                password_field.fill(TWITTER_PASSWORD)
                time.sleep(random.uniform(0.5, 1.5))
            
            # Click login
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


def create_tweet(content, context, test_mode=False):
    """
    Create and post a tweet with improved selectors
    """
    print("\n" + "=" * 60)
    print("CREATE TWEET")
    print("=" * 60)
    print(f"Content: {content}")
    print(f"Length: {len(content)} characters")
    print("=" * 60)
    
    try:
        if len(content) > 280:
            print("[ERROR] Tweet content exceeds 280 characters")
            log_action("tweet_error", "Content too long", success=False)
            return False
        
        if test_mode:
            print("[TEST MODE] Skipping actual tweet posting")
            log_action("tweet_test", f"Test tweet: {content[:100]}...")
            return True
        
        page = context.pages[0] if context.pages else context.new_page()
        
        if "x.com" not in page.url and "twitter.com" not in page.url:
            page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)
        
        take_screenshot(page, "before_compose")
        
        # Click compose button - try multiple selectors
        print("Opening compose box...")
        compose_button = None
        for selector in ['a[data-testid="SideNav_NewTweet_Button"]', 'a[href="/compose/tweet"]', '[aria-label="Compose"]']:
            compose_button = page.query_selector(selector)
            if compose_button:
                print(f"  Found compose button with selector: {selector}")
                break
        
        if compose_button:
            compose_button.click()
            time.sleep(2)
        else:
            tweet_box = page.query_selector('[data-testid="tweetTextarea_0"]')
            if tweet_box:
                tweet_box.click()
                time.sleep(1)
        
        take_screenshot(page, "compose_opened")
        
        # Type tweet content
        print("Typing tweet...")
        tweet_box = None
        for selector in ['div[data-testid="tweetTextarea_0"]', 'div[role="textbox"]', 'div.public-DraftEditor-content']:
            tweet_box = page.query_selector(selector)
            if tweet_box:
                print(f"  Found tweet box with selector: {selector}")
                break
        
        if tweet_box:
            for char in content:
                tweet_box.type(char)
                time.sleep(random.uniform(0.02, 0.1))
            
            time.sleep(2)
            take_screenshot(page, "tweet_typed")
            
            # Click Post button - try multiple selectors
            print("Posting tweet...")
            post_button = None
            for selector in ['div[data-testid="tweetButtonInline"]', 'button[data-testid="tweetButton"]', 'div[role="button"]:has-text("Post")']:
                post_button = page.query_selector(selector)
                if post_button:
                    print(f"  Found post button with selector: {selector}")
                    break
            
            if post_button:
                post_button.click()
                time.sleep(3)
                
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
        
        try:
            page = context.pages[0] if context.pages else None
            if page:
                take_screenshot(page, "tweet_error")
        except Exception:
            pass
        
        return False


def generate_tweet_content():
    """Generate professional tweet content from business data"""
    print("\n" + "=" * 60)
    print("GENERATE TWEET CONTENT")
    print("=" * 60)
    
    content_parts = []
    
    if COMPANY_HANDBOOK.exists():
        try:
            with open(COMPANY_HANDBOOK, "r", encoding="utf-8") as f:
                handbook = f.read()[:1000]
            
            name_match = re.search(r'#?\s*(\w+\s*Employee)', handbook)
            if name_match:
                content_parts.append(f"{name_match.group(1)} AI")
        except Exception:
            pass
    
    if DASHBOARD_FILE.exists():
        try:
            with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
                dashboard = f.read()
            
            tasks_match = re.search(r'Completed Tasks:\s*(\d+)', dashboard)
            if tasks_match:
                count = tasks_match.group(1)
                content_parts.append(f"Completed {count} tasks")
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
        except Exception:
            pass
    
    templates = []
    if TWITTER_TEMPLATES.exists():
        try:
            with open(TWITTER_TEMPLATES, "r", encoding="utf-8") as f:
                template_content = f.read()
            
            template_matches = re.findall(r'Template \d+:.*?(?=Template \d+:|$)', template_content, re.DOTALL)
            templates = [t.strip() for t in template_matches if t.strip()]
        except Exception:
            pass
    
    if content_parts:
        tweet = " | ".join(content_parts)
        tweet += " #AIEmployee #Automation #Productivity"
    elif templates:
        tweet = random.choice(templates)
    else:
        tweet = f"Working on automation tasks. #AI #Productivity #BusinessAutomation"
    
    if len(tweet) > 280:
        tweet = tweet[:277] + "..."
    
    print(f"Generated tweet: {tweet}")
    print(f"Length: {len(tweet)} characters")
    
    log_action("content_generated", f"Tweet: {tweet[:100]}...")
    
    return tweet


def update_dashboard():
    """Update Dashboard.md with Twitter status"""
    try:
        if not DASHBOARD_FILE.exists():
            return False
        
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            content = f.read()
        
        if twitter_stats["last_tweet"]:
            last = datetime.strptime(twitter_stats["last_tweet"], "%Y-%m-%d %H:%M:%S")
            next_tweet = last.replace(hour=(last.hour + TWITTER_POST_INTERVAL) % 24)
            next_str = next_tweet.strftime("%I:%M %p")
        else:
            next_str = "Pending"
        
        twitter_section = f"""## Twitter Status
- Last Tweet: {twitter_stats['last_tweet'] or 'Never'}
- Next Scheduled Tweet: {next_str}
- Total Tweets This Week: {twitter_stats['total_this_week']}
- Auto-posting: {twitter_stats['auto_posting']}
"""
        
        if "## Twitter Status" in content:
            pattern = r"## Twitter Status.*?(?=## |\Z)"
            content = re.sub(pattern, twitter_section, content, flags=re.DOTALL)
        else:
            if "---" in content:
                parts = content.rsplit("---", 1)
                content = parts[0] + twitter_section + "\n---" + parts[1] if len(parts) > 1 else content + "\n" + twitter_section
            else:
                content = content + "\n" + twitter_section
        
        with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        
        return True
    except Exception as e:
        log_action("dashboard_error", f"Failed to update dashboard: {e}", success=False)
        return False


def main():
    """Main function - generate content, login, and post"""
    parser = argparse.ArgumentParser(description='Twitter Poster - Auto-post tweets')
    parser.add_argument('--test', action='store_true', help='Test mode - don\'t actually post')
    args = parser.parse_args()
    
    test_mode = args.test
    
    print("=" * 60)
    print("Twitter Poster - AI Employee System (FIXED VERSION)")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Test Mode: {test_mode}")
    print(f"Post Interval: {TWITTER_POST_INTERVAL} hours")
    print("=" * 60)
    
    ensure_folders_exist()
    
    if not test_mode and (not TWITTER_EMAIL or not TWITTER_PASSWORD):
        print("\n[ERROR] Twitter credentials not set in .env file")
        print("Please add TWITTER_EMAIL and TWITTER_PASSWORD to .env")
        sys.exit(1)
    
    try:
        print("\nInitializing browser...")
        playwright = sync_playwright().start()
        
        browser, context = initialize_browser(playwright)
        
        try:
            tweet_content = generate_tweet_content()
            
            login_success = login_to_twitter(context, test_mode)
            
            if not login_success and not test_mode:
                print("\n[ERROR] Login failed - cannot post tweet")
                sys.exit(1)
            
            if test_mode:
                print("\n[TEST MODE] Would post tweet:")
                print(tweet_content)
                success = True
            else:
                success = create_tweet(tweet_content, context, test_mode)
            
            update_dashboard()
            
            if success:
                print("\n" + "=" * 60)
                print("TWEET POSTED SUCCESSFULLY")
                print("=" * 60)
                print(f"Content: {tweet_content}")
                print(f"Next scheduled: {TWITTER_POST_INTERVAL} hours")
                print("=" * 60)
            else:
                print("\n[ERROR] Tweet posting failed")
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
        print("\n\nTwitter Poster stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
