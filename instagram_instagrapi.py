#!/usr/bin/env python3
"""
Instagram Poster using instagrapi library
More reliable than Playwright for Instagram posting
No API key required - uses username/password login
"""

import os
import sys
import json
import random
import re
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, ChallengeRequired
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
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_EMAIL", "")
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
    return LOGS_FOLDER / f"instagram_instagrapi_{date_str}.json"


def get_text_log_file_path():
    """Get text log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"instagram_instagrapi_activity_{date_str}.txt"


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
    return SESSION_FOLDER / "instagrapi_session.json"


def login():
    """
    Login to Instagram using instagrapi
    
    Returns:
        Client object if successful, None otherwise
    """
    print("\n" + "=" * 60)
    print("INSTAGRAM LOGIN (instagrapi)")
    print("=" * 60)
    
    try:
        client = Client()
        session_file = get_session_file()
        
        # Try to load saved session
        if session_file.exists():
            print("Loading saved session...")
            try:
                client.load_settings(session_file)
                client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                print("[OK] Logged in with saved session!")
                log_action("login_success", "Logged in with saved session")
                return client
            except Exception as e:
                print(f"Saved session invalid: {e}")
                print("Attempting fresh login...")
        
        # Fresh login
        if not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD:
            print("[ERROR] Instagram credentials not found in .env file")
            log_action("login_error", "Credentials missing", success=False)
            return None
        
        print("Logging in with username/password...")
        client.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
        
        # Save session
        SESSION_FOLDER.mkdir(parents=True, exist_ok=True)
        client.dump_settings(session_file)
        print(f"[OK] Session saved to {session_file}")
        
        print("[OK] Instagram login successful!")
        log_action("login_success", "Fresh login completed")
        
        return client
        
    except ChallengeRequired as e:
        print(f"[ERROR] Challenge required: {e}")
        print("Instagram requires additional verification.")
        print("Please login manually in a browser first, then try again.")
        log_action("login_challenge", str(e), success=False)
        return None
        
    except LoginRequired as e:
        print(f"[ERROR] Login required: {e}")
        log_action("login_required", str(e), success=False)
        return None
        
    except Exception as e:
        print(f"[ERROR] Login failed: {e}")
        log_action("login_error", str(e), success=False)
        return None


def post_image(client, image_path, caption, test_mode=False):
    """
    Post image to Instagram
    
    Args:
        client: instagrapi Client object
        image_path: Path to image file
        caption: Post caption
        test_mode: If True, don't actually post
    
    Returns:
        True if successful, False otherwise
    """
    print("\n" + "=" * 60)
    print("POST IMAGE TO INSTAGRAM")
    print("=" * 60)
    print(f"Image: {image_path}")
    print(f"Caption: {caption[:100]}...")
    print("=" * 60)
    
    if test_mode:
        print("[TEST MODE] Skipping actual post")
        log_action("post_test", f"Test post: {caption[:100]}...")
        return True
    
    try:
        # Upload photo
        print("Uploading photo...")
        media = client.photo_upload(image_path, caption)
        
        print(f"[OK] Post created successfully!")
        print(f"Media ID: {media.pk if media else 'N/A'}")
        log_action("post_created", f"Posted: {caption[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Post failed: {e}")
        log_action("post_error", str(e), success=False)
        return False


def generate_content():
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
        
        # Create a simple fallback image
        try:
            img = Image.new('RGB', (1080, 1080), color='black')
            draw = ImageDraw.Draw(img)
            draw.text((540, 540), text[:50], fill='white', anchor="mm")
            
            POSTS_FOLDER.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = POSTS_FOLDER / f"post_{timestamp}_fallback.png"
            img.save(str(image_path), "PNG")
            
            return image_path
        except:
            return None


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
    print("Instagram Poster (instagrapi) - AI Employee System")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Test Mode: {test_mode}")
    print(f"Post Interval: {INSTAGRAM_POST_INTERVAL} hours")
    print("=" * 60)
    
    ensure_folders_exist()
    
    if not test_mode and (not INSTAGRAM_USERNAME or not INSTAGRAM_PASSWORD):
        print("\n[ERROR] Instagram credentials not set in .env file")
        print("Please add INSTAGRAM_EMAIL and INSTAGRAM_PASSWORD to .env")
        sys.exit(1)
    
    try:
        # Generate caption
        caption = generate_content()
        
        # Create text image
        print("\nCreating text image for post...")
        image_path = create_text_image(caption.split('\n')[0][:100])
        
        if not image_path:
            print("[ERROR] Failed to create image")
            sys.exit(1)
        
        # Login to Instagram
        print("\nLogging in to Instagram...")
        client = login()
        
        if not client and not test_mode:
            print("\n[ERROR] Login failed - cannot post")
            sys.exit(1)
        
        # Post image
        if test_mode:
            print("\n[TEST MODE] Would post:")
            print(f"Image: {image_path}")
            print(f"Caption: {caption[:200]}...")
            success = True
        else:
            success = post_image(client, image_path, caption, test_mode)
        
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
