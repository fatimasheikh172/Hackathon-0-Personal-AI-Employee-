#!/usr/bin/env python3
"""
Instagram Scheduler - Automatically posts on Instagram every 24 hours
Uses instagrapi library for reliable posting
"""

import os
import sys
import time
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
INSTAGRAM_POSTER = VAULT_PATH / "instagram_instagrapi.py"
POST_INTERVAL = int(os.getenv("INSTAGRAM_POST_INTERVAL", "24"))

# Scheduler statistics
scheduler_stats = {
    "last_post": None,
    "next_post": None,
    "total_posts": 0
}


def log_message(message):
    """Log a message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    print(log_entry)
    
    try:
        log_file = VAULT_PATH / "Logs" / f"instagram_scheduler_{datetime.now().strftime('%Y-%m-%d')}.txt"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"ERROR writing to log: {e}")


def run_instagram_poster():
    """Run the Instagram poster script"""
    try:
        log_message("Starting Instagram poster...")
        
        result = subprocess.run(
            [sys.executable, str(INSTAGRAM_POSTER)],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            log_message("Instagram poster completed successfully")
            scheduler_stats["last_post"] = datetime.now()
            scheduler_stats["total_posts"] += 1
            
            next_post = scheduler_stats["last_post"] + timedelta(hours=POST_INTERVAL)
            scheduler_stats["next_post"] = next_post
            
            return True
        else:
            log_message(f"Instagram poster failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        log_message("Instagram poster timed out")
        return False
    except Exception as e:
        log_message(f"Error running Instagram poster: {e}")
        return False


def main():
    """Main function - runs Instagram scheduler in infinite loop"""
    print("=" * 60)
    print("Instagram Scheduler - AI Employee System")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Post Interval: {POST_INTERVAL} hours")
    print(f"Instagram Poster: {INSTAGRAM_POSTER}")
    print("=" * 60)
    
    print("\nStarting in 10 seconds...")
    time.sleep(10)
    
    log_message("Running initial post...")
    run_instagram_poster()
    
    if scheduler_stats["last_post"]:
        scheduler_stats["next_post"] = scheduler_stats["last_post"] + timedelta(hours=POST_INTERVAL)
    
    print("\n" + "=" * 60)
    print("SCHEDULER STARTED")
    print("=" * 60)
    print(f"Posts every {POST_INTERVAL} hours")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            if scheduler_stats["next_post"]:
                now = datetime.now()
                time_until_next = scheduler_stats["next_post"] - now
                
                if time_until_next.total_seconds() <= 0:
                    log_message(f"\nScheduled time reached - posting...")
                    run_instagram_poster()
                else:
                    hours = int(time_until_next.total_seconds() // 3600)
                    minutes = int((time_until_next.total_seconds() % 3600) // 60)
                    print(f"Next post in: {hours}h {minutes}m", end='\r')
            else:
                log_message("No scheduled post - running now...")
                run_instagram_poster()
            
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user")
            sys.exit(0)
        except Exception as e:
            log_message(f"Scheduler error: {e}")
            time.sleep(300)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
