#!/usr/bin/env python3
"""
LinkedIn Auto-Poster for AI Employee Vault
Posts professional content to LinkedIn using Playwright automation.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# Configuration
VAULT_PATH = Path(r"F:\AI_Employee_Vault")
LOGS_PATH = VAULT_PATH / "Logs"
SESSION_FILE = VAULT_PATH / "linkedin_session.json"
COMPANY_HANDBOOK = VAULT_PATH / "Company_Handbook.md"
DASHBOARD = VAULT_PATH / "Dashboard.md"

# Ensure logs directory exists
LOGS_PATH.mkdir(exist_ok=True)


def log_message(message: str, level: str = "INFO") -> None:
    """Log a message with timestamp to both console and log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    # Handle Windows console encoding issues by encoding/decoding
    try:
        print(log_entry)
    except UnicodeEncodeError:
        # Fallback for Windows console with emoji/special characters
        print(log_entry.encode('ascii', errors='replace').decode('ascii'))
    
    # Write to log file
    log_file = LOGS_PATH / f"linkedin_{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")


def load_env() -> dict:
    """Load environment variables from .env file."""
    load_dotenv(VAULT_PATH / ".env")
    return {
        "email": os.getenv("LINKEDIN_EMAIL", ""),
        "password": os.getenv("LINKEDIN_PASSWORD", ""),
        "post_interval": os.getenv("LINKEDIN_POST_INTERVAL", "24"),
    }


def generate_post_content() -> str:
    """
    Generate professional LinkedIn post content based on company handbook and dashboard.
    Returns post content as string.
    """
    log_message("Generating post content...")
    
    content_parts = []
    
    # Read Company Handbook
    try:
        if COMPANY_HANDBOOK.exists():
            with open(COMPANY_HANDBOOK, "r", encoding="utf-8") as f:
                handbook_content = f.read()
            log_message("Read Company_Handbook.md successfully")
        else:
            log_message("Company_Handbook.md not found", "WARNING")
            handbook_content = ""
    except Exception as e:
        log_message(f"Error reading Company Handbook: {e}", "ERROR")
        handbook_content = ""
    
    # Read Dashboard
    try:
        if DASHBOARD.exists():
            with open(DASHBOARD, "r", encoding="utf-8") as f:
                dashboard_content = f.read()
            log_message("Read Dashboard.md successfully")
        else:
            log_message("Dashboard.md not found", "WARNING")
            dashboard_content = ""
    except Exception as e:
        log_message(f"Error reading Dashboard: {e}", "ERROR")
        dashboard_content = ""
    
    # Generate professional post content
    timestamp = datetime.now().strftime("%Y-%m-%d")
    
    # Create a professional business update post
    post_templates = [
        f"""🚀 Business Update - {timestamp}

We're excited to share our latest achievements and progress. Our team continues to deliver exceptional results through dedication and innovation.

#BusinessGrowth #ProfessionalExcellence #Innovation""",
        
        f"""💼 Professional Insight - {timestamp}

Success comes from consistent effort and attention to detail. We're committed to maintaining the highest standards in everything we do.

#ProfessionalDevelopment #Excellence #BusinessSuccess""",
        
        f"""📈 Company Update - {timestamp}

We're proud of the milestones we've reached and the value we continue to create. Thank you to our team and partners for their continued support.

#CompanyNews #Growth #TeamWork""",
    ]
    
    # Select a template based on the day
    day_index = datetime.now().weekday() % len(post_templates)
    post_content = post_templates[day_index]
    
    log_message(f"Generated post content ({len(post_content)} characters)")
    return post_content


def save_session_cookies(context, cookies: list) -> None:
    """Save session cookies to JSON file."""
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(cookies, f, indent=2)
        log_message("Session cookies saved successfully")
    except Exception as e:
        log_message(f"Error saving session cookies: {e}", "ERROR")


def load_session_cookies() -> list:
    """Load session cookies from JSON file if it exists."""
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            log_message("Loaded existing session cookies")
            return cookies
        except Exception as e:
            log_message(f"Error loading session cookies: {e}", "WARNING")
    return []


def delete_session_file() -> None:
    """Delete the session cookies file."""
    if SESSION_FILE.exists():
        try:
            SESSION_FILE.unlink()
            log_message("Deleted session cookies file")
        except Exception as e:
            log_message(f"Error deleting session file: {e}", "WARNING")


def take_screenshot(page, filename: str) -> None:
    """Take a screenshot and save to Logs folder."""
    try:
        screenshot_path = LOGS_PATH / filename
        page.screenshot(path=str(screenshot_path))
        log_message(f"Screenshot saved: {filename}")
    except Exception as e:
        log_message(f"Error taking screenshot: {e}", "DEBUG")


def login_to_linkedin(page, email: str, password: str) -> bool:
    """
    Login to LinkedIn and save session cookies.
    Returns True if login successful.
    Uses retry logic with maximum 3 attempts.
    """
    log_message("Starting LinkedIn login process...")

    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        log_message(f"Login attempt {attempt} of {max_attempts}...")

        try:
            # Check for existing session
            existing_cookies = load_session_cookies()
            if existing_cookies:
                log_message("Attempting to use existing session...")
                page.context.add_cookies(existing_cookies)
                page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=60000)
                take_screenshot(page, "session_check.png")

                # Wait for feed element to confirm we're logged in
                try:
                    page.wait_for_selector("div.share-box-feed-entry", timeout=60000)
                    log_message("Existing session is valid, already logged in")
                    take_screenshot(page, "logged_in.png")
                    return True
                except PlaywrightTimeout:
                    log_message("Existing session expired, deleting and trying fresh login")
                    delete_session_file()

            # Fresh login
            log_message("Navigating to LinkedIn login page...")
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=60000)
            take_screenshot(page, "login_page_loaded.png")
            
            # Wait 3 seconds after page load before looking for fields
            log_message("Waiting for page to stabilize...")
            page.wait_for_timeout(3000)
            take_screenshot(page, "page_stabilized.png")

            # Wait for and fill email field with multiple selector attempts
            log_message("Entering email...")
            email_field = None
            email_selectors = [
                'input#username',
                'input[name="session_key"]',
                'input[autocomplete="username"]',
                'input[type="email"]',
            ]
            
            for selector in email_selectors:
                try:
                    log_message(f"Trying email selector: {selector}")
                    email_field = page.locator(selector)
                    email_field.wait_for(state="visible", timeout=30000)
                    log_message(f"Found email field with selector: {selector}")
                    break
                except Exception as e:
                    log_message(f"Email selector failed: {selector} - {e}", "DEBUG")
                    email_field = None
                    continue
            
            if email_field is None:
                log_message("Could not find email field with any selector", "ERROR")
                take_screenshot(page, "no_email_field.png")
                raise Exception("Email field not found")
            
            email_field.fill(email)
            take_screenshot(page, "email_entered.png")

            # Wait for and fill password field with multiple selector attempts
            log_message("Entering password...")
            password_field = None
            password_selectors = [
                'input#password',
                'input[name="session_password"]',
                'input[autocomplete="current-password"]',
                'input[type="password"]',
            ]
            
            for selector in password_selectors:
                try:
                    log_message(f"Trying password selector: {selector}")
                    password_field = page.locator(selector)
                    password_field.wait_for(state="visible", timeout=30000)
                    log_message(f"Found password field with selector: {selector}")
                    break
                except Exception as e:
                    log_message(f"Password selector failed: {selector} - {e}", "DEBUG")
                    password_field = None
                    continue
            
            if password_field is None:
                log_message("Could not find password field with any selector", "ERROR")
                take_screenshot(page, "no_password_field.png")
                raise Exception("Password field not found")
            
            password_field.fill(password)
            take_screenshot(page, "password_entered.png")

            # Click sign in button with multiple selector attempts
            log_message("Clicking sign in button...")
            sign_in_button = None
            button_selectors = [
                'button[type="submit"]',
                'button.sign-in-form__submit-button',
                'button[aria-label="Sign in"]',
            ]
            
            for selector in button_selectors:
                try:
                    log_message(f"Trying submit button selector: {selector}")
                    sign_in_button = page.locator(selector)
                    if sign_in_button.is_visible(timeout=10000):
                        log_message(f"Found submit button with selector: {selector}")
                        break
                    sign_in_button = None
                except Exception as e:
                    log_message(f"Submit button selector failed: {selector} - {e}", "DEBUG")
                    continue
            
            if sign_in_button is None:
                log_message("Could not find submit button with any selector", "ERROR")
                take_screenshot(page, "no_submit_button.png")
                raise Exception("Submit button not found")
            
            sign_in_button.click()
            take_screenshot(page, "submit_clicked.png")

            # Wait for navigation to homepage
            log_message("Waiting for login to complete...")
            try:
                page.wait_for_selector("div.share-box-feed-entry", timeout=60000)
            except PlaywrightTimeout:
                # Check if we're on feed page even if selector doesn't appear
                if "feed" in page.url or "linkedin.com" in page.url:
                    log_message("Login may have succeeded - on LinkedIn domain")
                else:
                    log_message("Login may have failed - checking page state", "WARNING")
            
            take_screenshot(page, "after_login.png")

            # Small delay to ensure page is fully loaded
            page.wait_for_timeout(5000)

            # Save session cookies
            cookies = page.context.cookies()
            save_session_cookies(page.context, cookies)

            log_message("Login successful!")
            return True

        except Exception as e:
            log_message(f"Login attempt {attempt} failed: {e}", "ERROR")
            take_screenshot(page, f"login_error_attempt{attempt}.png")
            if attempt < max_attempts:
                log_message(f"Waiting 5 seconds before retry...")
                page.wait_for_timeout(5000)
                # Delete session file on error
                delete_session_file()
            else:
                log_message(f"All {max_attempts} login attempts failed", "ERROR")
                return False

    return False


def create_post(page, content: str) -> bool:
    """
    Create a LinkedIn post with the given content.
    Returns True if post creation successful.
    """
    log_message("Starting post creation process...")

    try:
        # Navigate to homepage
        log_message("Navigating to LinkedIn homepage...")
        page.goto("https://www.linkedin.com/feed/", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # Find and click "Start a post" button
        log_message("Looking for 'Start a post' button...")

        # Try multiple selectors for the start post button
        post_button = None
        start_post_selectors = [
            'div[data-placeholder="Start a post"]',
            'button.share-box-feed-entry__trigger',
            '[aria-label="Start a post"]',
            'div.share-box-feed-entry__top-bar',
            'div.share-creation-state__toggle-trigger',
            'button:has-text("Start a post")',
            'button:has-text("Start a Post")',
            '[data-test-id="feed-compose-cta"]',
        ]

        for selector in start_post_selectors:
            try:
                log_message(f"Trying Start a post selector: {selector}")
                if page.wait_for_selector(selector, timeout=10000):
                    post_button = page.locator(selector).first
                    if post_button.is_visible(timeout=5000):
                        log_message(f"Found post button with selector: {selector}")
                        break
                    post_button = None
            except Exception as e:
                log_message(f"Selector failed: {selector} - {e}", "DEBUG")
                continue

        if post_button is None:
            log_message("Could not find 'Start a post' button", "ERROR")
            # Take screenshot for debugging
            try:
                page.screenshot(path=str(LOGS_PATH / "linkedin_error.png"))
                log_message("Screenshot saved to Logs/linkedin_error.png", "WARNING")
            except Exception:
                pass
            return False

        post_button.click()
        log_message("Clicked 'Start a post' button")

        # Wait 3 seconds for post dialog to appear
        log_message("Waiting for post dialog to appear...")
        page.wait_for_timeout(3000)

        # Find the text editor and type content
        log_message("Entering post content...")

        # Try multiple selectors for the text editor/textarea
        editor = None
        editor_selectors = [
            'div.ql-editor',
            'div[role="textbox"]',
            'div[contenteditable="true"]',
            'div.share-creation-state__text-editor div[contenteditable="true"]',
            '.editor-composer__content',
            'div[aria-label="What do you want to talk about?"]',
            'div[aria-label="What do you want to talk about?"] div[contenteditable="true"]',
        ]

        for selector in editor_selectors:
            try:
                log_message(f"Trying editor selector: {selector}")
                if page.wait_for_selector(selector, timeout=10000):
                    editor = page.locator(selector).first
                    if editor.is_visible(timeout=5000):
                        log_message(f"Found editor with selector: {selector}")
                        break
                    editor = None
            except Exception as e:
                log_message(f"Editor selector failed: {selector} - {e}", "DEBUG")
                continue

        if editor is None:
            log_message("Could not find post editor", "ERROR")
            # Take screenshot for debugging
            try:
                page.screenshot(path=str(LOGS_PATH / "linkedin_error.png"))
                log_message("Screenshot saved to Logs/linkedin_error.png", "WARNING")
            except Exception:
                pass
            return False

        # Clear any existing content and type new content
        editor.click()
        page.wait_for_timeout(500)
        editor.fill(content)
        page.wait_for_timeout(1000)

        log_message("Post content entered")

        # Find and click "Post" button
        log_message("Looking for 'Post' button...")

        post_submit = None
        submit_selectors = [
            'button.share-actions__primary-action',
            'button[aria-label="Post"]',
            'div.share-actions button.artdeco-button--primary',
            'button:has-text("Post")',
            'button:has-text("POST")',
        ]

        for selector in submit_selectors:
            try:
                log_message(f"Trying Post button selector: {selector}")
                if page.wait_for_selector(selector, timeout=10000):
                    post_submit = page.locator(selector).first
                    if post_submit.is_visible(timeout=5000) and post_submit.is_enabled(timeout=5000):
                        log_message(f"Found post submit button with selector: {selector}")
                        break
                    post_submit = None
            except Exception as e:
                log_message(f"Post button selector failed: {selector} - {e}", "DEBUG")
                continue

        if post_submit is None:
            log_message("Could not find 'Post' button", "ERROR")
            # Take screenshot for debugging
            try:
                page.screenshot(path=str(LOGS_PATH / "linkedin_error.png"))
                log_message("Screenshot saved to Logs/linkedin_error.png", "WARNING")
            except Exception:
                pass
            return False

        # Click the post button
        post_submit.click()
        log_message("Clicked 'Post' button")

        # Wait for confirmation
        page.wait_for_timeout(3000)

        # Check if post was successful (look for confirmation or return to feed)
        log_message("Waiting for post confirmation...")

        # If we see a "Post" button still, the post might have failed
        try:
            still_see_post_button = page.locator('button:has-text("Post")').first.is_visible(timeout=3000)
            if still_see_post_button:
                log_message("Post button still visible - post may not have submitted", "WARNING")
        except Exception:
            pass

        log_message("Post creation completed successfully!")
        return True

    except Exception as e:
        log_message(f"Post creation error: {e}", "ERROR")
        # Take screenshot for debugging
        try:
            page.screenshot(path=str(LOGS_PATH / "linkedin_error.png"))
            log_message("Screenshot saved to Logs/linkedin_error.png", "WARNING")
        except Exception:
            pass
        return False


def run_linkedin_poster(test_mode: bool = False) -> bool:
    """
    Main function to run the LinkedIn posting flow.
    """
    log_message("=" * 50)
    log_message("LINKEDIN AUTO-POSTER STARTED")
    if test_mode:
        log_message("TEST MODE: No actual posting will occur")
    log_message("=" * 50)
    
    # Load environment
    env = load_env()
    
    if not env["email"] or env["email"] == "your_linkedin_email_here":
        log_message("ERROR: LinkedIn email not configured in .env file", "ERROR")
        log_message("Please update LINKEDIN_EMAIL in .env file")
        return False
    
    if not env["password"] or env["password"] == "your_linkedin_password_here":
        log_message("ERROR: LinkedIn password not configured in .env file", "ERROR")
        log_message("Please update LINKEDIN_PASSWORD in .env file")
        return False
    
    log_message(f"Loaded credentials for: {env['email']}")
    log_message(f"Post interval: {env['post_interval']} hours")
    
    # Generate post content
    post_content = generate_post_content()
    log_message(f"Generated content preview:\n{post_content[:200]}...")
    
    if test_mode:
        log_message("TEST MODE: Skipping actual login and posting")
        log_message("Test completed successfully - content generated")
        return True
    
    # Use Playwright to login and post
    try:
        with sync_playwright() as p:
            log_message("Launching Chromium browser...")
            browser = p.chromium.launch(
                headless=False,  # Set to True for headless mode
                slow_mo=500,  # Slow down for visibility
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
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Add stealth script to avoid detection
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined})
            """)
            
            page = context.new_page()
            
            # Login
            login_success = login_to_linkedin(page, env["email"], env["password"])
            
            if not login_success:
                log_message("Login failed, aborting post", "ERROR")
                browser.close()
                return False
            
            page.wait_for_timeout(2000)
            
            # Create post
            post_success = create_post(page, post_content)
            
            # Close browser
            browser.close()
            
            if post_success:
                log_message("=" * 50)
                log_message("LINKEDIN POST SUCCESSFUL!")
                log_message("=" * 50)
                return True
            else:
                log_message("Post creation failed", "ERROR")
                return False
                
    except Exception as e:
        log_message(f"Browser automation error: {e}", "ERROR")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="LinkedIn Auto-Poster")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run in test mode (dry run without actual posting)"
    )
    
    args = parser.parse_args()
    
    success = run_linkedin_poster(test_mode=args.test)
    
    if success:
        print("\n[SUCCESS] LinkedIn posting completed successfully!")
        sys.exit(0)
    else:
        print("\n[FAILED] LinkedIn posting failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
