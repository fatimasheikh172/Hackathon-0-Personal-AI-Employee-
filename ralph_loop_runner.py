#!/usr/bin/env python3
"""
Ralph Loop Runner - Demonstrates Ralph Wiggum Loop with real example
Creates test files and processes them using the loop pattern
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
NEEDS_ACTION_FOLDER = VAULT_PATH / "Needs_Action"
DONE_FOLDER = VAULT_PATH / "Done"

# Import Ralph Wiggum Loop
sys.path.insert(0, str(VAULT_PATH))
from ralph_wiggum import RalphWiggumLoop, TASK_COMPLETE, WORKING


def create_test_files():
    """Create 3 test files in Needs_Action folder for demonstration"""
    print("\n" + "=" * 60)
    print("STEP 1: Creating Test Files")
    print("=" * 60)
    
    NEEDS_ACTION_FOLDER.mkdir(parents=True, exist_ok=True)
    
    test_files = [
        {
            "name": "TEST_RALPH_001.md",
            "content": """---
type: test
priority: high
created: 2026-03-01
---

## Test Task 1
This is test file 1 for Ralph Wiggum Loop demonstration.
"""
        },
        {
            "name": "TEST_RALPH_002.md",
            "content": """---
type: test
priority: medium
created: 2026-03-01
---

## Test Task 2
This is test file 2 for Ralph Wiggum Loop demonstration.
"""
        },
        {
            "name": "TEST_RALPH_003.md",
            "content": """---
type: test
priority: low
created: 2026-03-01
---

## Test Task 3
This is test file 3 for Ralph Wiggum Loop demonstration.
"""
        }
    ]
    
    for test_file in test_files:
        file_path = NEEDS_ACTION_FOLDER / test_file["name"]
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(test_file["content"])
        print(f"  Created: {test_file['name']}")
    
    print(f"\n[OK] Created {len(test_files)} test files in Needs_Action folder")
    return len(test_files)


def run_ralph_demo():
    """Run the Ralph Wiggum Loop demonstration"""
    print("\n" + "=" * 60)
    print("STEP 2: Running Ralph Wiggum Loop")
    print("=" * 60)
    
    # Create loop instance
    loop = RalphWiggumLoop()
    
    # Count initial files
    initial_files = len(list(NEEDS_ACTION_FOLDER.glob("*.md")))
    print(f"\nInitial files in Needs_Action: {initial_files}")
    print(f"Max iterations: 5")
    print("\nStarting loop...\n")
    
    # Run the loop
    result = loop.run_loop(
        task_name="process_test_files",
        work_function=loop.process_needs_action_loop,
        max_iterations=5
    )
    
    # Show final status
    print("\n" + "=" * 60)
    print("STEP 3: Final Status")
    print("=" * 60)
    
    remaining_files = len(list(NEEDS_ACTION_FOLDER.glob("*.md")))
    done_files = len(list(DONE_FOLDER.glob("TEST_RALPH_*.md")))
    
    print(f"\nFiles remaining in Needs_Action: {remaining_files}")
    print(f"Files moved to Done: {done_files}")
    print(f"Loop result: {'SUCCESS' if result else 'FAILED'}")
    
    if result and remaining_files == 0:
        print("\n[OK] ALL TEST FILES PROCESSED SUCCESSFULLY!")
        print("\nRalph Wiggum Loop completed the task 100%!")
    else:
        print("\n[WARN] Some files may remain - check iteration count")
    
    return result


def main():
    """Main function - run complete demonstration"""
    print("=" * 60)
    print("RALPH WIGGUM LOOP DEMONSTRATION")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("\nThis demo will:")
    print("1. Create 3 test files in Needs_Action folder")
    print("2. Run Ralph Wiggum Loop to process all files")
    print("3. Show iteration by iteration progress")
    print("4. Display final completion status")
    print("=" * 60)
    
    # Create test files
    create_test_files()
    
    # Small delay
    time.sleep(1)
    
    # Run Ralph loop
    result = run_ralph_demo()
    
    # Print summary
    print("\n" + "=" * 60)
    print("DEMONSTRATION COMPLETE")
    print("=" * 60)
    
    if result:
        print("\n[OK] Ralph Wiggum Loop successfully processed all files!")
        print("\nKey takeaways:")
        print("  - Loop continues until task is 100% complete")
        print("  - Each iteration processes one file")
        print("  - Progress is logged and tracked")
        print("  - Task moves to Done folder when complete")
    else:
        print("\n[WARN] Loop did not complete - may need more iterations")
    
    print("\n" + "=" * 60)
    
    return result


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nDemonstration stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
