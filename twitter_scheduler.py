#!/usr/bin/env python3
"""
Twitter Scheduler - Automatically posts tweets every 12 hours
Uses Playwright automation with session persistence
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
TWITTER_POSTER = VAULT_PATH / "twitter_poster.py"
POST_INTERVAL = int(os.getenv("TWITTER_POST_INTERVAL", "12"))

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
    
    # Also write to log file
    try:
        log_file = VAULT_PATH / "Logs" / f"twitter_scheduler_{datetime.now().strftime('%Y-%m-%d')}.txt"
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"ERROR writing to log: {e}")


def run_twitter_poster():
    """Run the Twitter poster script"""
    try:
        log_message("Starting Twitter poster...")
        
        result = subprocess.run(
            [sys.executable, str(TWITTER_POSTER)],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            log_message("Twitter poster completed successfully")
            scheduler_stats["last_post"] = datetime.now()
            scheduler_stats["total_posts"] += 1
            
            # Calculate next post time
            next_post = scheduler_stats["last_post"] + timedelta(hours=POST_INTERVAL)
            scheduler_stats["next_post"] = next_post
            
            return True
        else:
            log_message(f"Twitter poster failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        log_message("Twitter poster timed out")
        return False
    except Exception as e:
        log_message(f"Error running Twitter poster: {e}")
        return False


def main():
    """Main function - runs Twitter scheduler in infinite loop"""
    print("=" * 60)
    print("Twitter Scheduler - AI Employee System")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Post Interval: {POST_INTERVAL} hours")
    print(f"Twitter Poster: {TWITTER_POSTER}")
    print("=" * 60)
    
    # Initial delay before first post
    print("\nStarting in 10 seconds...")
    time.sleep(10)
    
    # Run first post immediately
    log_message("Running initial tweet...")
    run_twitter_poster()
    
    # Calculate next post time
    if scheduler_stats["last_post"]:
        scheduler_stats["next_post"] = scheduler_stats["last_post"] + timedelta(hours=POST_INTERVAL)
    
    # Main scheduler loop
    print("\n" + "=" * 60)
    print("SCHEDULER STARTED")
    print("=" * 60)
    print(f"Posts every {POST_INTERVAL} hours")
    print("Press Ctrl+C to stop\n")
    
    while True:
        try:
            # Check if it's time for next post
            if scheduler_stats["next_post"]:
                now = datetime.now()
                time_until_next = scheduler_stats["next_post"] - now
                
                if time_until_next.total_seconds() <= 0:
                    # Time to post
                    log_message(f"\nScheduled time reached - posting tweet...")
                    run_twitter_poster()
                else:
                    # Show countdown
                    hours = int(time_until_next.total_seconds() // 3600)
                    minutes = int((time_until_next.total_seconds() % 3600) // 60)
                    print(f"Next tweet in: {hours}h {minutes}m", end='\r')
            else:
                # No next post scheduled, run now
                log_message("No scheduled post - running now...")
                run_twitter_poster()
            
            # Sleep for 1 minute before checking again
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("\n\nScheduler stopped by user")
            sys.exit(0)
        except Exception as e:
            log_message(f"Scheduler error: {e}")
            time.sleep(300)  # Wait 5 minutes on error


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
