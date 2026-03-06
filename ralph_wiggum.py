#!/usr/bin/env python3
"""
Ralph Wiggum Loop - Task completion loop pattern
Keeps working on tasks until they are 100% complete
"""

import os
import sys
import re
import json
import shutil
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
ACTIVE_TASKS_FOLDER = VAULT_PATH / "Active_Tasks"
DONE_FOLDER = VAULT_PATH / "Done"
NEEDS_ACTION_FOLDER = VAULT_PATH / "Needs_Action"
PLANS_FOLDER = VAULT_PATH / "Plans"
LOGS_FOLDER = VAULT_PATH / "Logs"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"

# Loop constants
TASK_COMPLETE = "TASK_COMPLETE"
WORKING = "WORKING"
TASK_FAILED = "TASK_FAILED"

# Loop statistics
loop_stats = {
    "active_loops": 0,
    "completed_today": 0,
    "failed_today": 0,
    "total_iterations": 0,
    "loops_run": 0
}


def get_log_file_path():
    """Get log file path with current date"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return LOGS_FOLDER / f"ralph_wiggum_{date_str}.log"


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, ACTIVE_TASKS_FOLDER, DONE_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)


def log_iteration(task_name, iteration, max_iterations, status, message=""):
    """Log an iteration to the log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {task_name} - Iteration {iteration}/{max_iterations} - {status}: {message}\n"
    
    try:
        with open(get_log_file_path(), "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"ERROR writing log: {e}")
    
    # Print to console
    print(f"[{timestamp}] {task_name} - Iteration {iteration}/{max_iterations} - {status}")


def log_action(action_type, details, success=True):
    """Log a general action"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "[OK]" if success else "[ERROR]"
    log_entry = f"[{timestamp}] {status} {action_type}: {details}\n"
    
    try:
        with open(get_log_file_path(), "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"ERROR writing log: {e}")


class RalphWiggumLoop:
    """
    Ralph Wiggum Loop - Keeps working until task is 100% complete
    
    Usage:
        loop = RalphWiggumLoop()
        loop.create_task("my_task", "Do something important")
        loop.run_loop("my_task", work_function, max_iterations=10)
    """
    
    def __init__(self):
        """Initialize Ralph Wiggum Loop"""
        ensure_folders_exist()
        self.task_files = {}
    
    def create_task(self, task_name, prompt, max_iterations=10):
        """
        Create a new task file
        
        Args:
            task_name: Name of the task (used for filename)
            prompt: Task description/prompt
            max_iterations: Maximum iterations before failing (default: 10)
        
        Returns:
            Path to task file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        task_filename = f"{task_name.replace(' ', '_').upper()}.md"
        task_path = ACTIVE_TASKS_FOLDER / task_filename
        
        task_content = f"""---
task_name: {task_name}
prompt: {prompt[:200]}
created: {timestamp}
max_iterations: {max_iterations}
current_iteration: 0
status: active
completion_promise: TASK_COMPLETE
---

## Task Description

{prompt}

---

## Progress Log

- [{timestamp}] Task created
- [{timestamp}] Starting iteration loop

---

## Iteration History

"""
        
        try:
            ACTIVE_TASKS_FOLDER.mkdir(parents=True, exist_ok=True)
            with open(task_path, "w", encoding="utf-8") as f:
                f.write(task_content)
            
            self.task_files[task_name] = task_path
            loop_stats["active_loops"] += 1
            
            log_action("task_created", f"Created task: {task_name}")
            
            return task_path
            
        except Exception as e:
            log_action("task_create_error", f"Failed to create task {task_name}: {e}", success=False)
            return None
    
    def check_completion(self, task_name):
        """
        Check if a task is complete
        
        Args:
            task_name: Name of the task to check
        
        Returns:
            True if complete, False if not
        """
        task_filename = f"{task_name.replace(' ', '_').upper()}.md"
        task_path = ACTIVE_TASKS_FOLDER / task_filename
        
        # Check if task file exists
        if not task_path.exists():
            # Check if done file exists
            done_filename = f"DONE_{task_name.replace(' ', '_').upper()}.md"
            done_path = DONE_FOLDER / done_filename
            return done_path.exists()
        
        try:
            with open(task_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Check frontmatter for status
            frontmatter = self._parse_frontmatter(content)
            status = frontmatter.get("status", "").lower()
            
            if status == "complete":
                return True
            
            # Check for TASK_COMPLETE in content
            if "TASK_COMPLETE" in content and status == "complete":
                return True
            
            return False
            
        except Exception as e:
            log_action("completion_check_error", f"Error checking {task_name}: {e}", success=False)
            return False
    
    def _parse_frontmatter(self, content):
        """Parse YAML frontmatter from markdown content"""
        frontmatter = {}
        
        match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
        if match:
            yaml_content = match.group(1)
            for line in yaml_content.split("\n"):
                if ":" in line:
                    key, value = line.split(":", 1)
                    value = value.strip().strip('"').strip("'")
                    frontmatter[key.strip()] = value
        
        return frontmatter
    
    def _update_task_file(self, task_name, updates):
        """Update task file with new values"""
        task_filename = f"{task_name.replace(' ', '_').upper()}.md"
        task_path = ACTIVE_TASKS_FOLDER / task_filename
        
        if not task_path.exists():
            return False
        
        try:
            with open(task_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Update frontmatter values
            for key, value in updates.items():
                pattern = rf"^{key}:.*$"
                replacement = f"{key}: {value}"
                content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
            
            # Add to progress log
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            progress_entry = f"- [{timestamp}] {updates.get('log_message', 'Iteration completed')}\n"
            
            # Find progress log section and add entry
            if "## Progress Log" in content:
                content = content.replace("## Progress Log", f"## Progress Log\n{progress_entry}")
            
            with open(task_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            return True
            
        except Exception as e:
            log_action("task_update_error", f"Failed to update {task_name}: {e}", success=False)
            return False
    
    def run_loop(self, task_name, work_function, max_iterations=10):
        """
        Run the Ralph Wiggum Loop
        
        Args:
            task_name: Name of the task
            work_function: Function to call each iteration (must return TASK_COMPLETE or WORKING)
            max_iterations: Maximum iterations before failing
        
        Returns:
            True if completed successfully, False if failed
        """
        print(f"\n{'='*60}")
        print(f"RALPH WIGGUM LOOP: {task_name}")
        print(f"{'='*60}")
        print(f"Max Iterations: {max_iterations}")
        print(f"Starting loop...\n")
        
        # Create task if not exists
        if task_name not in self.task_files:
            self.create_task(task_name, f"Automated task: {task_name}", max_iterations)
        
        iteration = 0
        completed = False
        
        while iteration < max_iterations:
            iteration += 1
            loop_stats["total_iterations"] += 1
            
            try:
                # Run work function
                print(f"Iteration {iteration}/{max_iterations} - Status: working")
                log_iteration(task_name, iteration, max_iterations, "working")
                
                result = work_function()
                
                # Update task file
                self._update_task_file(task_name, {
                    "current_iteration": iteration,
                    "log_message": f"Iteration {iteration} completed - Result: {result}"
                })
                
                # Check result
                if result == TASK_COMPLETE:
                    print(f"Iteration {iteration}/{max_iterations} - Status: complete")
                    log_iteration(task_name, iteration, max_iterations, "complete", "Task finished successfully")
                    
                    # Mark task as complete
                    self._update_task_file(task_name, {
                        "status": "complete",
                        "log_message": f"TASK_COMPLETE at iteration {iteration}"
                    })
                    
                    # Move to Done folder
                    self._move_task_to_done(task_name)
                    
                    completed = True
                    loop_stats["completed_today"] += 1
                    loop_stats["loops_run"] += 1
                    loop_stats["active_loops"] -= 1
                    
                    print(f"\n[OK] TASK_COMPLETE - {task_name} finished in {iteration} iterations")
                    break
                    
                elif result == WORKING:
                    print(f"Iteration {iteration}/{max_iterations} - Status: working (continuing)")
                    # Continue loop
                    
                else:
                    print(f"Iteration {iteration}/{max_iterations} - Status: unknown result '{result}'")
                    # Continue loop
                    
            except Exception as e:
                print(f"Iteration {iteration}/{max_iterations} - Status: error - {e}")
                log_iteration(task_name, iteration, max_iterations, "error", str(e))
                
                self._update_task_file(task_name, {
                    "log_message": f"Iteration {iteration} failed: {e}"
                })
        
        # Check if max iterations reached without completion
        if not completed:
            print(f"\n[WARN] Max iterations ({max_iterations}) reached without completion")
            log_action("loop_max_iterations", f"Task {task_name} reached max iterations", success=False)
            
            self._update_task_file(task_name, {
                "status": "failed",
                "log_message": f"TASK_FAILED - Max iterations reached at {max_iterations}"
            })
            
            loop_stats["failed_today"] += 1
            loop_stats["loops_run"] += 1
            loop_stats["active_loops"] -= 1
            
            return False
        
        # Update dashboard
        self._update_dashboard()
        
        return True
    
    def _move_task_to_done(self, task_name):
        """Move completed task to Done folder"""
        task_filename = f"{task_name.replace(' ', '_').upper()}.md"
        task_path = ACTIVE_TASKS_FOLDER / task_filename
        done_filename = f"DONE_{task_filename}"
        done_path = DONE_FOLDER / done_filename
        
        if task_path.exists():
            try:
                shutil.move(str(task_path), str(done_path))
                if task_name in self.task_files:
                    del self.task_files[task_name]
                log_action("task_completed", f"Moved {task_name} to Done folder")
                return True
            except Exception as e:
                log_action("task_move_error", f"Failed to move {task_name}: {e}", success=False)
        return False
    
    def process_needs_action_loop(self):
        """
        Work function that processes ALL files in Needs_Action folder
        
        Returns:
            TASK_COMPLETE when folder is empty
            WORKING if files still remain
        """
        if not NEEDS_ACTION_FOLDER.exists():
            log_action("process_na", "Needs_Action folder does not exist")
            return TASK_COMPLETE
        
        # Count files
        files = list(NEEDS_ACTION_FOLDER.glob("*.md"))
        file_count = len(files)
        
        if file_count == 0:
            log_action("process_na", "Needs_Action folder is empty - TASK_COMPLETE")
            return TASK_COMPLETE
        
        # Process one file per iteration
        processed = 0
        for file_path in files:
            try:
                # Read content
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Log action
                log_action("process_na_file", f"Processing {file_path.name}")
                
                # Move to Done
                done_path = DONE_FOLDER / file_path.name
                shutil.move(str(file_path), str(done_path))
                
                processed += 1
                print(f"  Processed: {file_path.name}")
                
                # Process one file per iteration for demonstration
                break
                
            except Exception as e:
                log_action("process_na_error", f"Error processing {file_path.name}: {e}", success=False)
        
        remaining = len(list(NEEDS_ACTION_FOLDER.glob("*.md")))
        
        if remaining > 0:
            log_action("process_na", f"Processed {processed} files, {remaining} remaining - WORKING")
            return WORKING
        else:
            log_action("process_na", f"All files processed - TASK_COMPLETE")
            return TASK_COMPLETE
    
    def generate_plans_loop(self):
        """
        Work function that generates plans for ALL files in Needs_Action
        
        Returns:
            TASK_COMPLETE when all files have plans
            WORKING if any file is missing a plan
        """
        if not NEEDS_ACTION_FOLDER.exists():
            return TASK_COMPLETE
        
        if not PLANS_FOLDER.exists():
            PLANS_FOLDER.mkdir(parents=True, exist_ok=True)
        
        # Check each file in Needs_Action
        files = list(NEEDS_ACTION_FOLDER.glob("*.md"))
        
        if not files:
            return TASK_COMPLETE
        
        for file_path in files:
            # Check if plan exists
            plan_filename = f"PLAN_{file_path.name}"
            plan_path = PLANS_FOLDER / plan_filename
            
            if not plan_path.exists():
                # Create plan
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Create simple plan
                    plan_content = f"""---
type: plan
source_file: {file_path.name}
priority: medium
created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
status: active
---

## Plan for {file_path.name}

### Steps
1. Review source file content
2. Identify required actions
3. Execute actions
4. Mark complete

### Notes
Auto-generated plan

"""
                    with open(plan_path, "w", encoding="utf-8") as f:
                        f.write(plan_content)
                    
                    print(f"  Created plan: {plan_filename}")
                    log_action("generate_plan", f"Created plan for {file_path.name}")
                    
                    # Create one plan per iteration
                    return WORKING
                    
                except Exception as e:
                    log_action("generate_plan_error", f"Error creating plan for {file_path.name}: {e}", success=False)
        
        # All files have plans
        return TASK_COMPLETE
    
    def _update_dashboard(self):
        """Update Dashboard.md with loop status"""
        try:
            if not DASHBOARD_FILE.exists():
                return False
            
            with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            
            avg_iterations = 0
            if loop_stats["loops_run"] > 0:
                avg_iterations = loop_stats["total_iterations"] / loop_stats["loops_run"]
            
            ralph_section = f"""## Ralph Wiggum Status
- Active Loops: {loop_stats['active_loops']}
- Completed Loops Today: {loop_stats['completed_today']}
- Failed Loops Today: {loop_stats['failed_today']}
- Average Iterations: {avg_iterations:.1f}
"""
            
            if "## Ralph Wiggum Status" in content:
                pattern = r"## Ralph Wiggum Status.*?(?=## |\Z)"
                content = re.sub(pattern, ralph_section, content, flags=re.DOTALL)
            else:
                if "---" in content:
                    parts = content.rsplit("---", 1)
                    content = parts[0] + ralph_section + "\n---" + parts[1] if len(parts) > 1 else content + "\n" + ralph_section
                else:
                    content = content + "\n" + ralph_section
            
            with open(DASHBOARD_FILE, "w", encoding="utf-8") as f:
                f.write(content)
            
            return True
        except Exception as e:
            log_action("dashboard_error", f"Failed to update dashboard: {e}", success=False)
            return False


def main():
    """Main function - demonstrate Ralph Wiggum Loop"""
    print("=" * 60)
    print("Ralph Wiggum Loop - AI Employee System")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Active Tasks Folder: {ACTIVE_TASKS_FOLDER}")
    print("=" * 60)
    
    # Ensure folders exist
    ensure_folders_exist()
    
    # Create loop instance
    loop = RalphWiggumLoop()
    
    print("\nRalph Wiggum Loop ready.")
    print("\nUsage:")
    print("  loop = RalphWiggumLoop()")
    print("  loop.run_loop('task_name', work_function, max_iterations=10)")
    print("\nAvailable work functions:")
    print("  - loop.process_needs_action_loop()")
    print("  - loop.generate_plans_loop()")
    
    return loop


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nRalph Wiggum Loop stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
