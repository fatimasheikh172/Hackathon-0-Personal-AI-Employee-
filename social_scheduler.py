#!/usr/bin/env python3
"""
Social Media Scheduler - 2026 Updated Version
Multi-platform scheduler for Twitter/X, LinkedIn, and Instagram
Supports DRY_RUN mode, content adaptation, and automated scheduling
"""

import os
import sys
import time
import json
import shutil
import random
import re
import argparse
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"
BRIEFINGS_FOLDER = VAULT_PATH / "Briefings"

# Social content folders
SOCIAL_PENDING = VAULT_PATH / "Social_Content" / "pending"
SOCIAL_POSTED = VAULT_PATH / "Social_Content" / "posted"
SOCIAL_DRAFTS = VAULT_PATH / "Social_Content" / "drafts"
SOCIAL_FAILED = VAULT_PATH / "Social_Content" / "failed"

# Manager scripts
TWITTER_MANAGER = VAULT_PATH / "twitter_manager.py"
LINKEDIN_MANAGER = VAULT_PATH / "linkedin_manager.py"
INSTAGRAM_MANAGER = VAULT_PATH / "instagram_manager.py"

# Environment settings
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"

# Posting schedule (9 AM, 12 PM, 5 PM)
POST_TIMES = [9, 12, 17]  # Hours in 24-hour format

# Rate limits per platform
RATE_LIMITS = {
    "twitter": {"posts_per_hour": 5, "posts_per_day": 20},
    "linkedin": {"posts_per_hour": 1, "posts_per_day": 3},
    "instagram": {"posts_per_hour": 2, "posts_per_day": 5}
}

# Statistics
scheduler_stats = {
    "last_run": None,
    "posts_today": {"twitter": 0, "linkedin": 0, "instagram": 0},
    "total_posts": {"twitter": 0, "linkedin": 0, "instagram": 0},
    "failed_posts": 0
}


def get_log_file_path():
    """Get log file path with current date"""
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"social_scheduler_{date_str}.json"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, BRIEFINGS_FOLDER, SOCIAL_PENDING, SOCIAL_POSTED, 
                   SOCIAL_DRAFTS, SOCIAL_FAILED]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True, data=None):
    """Log a scheduler action to JSON log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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
            if a["type"] == "post_scheduled" and a["success"]
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
        "platform": "Multi-Platform Scheduler",
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


def adapt_content_for_platform(content, platform):
    """
    Adapt content for specific platform requirements
    
    Twitter: max 280 chars, punchy
    LinkedIn: professional, 150-300 words
    Instagram: hashtag-heavy caption
    """
    content = content.strip()
    
    if platform == "twitter":
        # Max 280 characters, punchy style
        if len(content) > 280:
            content = content[:277] + "..."
        
        # Add relevant hashtags if not present
        if "#" not in content:
            hashtags = ["#AI", "#Automation", "#Business"]
            content += f" {' '.join(random.sample(hashtags, 2))}"
        
        # Ensure still under limit
        if len(content) > 280:
            content = content[:277] + "..."
        
        return content
    
    elif platform == "linkedin":
        # Professional tone, 150-300 words optimal
        words = content.split()
        
        # If too short, expand with professional context
        if len(words) < 100:
            expansions = [
                "\n\nThis reflects our commitment to excellence and continuous improvement.",
                "\n\nWe remain dedicated to delivering value through innovation.",
                "\n\nOur team continues to push boundaries and achieve exceptional results."
            ]
            content += random.choice(expansions)
        
        # Add professional hashtags
        professional_tags = ["#ProfessionalExcellence", "#BusinessGrowth", "#Innovation", "#Leadership"]
        if not any(tag in content for tag in professional_tags):
            content += f"\n\n{' '.join(random.sample(professional_tags, 2))}"
        
        return content
    
    elif platform == "instagram":
        # Hashtag-heavy caption with emojis
        emojis = ["🚀", "✨", "💡", "🎯", "📈", "💼", "🏆", "🌟"]
        
        # Add emoji at start if not present
        if not any(e in content for e in emojis):
            content = f"{random.choice(emojis)} {content}"
        
        # Add hashtags if not present
        if "#" not in content:
            hashtags = [
                "#BusinessGrowth", "#Innovation", "#Success", "#Motivation",
                "#Leadership", "#Productivity", "#AI", "#Automation", "#Entrepreneur",
                "#Mindset", "#Growth", "#Inspiration", "#Technology", "#Future"
            ]
            content += f"\n\n{' '.join(random.sample(hashtags, 12))}"
        
        return content
    
    return content


def validate_content(content, platform):
    """Validate content for platform requirements"""
    if not content or not content.strip():
        return False, "Empty content"
    
    if platform == "twitter":
        if len(content) > 280:
            return False, f"Content too long: {len(content)} > 280 chars"
    
    elif platform == "linkedin":
        if len(content) < 50:
            return False, "Content too short for LinkedIn (min 50 chars)"
    
    elif platform == "instagram":
        if len(content) < 20:
            return False, "Content too short for Instagram (min 20 chars)"
    
    return True, "Valid"


def run_platform_manager(platform, content, image_path=None):
    """
    Run the appropriate platform manager script
    Returns (success, message)
    """
    import subprocess
    
    if platform == "twitter":
        script = TWITTER_MANAGER
        args = ["--content", content]
    elif platform == "linkedin":
        script = LINKEDIN_MANAGER
        args = ["--content", content]
    elif platform == "instagram":
        script = INSTAGRAM_MANAGER
        if image_path:
            args = ["--image", image_path, "--caption", content]
        else:
            args = ["--topic", content[:100]]
    else:
        return False, f"Unknown platform: {platform}"
    
    if DRY_RUN:
        args.insert(0, "--test")
    
    try:
        log_action("running_manager", f"Running {platform} manager for: {content[:50]}...")
        
        result = subprocess.run(
            [sys.executable, str(script)] + args,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            log_action("manager_success", f"{platform} post successful")
            return True, "Success"
        else:
            error_msg = result.stderr[:500] if result.stderr else "Unknown error"
            log_action("manager_failed", f"{platform} post failed: {error_msg}", success=False)
            return False, error_msg
    
    except subprocess.TimeoutExpired:
        log_action("manager_timeout", f"{platform} post timed out", success=False)
        return False, "Timeout"
    except Exception as e:
        log_action("manager_error", f"{platform} post error: {e}", success=False)
        return False, str(e)


def process_pending_content():
    """
    Process all pending content files
    Returns (success_count, failed_count)
    """
    print("\n" + "=" * 60)
    print("PROCESSING PENDING CONTENT")
    print("=" * 60)
    
    success_count = 0
    failed_count = 0
    
    # Get all pending files
    pending_files = list(SOCIAL_PENDING.glob("*.txt")) + \
                    list(SOCIAL_PENDING.glob("*.md")) + \
                    list(SOCIAL_PENDING.glob("*.json"))
    
    if not pending_files:
        print("No pending content found")
        return 0, 0
    
    print(f"Found {len(pending_files)} pending content file(s)")
    
    for pending_file in pending_files:
        print(f"\nProcessing: {pending_file.name}")
        
        try:
            # Read content
            with open(pending_file, "r", encoding="utf-8") as f:
                content_data = f.read()
            
            # Parse JSON or use as plain text
            if pending_file.suffix == ".json":
                try:
                    data = json.loads(content_data)
                    content = data.get("content", data.get("text", ""))
                    image_path = data.get("image_path")
                except json.JSONDecodeError:
                    content = content_data
                    image_path = None
            else:
                content = content_data
                image_path = None
            
            if not content.strip():
                print(f"  [SKIP] Empty content in {pending_file.name}")
                failed_count += 1
                move_to_failed(pending_file, "Empty content")
                continue
            
            # Validate and post to each platform
            platforms = ["twitter", "linkedin", "instagram"]
            platform_results = {}
            
            for platform in platforms:
                print(f"\n  Posting to {platform}...")
                
                # Adapt content for platform
                adapted_content = adapt_content_for_platform(content, platform)
                
                # Validate
                valid, reason = validate_content(adapted_content, platform)
                if not valid:
                    print(f"    [SKIP] Invalid content: {reason}")
                    platform_results[platform] = {"success": False, "reason": reason}
                    continue
                
                # Post
                success, message = run_platform_manager(platform, adapted_content, image_path)
                platform_results[platform] = {"success": success, "reason": message}
                
                if success:
                    scheduler_stats["posts_today"][platform] += 1
                    print(f"    [OK] Posted to {platform}")
                else:
                    print(f"    [FAIL] {platform}: {message}")
            
            # Move file based on results
            all_failed = all(not r["success"] for r in platform_results.values())
            
            if all_failed:
                move_to_failed(pending_file, str(platform_results))
                failed_count += 1
            else:
                move_to_posted(pending_file, platform_results)
                success_count += 1
            
        except Exception as e:
            print(f"  [ERROR] Processing failed: {e}")
            move_to_failed(pending_file, str(e))
            failed_count += 1
    
    return success_count, failed_count


def move_to_posted(source_file, results):
    """Move file to posted folder with results metadata"""
    try:
        SOCIAL_POSTED.mkdir(parents=True, exist_ok=True)
        
        # Create metadata file
        metadata = {
            "original_file": source_file.name,
            "posted_at": datetime.now().isoformat(),
            "platforms": results,
            "dry_run": DRY_RUN
        }
        
        # Move content file
        dest_file = SOCIAL_POSTED / f"posted_{source_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{source_file.suffix}"
        shutil.move(str(source_file), str(dest_file))
        
        # Save metadata
        meta_file = SOCIAL_POSTED / f"{dest_file.stem}_meta.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        log_action("content_posted", f"Moved {source_file.name} to posted")
        
    except Exception as e:
        log_action("move_posted_error", str(e), success=False)


def move_to_failed(source_file, error):
    """Move file to failed folder with error details"""
    try:
        SOCIAL_FAILED.mkdir(parents=True, exist_ok=True)
        
        # Create error metadata
        metadata = {
            "original_file": source_file.name,
            "failed_at": datetime.now().isoformat(),
            "error": error,
            "dry_run": DRY_RUN
        }
        
        # Move content file
        dest_file = SOCIAL_FAILED / f"failed_{source_file.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{source_file.suffix}"
        shutil.move(str(source_file), str(dest_file))
        
        # Save metadata
        meta_file = SOCIAL_FAILED / f"{dest_file.stem}_error.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        
        log_action("content_failed", f"Moved {source_file.name} to failed: {error}", success=False)
        
    except Exception as e:
        log_action("move_failed_error", str(e), success=False)


def get_next_scheduled_time():
    """Get next scheduled post time"""
    now = datetime.now()
    
    for hour in POST_TIMES:
        scheduled = now.replace(hour=hour, minute=0, second=0, microsecond=0)
        if scheduled > now:
            return scheduled
    
    # All times passed today, schedule for tomorrow 9 AM
    tomorrow = now + timedelta(days=1)
    return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)


def generate_weekly_summary():
    """Generate weekly summary briefing"""
    print("\n" + "=" * 60)
    print("GENERATING WEEKLY SUMMARY")
    print("=" * 60)
    
    BRIEFINGS_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Get current week's logs
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    
    total_posts = {"twitter": 0, "linkedin": 0, "instagram": 0}
    total_errors = 0
    
    # Scan logs for the week
    for log_file in LOGS_FOLDER.glob("social_scheduler_*.json"):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for action in data.get("actions", []):
                if action["type"] == "post_scheduled" and action.get("success"):
                    platform = action.get("data", {}).get("platform", "unknown")
                    if platform in total_posts:
                        total_posts[platform] += 1
                elif not action.get("success", True):
                    total_errors += 1
        except Exception:
            pass
    
    # Create summary
    summary_date = today.strftime("%Y-%m-%d")
    summary = f"""# Social Media Weekly Summary

**Generated:** {today.strftime("%Y-%m-%d %H:%M:%S")}
**Week Starting:** {week_start.strftime("%Y-%m-%d")}

## Posting Statistics

| Platform | Posts This Week |
|----------|----------------|
| Twitter/X | {total_posts['twitter']} |
| LinkedIn | {total_posts['linkedin']} |
| Instagram | {total_posts['instagram']} |
| **Total** | **{sum(total_posts.values())}** |

## Error Summary
- Total Errors: {total_errors}

## Rate Limit Status
- Twitter: {scheduler_stats['posts_today']['twitter']}/{RATE_LIMITS['twitter']['posts_per_day']} today
- LinkedIn: {scheduler_stats['posts_today']['linkedin']}/{RATE_LIMITS['linkedin']['posts_per_day']} today
- Instagram: {scheduler_stats['posts_today']['instagram']}/{RATE_LIMITS['instagram']['posts_per_day']} today

## Next Scheduled Posts
- Next run: {get_next_scheduled_time().strftime("%Y-%m-%d %H:%M:%S")}

## DRY_RUN Mode
- Status: {'Enabled (no actual posting)' if DRY_RUN else 'Disabled (live posting)'}

---
*Generated by AI Employee Social Scheduler*
"""
    
    # Save summary
    summary_file = BRIEFINGS_FOLDER / f"social_summary_{summary_date}.md"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.write(summary)
    
    print(f"Summary saved to: {summary_file}")
    log_action("summary_generated", f"Weekly summary: {summary_file.name}")
    
    return summary


def run_scheduler_cycle():
    """Run one complete scheduler cycle"""
    print("\n" + "=" * 60)
    print("SCHEDULER CYCLE")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"DRY_RUN: {DRY_RUN}")
    
    scheduler_stats["last_run"] = datetime.now()
    
    # Process pending content
    success_count, failed_count = process_pending_content()
    
    # Update stats
    scheduler_stats["failed_posts"] += failed_count
    
    # Log summary
    log_action("cycle_complete", 
               f"Processed {success_count + failed_count} files: {success_count} success, {failed_count} failed",
               data={"success": success_count, "failed": failed_count})
    
    return success_count, failed_count


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Social Media Scheduler')
    parser.add_argument('--test', action='store_true', help='Test mode')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--summary', action='store_true', help='Generate weekly summary')
    parser.add_argument('--interval', type=int, default=30, help='Check interval in minutes')
    args = parser.parse_args()

    global DRY_RUN
    if args.test:
        DRY_RUN = True

    print("=" * 60)
    print("Social Media Scheduler - AI Employee System (2026)")
    print("=" * 60)
    print(f"Vault: {VAULT_PATH}")
    print(f"DRY_RUN: {DRY_RUN}")
    print(f"Schedule: {POST_TIMES} (9 AM, 12 PM, 5 PM)")
    print("=" * 60)

    ensure_folders_exist()

    # Generate summary if requested
    if args.summary:
        generate_weekly_summary()
        if args.once:
            return 0

    # Run once mode
    if args.once:
        print("\n[ONCE MODE] Running single cycle...")
        success, failed = run_scheduler_cycle()
        print(f"\nCompleted: {success} success, {failed} failed")
        return 0 if failed == 0 else 1

    # Continuous scheduler mode
    print("\n" + "=" * 60)
    print("SCHEDULER STARTED")
    print("=" * 60)
    print(f"Check interval: {args.interval} minutes")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            now = datetime.now()
            next_run = get_next_scheduled_time()
            
            # Check if it's a scheduled time
            if now >= next_run:
                run_scheduler_cycle()
            
            # Wait before next check
            time.sleep(args.interval * 60)

    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user")
        return 0
    except Exception as e:
        log_action("fatal_error", str(e), success=False)
        print(f"\n[ERROR] Fatal: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
