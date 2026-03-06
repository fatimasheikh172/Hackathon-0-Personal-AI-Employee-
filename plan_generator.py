#!/usr/bin/env python3
"""
Plan Generator for AI Employee Vault
Monitors Needs_Action folder and creates Plan.md files for each task.
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Configuration
VAULT_PATH = Path(r"F:\AI_Employee_Vault")
NEEDS_ACTION_PATH = VAULT_PATH / "Needs_Action"
PLANS_PATH = VAULT_PATH / "Plans"
LOGS_PATH = VAULT_PATH / "Logs"
DASHBOARD = VAULT_PATH / "Dashboard.md"
PROCESSED_FILES = VAULT_PATH / ".processed_plans.json"

# Ensure directories exist
PLANS_PATH.mkdir(exist_ok=True)
LOGS_PATH.mkdir(exist_ok=True)
NEEDS_ACTION_PATH.mkdir(exist_ok=True)


def log_message(message: str, level: str = "INFO") -> None:
    """Log a message with timestamp to both console and log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{level}] {message}"
    
    # Handle Windows console encoding issues
    try:
        print(log_entry)
    except UnicodeEncodeError:
        print(log_entry.encode('ascii', errors='replace').decode('ascii'))
    
    # Write to log file
    log_file = LOGS_PATH / f"plan_generator_{datetime.now().strftime('%Y-%m-%d')}.log"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_entry + "\n")


def load_env() -> dict:
    """Load environment variables from .env file."""
    load_dotenv(VAULT_PATH / ".env")
    return {
        "vault_path": os.getenv("VAULT_PATH", str(VAULT_PATH)),
    }


def load_processed_files() -> set:
    """Load set of already processed files."""
    if PROCESSED_FILES.exists():
        try:
            with open(PROCESSED_FILES, "r", encoding="utf-8") as f:
                data = json.load(f)
            return set(data.get("processed", []))
        except Exception as e:
            log_message(f"Error loading processed files: {e}", "WARNING")
    return set()


def save_processed_file(filename: str) -> None:
    """Save a processed file to the tracking file."""
    processed = load_processed_files()
    processed.add(filename)
    try:
        with open(PROCESSED_FILES, "w", encoding="utf-8") as f:
            json.dump({"processed": list(processed)}, f, indent=2)
    except Exception as e:
        log_message(f"Error saving processed file: {e}", "ERROR")


def parse_yaml_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown file."""
    frontmatter = {}
    lines = content.split("\n")
    
    if not lines[0].strip() == "---":
        return frontmatter
    
    in_frontmatter = False
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()
    
    return frontmatter


def detect_priority(content: str, frontmatter: dict) -> tuple:
    """
    Detect priority level based on content.
    Returns (priority_level, reason)
    """
    # Combine subject and content for analysis
    text_to_analyze = ""
    
    if "subject" in frontmatter:
        text_to_analyze += frontmatter["subject"].lower() + " "
    
    text_to_analyze += content.lower()
    
    # HIGH priority keywords
    high_keywords = ["urgent", "asap", "payment", "invoice", "important", "critical", "emergency"]
    for keyword in high_keywords:
        if keyword in text_to_analyze:
            return ("HIGH", f"Contains priority keyword: {keyword}")
    
    # MEDIUM priority keywords
    medium_keywords = ["follow up", "follow-up", "reminder", "update", "review", "check"]
    for keyword in medium_keywords:
        if keyword in text_to_analyze:
            return ("MEDIUM", f"Contains priority keyword: {keyword}")
    
    # LOW priority (default)
    return ("LOW", "No priority keywords detected")


def requires_approval(content: str, frontmatter: dict) -> bool:
    """Check if the task requires human approval."""
    text_to_analyze = ""
    
    if "subject" in frontmatter:
        text_to_analyze += frontmatter["subject"].lower() + " "
    
    text_to_analyze += content.lower()
    
    approval_keywords = ["payment", "invoice", "urgent", "asap"]
    for keyword in approval_keywords:
        if keyword in text_to_analyze:
            return True
    
    return False


def generate_objective(frontmatter: dict, content: str) -> str:
    """Generate a clear one-line objective description."""
    task_type = frontmatter.get("type", "task")
    
    if task_type == "email":
        sender = frontmatter.get("from", "unknown sender")
        subject = frontmatter.get("subject", "no subject")
        return f"Process email from {sender} regarding: {subject}"
    elif task_type == "file_drop":
        return "Process and handle the dropped file"
    elif task_type == "whatsapp":
        return "Process WhatsApp message and respond appropriately"
    else:
        return "Review and process the incoming task"


def extract_notes(content: str) -> str:
    """Extract relevant notes from the content."""
    notes = []
    
    # Look for action items
    if "## Actions Needed" in content:
        actions_section = content.split("## Actions Needed")[1]
        notes.append(f"Action items found in original file")
    
    # Look for email content
    if "## Email Content" in content:
        notes.append("Email content available for review")
    
    return "\n".join(notes) if notes else "No specific notes extracted"


def create_plan(source_file: Path, content: str) -> Path:
    """
    Create a Plan.md file for the given source file.
    Returns path to created plan file.
    """
    # Parse frontmatter
    frontmatter = parse_yaml_frontmatter(content)
    
    # Detect type
    task_type = frontmatter.get("type", "task")
    
    # Detect priority
    priority, priority_reason = detect_priority(content, frontmatter)
    
    # Check approval requirement
    needs_approval = requires_approval(content, frontmatter)
    
    # Generate objective
    objective = generate_objective(frontmatter, content)
    
    # Extract notes
    notes = extract_notes(content)
    
    # Calculate due date (24 hours from now)
    due_date = datetime.now() + timedelta(hours=24)
    
    # Create plan content
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    plan_name = f"PLAN_{source_file.stem}.md"
    plan_path = PLANS_PATH / plan_name
    
    plan_content = f"""---
created: {current_time}
source_file: {source_file.name}
type: {task_type}
priority: {priority.lower()}
status: pending
due_date: {due_date.strftime('%Y-%m-%d %H:%M:%S')}
---

## Objective
{objective}

## Steps
- [ ] Step 1: Review the incoming request
- [ ] Step 2: Determine appropriate response
- [ ] Step 3: Draft response or action
- [ ] Step 4: Get human approval if needed
- [ ] Step 5: Execute approved action
- [ ] Step 6: Log completion
- [ ] Step 7: Move to Done folder

## Priority
- Level: {priority}
- Reason: {priority_reason}

## Approval Required
{"YES" if needs_approval else "NO"}

## Notes
{notes}
"""
    
    # Write plan file
    with open(plan_path, "w", encoding="utf-8") as f:
        f.write(plan_content)
    
    log_message(f"Created plan: {plan_name}")
    
    return plan_path, priority, needs_approval


def update_dashboard(plan_priority: str = None) -> None:
    """Update Dashboard.md with plan creation info."""
    try:
        if not DASHBOARD.exists():
            log_message("Dashboard.md not found, skipping update", "WARNING")
            return
        
        with open(DASHBOARD, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Count plans
        total_plans = len(list(PLANS_PATH.glob("PLAN_*.md")))
        
        # Count by priority
        high_priority = 0
        pending = 0
        completed = 0
        
        for plan_file in PLANS_PATH.glob("PLAN_*.md"):
            with open(plan_file, "r", encoding="utf-8") as f:
                plan_content = f.read()
            
            if "priority: high" in plan_content.lower():
                high_priority += 1
            if "status: pending" in plan_content.lower():
                pending += 1
            if "status: completed" in plan_content.lower():
                completed += 1
        
        # Check if Plans Status section exists
        if "## Plans Status" in content:
            # Update existing section
            lines = content.split("\n")
            new_lines = []
            in_plans_section = False
            
            for line in lines:
                if line.strip() == "## Plans Status":
                    in_plans_section = True
                    new_lines.append(line)
                    continue
                
                if in_plans_section:
                    if line.startswith("## ") and "Plans" not in line:
                        in_plans_section = False
                        new_lines.append(line)
                    elif "- Total Plans Created:" in line:
                        new_lines.append(f"- Total Plans Created: {total_plans}")
                    elif "- High Priority Plans:" in line:
                        new_lines.append(f"- High Priority Plans: {high_priority}")
                    elif "- Pending Plans:" in line:
                        new_lines.append(f"- Pending Plans: {pending}")
                    elif "- Completed Plans:" in line:
                        new_lines.append(f"- Completed Plans: {completed}")
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            
            content = "\n".join(new_lines)
        else:
            # Add new section before the last ---
            plans_section = f"""
## Plans Status
- Total Plans Created: {total_plans}
- High Priority Plans: {high_priority}
- Pending Plans: {pending}
- Completed Plans: {completed}
"""
            if content.endswith("\n"):
                content = content.rstrip() + plans_section
            else:
                content = content + "\n" + plans_section
        
        with open(DASHBOARD, "w", encoding="utf-8") as f:
            f.write(content)
        
        log_message("Dashboard.md updated with plans status")
        
    except Exception as e:
        log_message(f"Error updating dashboard: {e}", "ERROR")


def process_needs_action_folder() -> int:
    """
    Process all .md files in Needs_Action folder.
    Returns number of plans created.
    """
    processed = load_processed_files()
    plans_created = 0
    
    # Find all .md files in Needs_Action
    md_files = list(NEEDS_ACTION_PATH.glob("*.md"))
    
    if not md_files:
        log_message("No .md files found in Needs_Action folder")
        return 0
    
    for md_file in md_files:
        # Skip already processed files
        if md_file.name in processed:
            log_message(f"Skipping already processed: {md_file.name}")
            continue
        
        log_message(f"Processing: {md_file.name}")
        
        try:
            # Read file content
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Create plan
            plan_path, priority, needs_approval = create_plan(md_file, content)
            
            # Mark as processed
            save_processed_file(md_file.name)
            
            # Update dashboard
            update_dashboard(priority)
            
            plans_created += 1
            
            log_message(f"Plan created successfully: {plan_path.name} (Priority: {priority})")
            
        except Exception as e:
            log_message(f"Error processing {md_file.name}: {e}", "ERROR")
    
    return plans_created


def run_plan_generator() -> None:
    """Main function to run the plan generator."""
    log_message("=" * 50)
    log_message("PLAN GENERATOR STARTED")
    log_message("=" * 50)
    
    # Load configuration
    env = load_env()
    log_message(f"Vault path: {env['vault_path']}")
    log_message(f"Monitoring: {NEEDS_ACTION_PATH}")
    log_message(f"Plans output: {PLANS_PATH}")
    
    # Initial scan
    log_message("Running initial scan...")
    plans_created = process_needs_action_folder()
    log_message(f"Initial scan complete. Plans created: {plans_created}")
    
    # Continuous monitoring
    log_message("Starting continuous monitoring (60 second intervals)...")
    log_message("Press Ctrl+C to stop")
    
    while True:
        try:
            time.sleep(60)
            
            log_message("Checking for new files...")
            plans_created = process_needs_action_folder()
            
            if plans_created > 0:
                log_message(f"Created {plans_created} new plan(s)")
            else:
                log_message("No new files to process")
                
        except KeyboardInterrupt:
            log_message("Plan generator stopped by user")
            break
        except Exception as e:
            log_message(f"Error in monitoring loop: {e}", "ERROR")
            time.sleep(60)


def main():
    """Main entry point."""
    try:
        run_plan_generator()
    except Exception as e:
        log_message(f"Fatal error: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
