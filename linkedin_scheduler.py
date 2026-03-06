#!/usr/bin/env python3
"""
LinkedIn Auto-Poster Scheduler
Runs linkedin_poster.py automatically at specified intervals.
"""

import os
import sys
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Configuration
VAULT_PATH = Path(r"F:\AI_Employee_Vault")
LOGS_PATH = VAULT_PATH / "Logs"
POSTER_SCRIPT = VAULT_PATH / "linkedin_poster.py"
SCHEDULER_STATE_FILE = VAULT_PATH / ".linkedin_scheduler_state.json"

# Ensure logs directory exists
LOGS_PATH.mkdir(exist_ok=True)


def log_message(message: str, level: str = "INFO") -> None:
    """Log a message with timestamp to both console and log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    print(log_entry)
    
    # Write to log file
    log_file = LOGS_PATH / f"linkedin_scheduler_{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")


def load_env() -> dict:
    """Load environment variables from .env file."""
    load_dotenv(VAULT_PATH / ".env")
    return {
        "post_interval": int(os.getenv("LINKEDIN_POST_INTERVAL", "24")),
    }


def load_scheduler_state() -> dict:
    """Load scheduler state from file."""
    if SCHEDULER_STATE_FILE.exists():
        try:
            import json
            with open(SCHEDULER_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            log_message("Loaded scheduler state")
            return state
        except Exception as e:
            log_message(f"Error loading scheduler state: {e}", "WARNING")
    return {}


def save_scheduler_state(state: dict) -> None:
    """Save scheduler state to file."""
    try:
        import json
        with open(SCHEDULER_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        log_message("Saved scheduler state")
    except Exception as e:
        log_message(f"Error saving scheduler state: {e}", "ERROR")


def calculate_next_post_time(interval_hours: int) -> datetime:
    """Calculate the next scheduled post time."""
    return datetime.now() + timedelta(hours=interval_hours)


def run_poster_script() -> bool:
    """Run the LinkedIn poster script."""
    log_message("Running LinkedIn poster script...")
    
    try:
        result = subprocess.run(
            [sys.executable, str(POSTER_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        # Log output
        if result.stdout:
            for line in result.stdout.strip().split("\n"):
                log_message(f"Poster: {line}")
        
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                log_message(f"Poster Error: {line}", "ERROR")
        
        success = result.returncode == 0
        log_message(f"Poster script completed with return code: {result.returncode}")
        return success
        
    except subprocess.TimeoutExpired:
        log_message("Poster script timed out after 5 minutes", "ERROR")
        return False
    except Exception as e:
        log_message(f"Error running poster script: {e}", "ERROR")
        return False


def update_dashboard_stats(success: bool) -> None:
    """Update Dashboard.md with LinkedIn posting stats."""
    dashboard_file = VAULT_PATH / "Dashboard.md"
    
    try:
        if not dashboard_file.exists():
            log_message("Dashboard.md not found, skipping stats update", "WARNING")
            return
        
        with open(dashboard_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check if LinkedIn Status section exists
        if "## LinkedIn Status" in content:
            # Update the section
            lines = content.split("\n")
            new_lines = []
            in_linkedin_section = False
            section_updated = False
            
            for line in lines:
                if line.strip() == "## LinkedIn Status":
                    in_linkedin_section = True
                    new_lines.append(line)
                    continue
                
                if in_linkedin_section:
                    if line.startswith("## ") and "LinkedIn" not in line:
                        # New section started
                        in_linkedin_section = False
                        section_updated = True
                    
                    elif "- Last Post:" in line:
                        if success:
                            new_lines.append(f"- Last Post: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                        continue
                    
                    elif "- Next Scheduled Post:" in line:
                        next_post = calculate_next_post_time(load_env()["post_interval"])
                        new_lines.append(f"- Next Scheduled Post: {next_post.strftime('%Y-%m-%d %H:%M:%S')}")
                        continue
                    
                    elif "- Total Posts This Week:" in line and success:
                        # Try to extract current count and increment
                        try:
                            current_count = int(line.split(":")[1].strip())
                            new_lines.append(f"- Total Posts This Week: {current_count + 1}")
                        except (ValueError, IndexError):
                            new_lines.append("- Total Posts This Week: 1")
                        continue
                    
                    else:
                        new_lines.append(line)
                        continue
                else:
                    new_lines.append(line)
            
            content = "\n".join(new_lines)
        
        with open(dashboard_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        log_message("Dashboard stats updated")
        
    except Exception as e:
        log_message(f"Error updating dashboard: {e}", "WARNING")


def run_scheduler() -> None:
    """Main scheduler loop."""
    log_message("=" * 50)
    log_message("LINKEDIN SCHEDULER STARTED")
    log_message("=" * 50)
    
    # Load configuration
    env = load_env()
    interval_hours = env["post_interval"]
    
    log_message(f"Post interval: {interval_hours} hours")
    
    # Load or initialize state
    state = load_scheduler_state()
    
    if "last_post_time" in state:
        last_post = datetime.fromisoformat(state["last_post_time"])
        log_message(f"Last post time: {last_post.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        log_message("No previous post time recorded")
        last_post = None
    
    if "next_post_time" in state:
        next_post = datetime.fromisoformat(state["next_post_time"])
        log_message(f"Next scheduled post: {next_post.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        next_post = calculate_next_post_time(interval_hours)
        log_message(f"First post scheduled for: {next_post.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if we should post immediately on first run
    if last_post is None:
        log_message("First run - posting immediately")
        success = run_poster_script()
        
        if success:
            update_dashboard_stats(True)
            last_post = datetime.now()
            next_post = calculate_next_post_time(interval_hours)
            
            state["last_post_time"] = last_post.isoformat()
            state["next_post_time"] = next_post.isoformat()
            state["total_posts"] = state.get("total_posts", 0) + 1
            save_scheduler_state(state)
    
    log_message("Starting scheduler loop...")
    log_message(f"Next post scheduled for: {next_post.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Main scheduler loop
    while True:
        try:
            now = datetime.now()
            next_post = datetime.fromisoformat(state.get("next_post_time", next_post.isoformat()))
            
            # Calculate time until next post
            time_until_next = next_post - now
            
            if time_until_next.total_seconds() <= 0:
                # Time to post!
                log_message("=" * 50)
                log_message("SCHEDULED POST TIME REACHED")
                log_message("=" * 50)
                
                success = run_poster_script()
                
                if success:
                    update_dashboard_stats(True)
                    last_post = datetime.now()
                    next_post = calculate_next_post_time(interval_hours)
                    
                    state["last_post_time"] = last_post.isoformat()
                    state["next_post_time"] = next_post.isoformat()
                    state["total_posts"] = state.get("total_posts", 0) + 1
                    save_scheduler_state(state)
                    
                    log_message(f"Post successful! Next post: {next_post.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    log_message("Post failed, will retry at next interval", "ERROR")
                    # Still update next post time to avoid repeated failures
                    next_post = calculate_next_post_time(interval_hours)
                    state["next_post_time"] = next_post.isoformat()
                    save_scheduler_state(state)
            else:
                # Wait and check again
                wait_minutes = min(30, max(1, time_until_next.total_seconds() / 60))
                log_message(f"Next post in {time_until_next.total_seconds() / 3600:.2f} hours - sleeping for {wait_minutes:.0f} minutes")
                time.sleep(wait_minutes * 60)
                continue
                
        except KeyboardInterrupt:
            log_message("Scheduler interrupted by user")
            log_message("Saving state before exit...")
            save_scheduler_state(state)
            log_message("Scheduler stopped gracefully")
            break
        except Exception as e:
            log_message(f"Scheduler error: {e}", "ERROR")
            log_message("Waiting 5 minutes before retry...")
            time.sleep(300)


def main():
    """Main entry point."""
    # Check if poster script exists
    if not POSTER_SCRIPT.exists():
        log_message(f"ERROR: Poster script not found at {POSTER_SCRIPT}", "ERROR")
        sys.exit(1)
    
    try:
        run_scheduler()
    except Exception as e:
        log_message(f"Fatal scheduler error: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
