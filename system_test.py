#!/usr/bin/env python3
"""
System Test Suite - Gold Tier Integration Testing
Tests all components and saves results to TEST_REPORT.md

Tests:
1. Odoo connection
2. Gmail watcher
3. WhatsApp watcher
4. File watcher
5. Error recovery (retry_handler)
6. Social media (DRY_RUN)
7. CEO Briefing generation
"""

import os
import sys
import time
import json
import subprocess
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"
TEST_REPORT_FILE = VAULT_PATH / "TEST_REPORT.md"

# Test results storage
test_results = {
    "timestamp": None,
    "total_tests": 0,
    "passed": 0,
    "failed": 0,
    "warnings": 0,
    "tests": []
}


def log_test_result(test_name: str, passed: bool, message: str = "", details: str = ""):
    """Log a test result"""
    test_results["total_tests"] += 1
    if passed:
        test_results["passed"] += 1
        status = "PASS"
    else:
        test_results["failed"] += 1
        status = "FAIL"
    
    result = {
        "name": test_name,
        "passed": passed,
        "message": message,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    test_results["tests"].append(result)
    
    # Use ASCII-safe characters for Windows console compatibility
    status_icon = "[OK]" if passed else "[FAIL]"
    print(f"  {status_icon} {test_name}: {message}")


def check_python_file_syntax(filepath: Path) -> Tuple[bool, str]:
    """Check if a Python file has valid syntax"""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(filepath)],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, "Syntax OK"
        else:
            return False, result.stderr[:200]
    except subprocess.TimeoutExpired:
        return False, "Syntax check timed out"
    except Exception as e:
        return False, str(e)


def check_file_exists(filepath: Path) -> Tuple[bool, str]:
    """Check if a file exists"""
    if filepath.exists():
        return True, f"File exists ({filepath.stat().st_size} bytes)"
    return False, "File not found"


def check_import(module_name: str) -> Tuple[bool, str]:
    """Check if a module can be imported"""
    try:
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            return True, f"Module '{module_name}' found"
        return False, f"Module '{module_name}' not found"
    except Exception as e:
        return False, str(e)


def test_odoo_connection() -> bool:
    """Test 1: Odoo ERP Connection"""
    print("\n" + "=" * 60)
    print("TEST 1: Odoo ERP Connection")
    print("=" * 60)
    
    odoo_script = VAULT_PATH / "odoo_mcp_server.py"
    odoo_config = VAULT_PATH / "odoo_config.py"
    
    # Check files exist
    exists, msg = check_file_exists(odoo_script)
    log_test_result("Odoo MCP Server exists", exists, msg)
    
    exists, msg = check_file_exists(odoo_config)
    log_test_result("Odoo Config exists", exists, msg)
    
    # Check syntax
    if odoo_script.exists():
        valid, msg = check_python_file_syntax(odoo_script)
        log_test_result("Odoo MCP syntax", valid, msg)
    
    # Check environment variables
    odoo_url = os.getenv("ODOO_URL", "")
    odoo_db = os.getenv("ODOO_DB", "")
    odoo_user = os.getenv("ODOO_USERNAME", "")
    odoo_pass = os.getenv("ODOO_PASSWORD", "")
    
    has_url = bool(odoo_url)
    has_db = bool(odoo_db)
    has_user = bool(odoo_user)
    has_pass = bool(odoo_pass)
    
    log_test_result("ODOO_URL configured", has_url, odoo_url if has_url else "Not set")
    log_test_result("ODOO_DB configured", has_db, odoo_db if has_db else "Not set")
    log_test_result("ODOO_USERNAME configured", has_user, odoo_user if has_user else "Not set")
    log_test_result("ODOO_PASSWORD configured", has_pass, "***" if has_pass else "Not set")
    
    # Try to import and test connection
    try:
        sys.path.insert(0, str(VAULT_PATH))
        from odoo_config import test_connection
        
        result = test_connection()
        connected = result.get("success", False)
        log_test_result("Odoo connection test", connected, result.get("message", "No message"))
        
        return connected
    except ImportError as e:
        log_test_result("Odoo import", False, f"Import error: {e}")
        return False
    except Exception as e:
        log_test_result("Odoo connection", False, f"Error: {e}")
        return False


def test_gmail_watcher() -> bool:
    """Test 2: Gmail Watcher"""
    print("\n" + "=" * 60)
    print("TEST 2: Gmail Watcher")
    print("=" * 60)
    
    gmail_script = VAULT_PATH / "gmail_watcher.py"
    credentials_file = VAULT_PATH / "credentials.json"
    token_file = VAULT_PATH / "token.json"
    
    # Check files exist
    exists, msg = check_file_exists(gmail_script)
    log_test_result("Gmail Watcher exists", exists, msg)
    
    exists, msg = check_file_exists(credentials_file)
    log_test_result("Google Credentials exists", exists, msg)
    
    # Check syntax
    if gmail_script.exists():
        valid, msg = check_python_file_syntax(gmail_script)
        log_test_result("Gmail Watcher syntax", valid, msg)
    
    # Check imports
    try:
        from retry_handler import with_retry
        log_test_result("retry_handler import", True, "Available for Gmail Watcher")
    except ImportError as e:
        log_test_result("retry_handler import", False, str(e))
    
    # Check environment
    check_interval = os.getenv("CHECK_INTERVAL", "Not set")
    log_test_result("CHECK_INTERVAL configured", bool(check_interval), check_interval)
    
    # Try to import module
    try:
        sys.path.insert(0, str(VAULT_PATH))
        # Just check if it can be imported
        spec = importlib.util.spec_from_file_location("gmail_watcher", gmail_script)
        if spec:
            log_test_result("Gmail Watcher module spec", True, "Module can be loaded")
        else:
            log_test_result("Gmail Watcher module spec", False, "Cannot create module spec")
        
        return True
    except Exception as e:
        log_test_result("Gmail Watcher import", False, str(e))
        return False


def test_whatsapp_watcher() -> bool:
    """Test 3: WhatsApp Watcher"""
    print("\n" + "=" * 60)
    print("TEST 3: WhatsApp Watcher")
    print("=" * 60)
    
    whatsapp_script = VAULT_PATH / "whatsapp_watcher.py"
    session_path = VAULT_PATH / "whatsapp_session"
    
    # Check files exist
    exists, msg = check_file_exists(whatsapp_script)
    log_test_result("WhatsApp Watcher exists", exists, msg)
    
    # Check session folder
    exists, msg = check_file_exists(session_path)
    log_test_result("WhatsApp Session folder", exists, msg)
    
    # Check syntax
    if whatsapp_script.exists():
        valid, msg = check_python_file_syntax(whatsapp_script)
        log_test_result("WhatsApp Watcher syntax", valid, msg)
    
    # Check Playwright availability
    try:
        from playwright.sync_api import sync_playwright
        log_test_result("Playwright available", True, "Browser automation ready")
    except ImportError as e:
        log_test_result("Playwright available", False, str(e))
    
    # Check environment
    keywords = os.getenv("WHATSAPP_KEYWORDS", "Not set")
    check_interval = os.getenv("WHATSAPP_CHECK_INTERVAL", "Not set")
    log_test_result("WHATSAPP_KEYWORDS", bool(keywords), keywords)
    log_test_result("WHATSAPP_CHECK_INTERVAL", bool(check_interval), check_interval)
    
    return True


def test_file_watcher() -> bool:
    """Test 4: File Watcher"""
    print("\n" + "=" * 60)
    print("TEST 4: File Watcher")
    print("=" * 60)
    
    file_watcher_script = VAULT_PATH / "file_watcher.py"
    incoming_folder = VAULT_PATH / "Incoming"
    needs_action_folder = VAULT_PATH / "Needs_Action"
    
    # Check files exist
    exists, msg = check_file_exists(file_watcher_script)
    log_test_result("File Watcher exists", exists, msg)
    
    # Check folders
    exists, msg = check_file_exists(incoming_folder)
    log_test_result("Incoming folder", exists, msg)
    
    exists, msg = check_file_exists(needs_action_folder)
    log_test_result("Needs_Action folder", exists, msg)
    
    # Check syntax
    if file_watcher_script.exists():
        valid, msg = check_python_file_syntax(file_watcher_script)
        log_test_result("File Watcher syntax", valid, msg)
    
    # Check watchdog availability
    try:
        from watchdog.observers import Observer
        log_test_result("Watchdog available", True, "File monitoring ready")
    except ImportError as e:
        log_test_result("Watchdog available", False, str(e))
    
    return True


def test_error_recovery() -> bool:
    """Test 5: Error Recovery (retry_handler)"""
    print("\n" + "=" * 60)
    print("TEST 5: Error Recovery System")
    print("=" * 60)
    
    retry_handler = VAULT_PATH / "retry_handler.py"
    graceful_deg = VAULT_PATH / "graceful_degradation.py"
    watchdog_adv = VAULT_PATH / "watchdog_advanced.py"
    
    # Check files exist
    exists, msg = check_file_exists(retry_handler)
    log_test_result("retry_handler.py exists", exists, msg)
    
    exists, msg = check_file_exists(graceful_deg)
    log_test_result("graceful_degradation.py exists", exists, msg)
    
    exists, msg = check_file_exists(watchdog_adv)
    log_test_result("watchdog_advanced.py exists", exists, msg)
    
    # Check syntax
    for script, name in [(retry_handler, "retry_handler"), 
                         (graceful_deg, "graceful_degradation"),
                         (watchdog_adv, "watchdog_advanced")]:
        if script.exists():
            valid, msg = check_python_file_syntax(script)
            log_test_result(f"{name} syntax", valid, msg)
    
    # Test retry handler functionality
    try:
        sys.path.insert(0, str(VAULT_PATH))
        from retry_handler import with_retry, TransientError, AuthError, get_retry_stats
        
        log_test_result("retry_handler imports", True, "All classes available")
        
        # Test decorator
        @with_retry(max_attempts=2, base_delay=0.01)
        def test_func():
            return "OK"
        
        result = test_func()
        log_test_result("retry_handler decorator", result == "OK", f"Result: {result}")
        
        # Get stats
        stats = get_retry_stats()
        log_test_result("retry_handler stats", "total_calls" in stats, "Stats available")
        
    except ImportError as e:
        log_test_result("retry_handler imports", False, str(e))
    except Exception as e:
        log_test_result("retry_handler test", False, str(e))
    
    # Test graceful degradation
    try:
        from graceful_degradation import HealthChecker, GracefulDegradationManager
        
        log_test_result("graceful_degradation imports", True, "Classes available")
        
        checker = HealthChecker()
        log_test_result("HealthChecker init", True, "Instance created")
        
    except ImportError as e:
        log_test_result("graceful_degradation imports", False, str(e))
    except Exception as e:
        log_test_result("graceful_degradation test", False, str(e))
    
    return True


def test_social_media() -> bool:
    """Test 6: Social Media (DRY_RUN)"""
    print("\n" + "=" * 60)
    print("TEST 6: Social Media Integration (DRY_RUN)")
    print("=" * 60)
    
    twitter_mgr = VAULT_PATH / "twitter_manager.py"
    linkedin_mgr = VAULT_PATH / "linkedin_manager.py"
    instagram_mgr = VAULT_PATH / "instagram_manager.py"
    social_scheduler = VAULT_PATH / "social_scheduler.py"
    social_generator = VAULT_PATH / "social_content_generator.py"
    
    # Check files exist
    for script, name in [(twitter_mgr, "twitter_manager"),
                         (linkedin_mgr, "linkedin_manager"),
                         (instagram_mgr, "instagram_manager"),
                         (social_scheduler, "social_scheduler"),
                         (social_generator, "social_content_generator")]:
        exists, msg = check_file_exists(script)
        log_test_result(f"{name} exists", exists, msg)
    
    # Check syntax
    for script, name in [(twitter_mgr, "twitter_manager"),
                         (linkedin_mgr, "linkedin_manager"),
                         (instagram_mgr, "instagram_manager")]:
        if script.exists():
            valid, msg = check_python_file_syntax(script)
            log_test_result(f"{name} syntax", valid, msg)
    
    # Check session folders
    for platform in ["twitter_session", "linkedin_session", "instagram_session"]:
        session_path = VAULT_PATH / "sessions" / platform
        exists, msg = check_file_exists(session_path)
        log_test_result(f"{platform} folder", exists, msg)
    
    # Check Social_Content folders
    for folder in ["pending", "posted", "drafts", "failed"]:
        content_path = VAULT_PATH / "Social_Content" / folder
        exists, msg = check_file_exists(content_path)
        log_test_result(f"Social_Content/{folder}", exists, msg)
    
    # Check DRY_RUN setting
    dry_run = os.getenv("DRY_RUN", "false")
    log_test_result("DRY_RUN mode", True, f"DRY_RUN={dry_run}")
    
    # Check credentials
    twitter_email = os.getenv("TWITTER_EMAIL", "")
    linkedin_email = os.getenv("LINKEDIN_EMAIL", "")
    instagram_email = os.getenv("INSTAGRAM_EMAIL", "")
    
    log_test_result("TWITTER_EMAIL configured", bool(twitter_email), "***" if twitter_email else "Not set")
    log_test_result("LINKEDIN_EMAIL configured", bool(linkedin_email), "***" if linkedin_email else "Not set")
    log_test_result("INSTAGRAM_EMAIL configured", bool(instagram_email), "***" if instagram_email else "Not set")
    
    return True


def test_ceo_briefing() -> bool:
    """Test 7: CEO Briefing Generation"""
    print("\n" + "=" * 60)
    print("TEST 7: CEO Briefing Generation")
    print("=" * 60)
    
    briefing_script = VAULT_PATH / "ceo_briefing.py"
    briefings_folder = VAULT_PATH / "Briefings"
    business_goals = VAULT_PATH / "Business_Goals.md"
    
    # Check files exist
    exists, msg = check_file_exists(briefing_script)
    log_test_result("ceo_briefing.py exists", exists, msg)
    
    exists, msg = check_file_exists(briefings_folder)
    log_test_result("Briefings folder", exists, msg)
    
    exists, msg = check_file_exists(business_goals)
    log_test_result("Business_Goals.md", exists, msg)
    
    # Check syntax
    if briefing_script.exists():
        valid, msg = check_python_file_syntax(briefing_script)
        log_test_result("ceo_briefing.py syntax", valid, msg)
    
    # Test Odoo integration in briefing
    try:
        sys.path.insert(0, str(VAULT_PATH))
        
        # Check if odoo_mcp_server can be imported
        from odoo_mcp_server import get_financial_summary, get_invoices
        log_test_result("Odoo MCP functions", True, "Available for briefing")
        
        # Test get_financial_summary (DRY_RUN mode)
        result = get_financial_summary()
        has_summary = result.get("success", False)
        log_test_result("get_financial_summary()", has_summary, result.get("summary", {}))
        
        # Test get_invoices
        result = get_invoices(status="draft", limit=5)
        has_invoices = result.get("success", False)
        log_test_result("get_invoices()", has_invoices, f"Count: {result.get('count', 0)}")
        
    except ImportError as e:
        log_test_result("Odoo MCP import", False, str(e))
    except Exception as e:
        log_test_result("Odoo functions test", False, str(e))
    
    return True


def generate_test_report():
    """Generate TEST_REPORT.md with all results"""
    print("\n" + "=" * 60)
    print("GENERATING TEST REPORT")
    print("=" * 60)
    
    test_results["timestamp"] = datetime.now().isoformat()
    
    # Calculate pass rate
    total = test_results["total_tests"]
    passed = test_results["passed"]
    failed = test_results["failed"]
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    report = f"""# System Test Report - Gold Tier Integration

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Vault Path:** {VAULT_PATH}

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | {total} |
| Passed | {passed} |
| Failed | {failed} |
| Pass Rate | {pass_rate:.1f}% |

---

## Test Results

"""
    
    # Group tests by category
    categories = {
        "Odoo ERP": [],
        "Gmail Watcher": [],
        "WhatsApp Watcher": [],
        "File Watcher": [],
        "Error Recovery": [],
        "Social Media": [],
        "CEO Briefing": []
    }
    
    category_mapping = {
        "Odoo": "Odoo ERP",
        "Gmail": "Gmail Watcher",
        "WhatsApp": "WhatsApp Watcher",
        "File": "File Watcher",
        "retry": "Error Recovery",
        "graceful": "Error Recovery",
        "watchdog": "Error Recovery",
        "Twitter": "Social Media",
        "LinkedIn": "Social Media",
        "Instagram": "Social Media",
        "Social": "Social Media",
        "CEO": "CEO Briefing",
        "Odoo MCP": "Odoo ERP"
    }
    
    for test in test_results["tests"]:
        name = test["name"]
        category = "Other"
        for key, cat in category_mapping.items():
            if key in name:
                category = cat
                break
        
        if category not in categories:
            categories[category] = []
        categories[category].append(test)
    
    # Write results by category
    for category, tests in categories.items():
        if tests:
            report += f"### {category}\n\n"
            report += "| Test | Status | Details |\n"
            report += "|------|--------|--------|\n"
            
            for test in tests:
                status = "✓" if test["passed"] else "✗"
                message = str(test.get("message", ""))[:50] if test.get("message") else ""
                report += f"| {test['name']} | {status} | {message} |\n"
            
            report += "\n"
    
    # Recommendations
    report += """---

## Recommendations

"""
    
    if failed > 0:
        report += "### Issues to Address\n\n"
        for test in test_results["tests"]:
            if not test["passed"]:
                report += f"- **{test['name']}**: {test['message']}\n"
        report += "\n"
    
    report += """### Next Steps

1. Review any failed tests above
2. Ensure all credentials are properly configured in .env
3. Run individual component tests for detailed debugging
4. Schedule regular system tests (recommended: weekly)

---

## Environment Information

"""
    
    report += f"- **Python Version:** {sys.version}\n"
    report += f"- **Vault Path:** {VAULT_PATH}\n"
    report += f"- **DRY_RUN Mode:** {os.getenv('DRY_RUN', 'false')}\n"
    report += f"- **Test Duration:** Completed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    
    report += """
---

*Generated by AI Employee System Test Suite v1.0*
"""
    
    # Save report
    try:
        with open(TEST_REPORT_FILE, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"\nTest report saved to: {TEST_REPORT_FILE}")
        return True
    except Exception as e:
        print(f"\nERROR saving test report: {e}")
        return False


def main():
    """Run all system tests"""
    print("=" * 60)
    print("AI Employee System Test Suite")
    print("Gold Tier Integration Testing")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Test Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Ensure logs folder exists
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
    
    # Run all tests
    print("\n" + "=" * 60)
    print("RUNNING SYSTEM TESTS")
    print("=" * 60)
    
    # Test 1: Odoo Connection
    test_odoo_connection()
    
    # Test 2: Gmail Watcher
    test_gmail_watcher()
    
    # Test 3: WhatsApp Watcher
    test_whatsapp_watcher()
    
    # Test 4: File Watcher
    test_file_watcher()
    
    # Test 5: Error Recovery
    test_error_recovery()
    
    # Test 6: Social Media
    test_social_media()
    
    # Test 7: CEO Briefing
    test_ceo_briefing()
    
    # Generate report
    generate_test_report()
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total = test_results["total_tests"]
    passed = test_results["passed"]
    failed = test_results["failed"]
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\nTotal Tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    
    if failed == 0:
        print("\n[OK] ALL TESTS PASSED!")
    else:
        print(f"\n[WARN] {failed} test(s) failed - review TEST_REPORT.md for details")
    
    print("\n" + "=" * 60)
    print(f"Test Report: {TEST_REPORT_FILE}")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nSystem test stopped by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nFatal error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
