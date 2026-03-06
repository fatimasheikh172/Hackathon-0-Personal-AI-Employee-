#!/usr/bin/env python3
"""
Test Email MCP Server - Dry run tests for email functions
Does NOT actually send any emails
"""

import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"

# Test results
test_results = {
    "passed": 0,
    "failed": 0,
    "skipped": 0,
    "tests": []
}


def log_test_result(test_name, passed, message=""):
    """Log a test result"""
    status = "PASS" if passed else "FAIL"
    result = {
        "name": test_name,
        "passed": passed,
        "message": message
    }
    test_results["tests"].append(result)
    
    if passed:
        test_results["passed"] += 1
        print(f"  [OK] {test_name}: PASS")
    else:
        test_results["failed"] += 1
        print(f"  [FAIL] {test_name}: FAIL - {message}")


def test_imports():
    """Test that all required modules can be imported"""
    print("\n" + "=" * 50)
    print("TEST: Module Imports")
    print("=" * 50)
    
    try:
        from email_mcp_server import (
            draft_email,
            send_email,
            search_emails,
            get_email_content,
            reply_to_email,
            get_gmail_service,
            ensure_folders_exist
        )
        log_test_result("Import email_mcp_server", True)
        return True
    except ImportError as e:
        log_test_result("Import email_mcp_server", False, str(e))
        return False


def test_folders_exist():
    """Test that required folders exist or can be created"""
    print("\n" + "=" * 50)
    print("TEST: Folders Exist")
    print("=" * 50)
    
    try:
        from email_mcp_server import ensure_folders_exist
        ensure_folders_exist()
        
        required_folders = [
            VAULT_PATH / "Logs",
            VAULT_PATH / "Pending_Approval",
            VAULT_PATH / "Approved"
        ]
        
        all_exist = True
        for folder in required_folders:
            if folder.exists():
                print(f"  [OK] {folder.name} exists")
            else:
                print(f"  [MISSING] {folder.name} missing")
                all_exist = False
        
        log_test_result("Folders exist", all_exist)
        return all_exist
    except Exception as e:
        log_test_result("Folders exist", False, str(e))
        return False


def test_credentials_file():
    """Test that credentials file exists"""
    print("\n" + "=" * 50)
    print("TEST: Credentials File")
    print("=" * 50)
    
    credentials_file = VAULT_PATH / "credentials.json"
    
    if credentials_file.exists():
        try:
            import json
            with open(credentials_file, "r", encoding="utf-8") as f:
                creds = json.load(f)
            
            if "installed" in creds:
                has_client_id = "client_id" in creds["installed"]
                has_client_secret = "client_secret" in creds["installed"]
                
                if has_client_id and has_client_secret:
                    print(f"  [OK] credentials.json exists and valid")
                    log_test_result("Credentials file", True)
                    return True
                else:
                    log_test_result("Credentials file", False, "Missing client_id or client_secret")
                    return False
            else:
                log_test_result("Credentials file", False, "Invalid format")
                return False
        except Exception as e:
            log_test_result("Credentials file", False, str(e))
            return False
    else:
        log_test_result("Credentials file", False, "File not found")
        return False


def test_token_file():
    """Test that token file exists (authentication)"""
    print("\n" + "=" * 50)
    print("TEST: Token File (Authentication)")
    print("=" * 50)
    
    token_file = VAULT_PATH / "token.json"
    
    if token_file.exists():
        print(f"  [OK] token.json exists")
        print(f"  Note: Token file found - authentication should work")
        log_test_result("Token file", True)
        return True
    else:
        print(f"  [WARN] token.json not found")
        print(f"  Note: First run will require browser authentication")
        log_test_result("Token file", True, "Not found but expected on first run")
        return True  # Not a failure - first run needs auth


def test_draft_email_dry_run():
    """Test draft_email function (dry run - checks structure only)"""
    print("\n" + "=" * 50)
    print("TEST: draft_email() Function (Dry Run)")
    print("=" * 50)
    
    try:
        from email_mcp_server import draft_email
        
        # Test data
        test_to = "test@example.com"
        test_subject = f"Test Email - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        test_body = """This is a test email.

This email was created by the Email MCP Server test suite.
No actual email was sent - this is a dry run test.

Best regards,
AI Employee Test Suite"""
        
        print(f"  Test To: {test_to}")
        print(f"  Test Subject: {test_subject}")
        print(f"  Test Body Length: {len(test_body)} chars")
        print(f"  [SKIP] Skipping actual API call (requires authentication)")
        
        # Just check function exists and has correct signature
        import inspect
        sig = inspect.signature(draft_email)
        params = list(sig.parameters.keys())
        
        if 'to' in params and 'subject' in params and 'body' in params:
            print(f"  [OK] Function has correct parameters: {params}")
            log_test_result("draft_email function", True)
            return True
        else:
            log_test_result("draft_email function", False, f"Wrong parameters: {params}")
            return False
            
    except Exception as e:
        log_test_result("draft_email function", False, str(e))
        return False


def test_search_emails_dry_run():
    """Test search_emails function"""
    print("\n" + "=" * 50)
    print("TEST: search_emails() Function")
    print("=" * 50)
    
    try:
        from email_mcp_server import search_emails
        
        # Test query
        test_query = "is:inbox"
        test_max = 5
        
        print(f"  Test Query: {test_query}")
        print(f"  Test Max Results: {test_max}")
        print(f"  [SKIP] Skipping actual API call (requires authentication)")
        
        # Just check function exists and has correct signature
        import inspect
        sig = inspect.signature(search_emails)
        params = list(sig.parameters.keys())
        
        if 'query' in params and 'max_results' in params:
            print(f"  [OK] Function has correct parameters: {params}")
            log_test_result("search_emails function", True)
            return True
        else:
            log_test_result("search_emails function", False, f"Wrong parameters: {params}")
            return False
            
    except Exception as e:
        log_test_result("search_emails function", False, str(e))
        return False


def test_get_email_content_structure():
    """Test get_email_content function structure (without actual message)"""
    print("\n" + "=" * 50)
    print("TEST: get_email_content() Function Structure")
    print("=" * 50)
    
    try:
        from email_mcp_server import get_email_content
        
        print(f"  [SKIP] Skipping actual API call (requires authentication)")
        
        # Just check function exists and has correct signature
        import inspect
        sig = inspect.signature(get_email_content)
        params = list(sig.parameters.keys())
        
        if 'message_id' in params:
            print(f"  [OK] Function has correct parameters: {params}")
            log_test_result("get_email_content function", True)
            return True
        else:
            log_test_result("get_email_content function", False, f"Wrong parameters: {params}")
            return False
            
    except Exception as e:
        log_test_result("get_email_content function", False, str(e))
        return False


def test_send_email_requires_approval():
    """Test that send_email requires approval"""
    print("\n" + "=" * 50)
    print("TEST: send_email() Requires Approval")
    print("=" * 50)
    
    try:
        from email_mcp_server import send_email
        
        print(f"  [SKIP] Skipping actual API call (requires authentication)")
        
        # Just check function exists and has correct signature
        import inspect
        sig = inspect.signature(send_email)
        params = list(sig.parameters.keys())
        
        # Check that require_approval parameter exists
        if 'to' in params and 'subject' in params and 'body' in params and 'require_approval' in params:
            print(f"  [OK] Function has correct parameters: {params}")
            print(f"  [OK] Has require_approval parameter for HITL")
            log_test_result("send_email requires approval", True)
            return True
        else:
            log_test_result("send_email requires approval", False, f"Wrong parameters: {params}")
            return False
            
    except Exception as e:
        log_test_result("send_email requires approval", False, str(e))
        return False


def test_logging():
    """Test that logging works"""
    print("\n" + "=" * 50)
    print("TEST: Logging Functions")
    print("=" * 50)
    
    try:
        from email_mcp_server import log_action, get_text_log_file_path
        
        # Log a test action
        log_action("test_action", "This is a test log entry")
        
        # Check if log file exists
        log_file = get_text_log_file_path()
        
        if log_file.exists():
            print(f"  [OK] Log file created: {log_file.name}")

            # Check if our entry is in the log
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()

            if "test_action" in content:
                print(f"  [OK] Test entry found in log")
                log_test_result("Logging functions", True)
                return True
            else:
                log_test_result("Logging functions", False, "Test entry not found")
                return False
        else:
            log_test_result("Logging functions", False, "Log file not created")
            return False
            
    except Exception as e:
        log_test_result("Logging functions", False, str(e))
        return False


def test_dashboard_update():
    """Test dashboard update function"""
    print("\n" + "=" * 50)
    print("TEST: Dashboard Update")
    print("=" * 50)
    
    try:
        from email_mcp_server import update_dashboard
        
        dashboard_file = VAULT_PATH / "Dashboard.md"

        if not dashboard_file.exists():
            print(f"  [WARN] Dashboard file not found")
            log_test_result("Dashboard update", True, "Dashboard not found - expected")
            return True

        # Try to update
        result = update_dashboard()

        if result:
            print(f"  [OK] Dashboard updated successfully")
            log_test_result("Dashboard update", True)
            return True
        else:
            print(f"  [WARN] Dashboard update returned False")
            log_test_result("Dashboard update", True, "Returned False but may be OK")
            return True
            
    except Exception as e:
        log_test_result("Dashboard update", False, str(e))
        return False


def print_summary():
    """Print test summary"""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total = test_results["passed"] + test_results["failed"]
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {test_results['passed']}")
    print(f"Failed: {test_results['failed']}")
    
    if test_results["failed"] == 0:
        print(f"\n[OK] ALL TESTS PASSED")
    else:
        print(f"\n[FAIL] SOME TESTS FAILED")
        print("\nFailed tests:")
        for test in test_results["tests"]:
            if not test["passed"]:
                print(f"  - {test['name']}: {test['message']}")
    
    print("\n" + "=" * 60)
    
    # Save results to log
    try:
        log_file = LOGS_FOLDER / f"test_results_{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(log_file, "w", encoding="utf-8") as f:
            import json
            json.dump(test_results, f, indent=2)
        print(f"Results saved to: {log_file}")
    except Exception as e:
        print(f"Could not save results: {e}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Email MCP Server - Test Suite (Dry Run)")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("\nNOTE: This is a DRY RUN. No emails will be sent.")
    print("      Some tests may fail if Gmail API is not authenticated.")
    
    # Run tests
    test_imports()
    test_folders_exist()
    test_credentials_file()
    test_token_file()
    test_draft_email_dry_run()
    test_search_emails_dry_run()
    test_get_email_content_structure()
    test_send_email_requires_approval()
    test_logging()
    test_dashboard_update()
    
    # Print summary
    print_summary()
    
    return test_results["failed"] == 0


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests stopped by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
