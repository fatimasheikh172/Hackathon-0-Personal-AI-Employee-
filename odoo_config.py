#!/usr/bin/env python3
"""
Odoo Configuration Module
Centralized configuration and connection testing for Odoo MCP Server
"""

import os
import xmlrpc.client
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration from .env
ODOO_URL = os.getenv("ODOO_URL", "http://localhost:8069")
ODOO_DB = os.getenv("ODOO_DB", "")
ODOO_USERNAME = os.getenv("ODOO_USERNAME", "")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD", "")

# Vault paths
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"
PENDING_APPROVAL_FOLDER = VAULT_PATH / "Pending_Approval"


def get_odoo_url():
    """Get Odoo URL from environment"""
    return ODOO_URL


def get_odoo_db():
    """Get Odoo database name from environment"""
    return ODOO_DB


def get_odoo_credentials():
    """Get Odoo credentials from environment"""
    return {
        "username": ODOO_USERNAME,
        "password": ODOO_PASSWORD,
        "database": ODOO_DB
    }


def test_connection():
    """
    Test connection to Odoo server
    
    Returns:
        dict: {
            "success": bool,
            "uid": int or None,
            "error": str or None,
            "message": str
        }
    """
    try:
        # Connect to Odoo common endpoint to get UID
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        
        if uid:
            # Get user info using execute_kw on object endpoint
            # Note: read() returns a list of records, not a single dict
            models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
            user_data = models.execute_kw(ODOO_DB, uid, ODOO_PASSWORD, "res.users", "read", [[uid]])
            user_name = user_data[0].get("name", "Unknown") if user_data and len(user_data) > 0 else "Unknown"
            
            return {
                "success": True,
                "uid": uid,
                "error": None,
                "message": f"Connected to Odoo as '{user_name}' (UID: {uid})",
                "database": ODOO_DB,
                "url": ODOO_URL
            }
        else:
            return {
                "success": False,
                "uid": None,
                "error": "Authentication failed - invalid credentials",
                "message": "Authentication failed. Please check your username and password."
            }
            
    except xmlrpc.client.Fault as e:
        return {
            "success": False,
            "uid": None,
            "error": f"XML-RPC Fault: {e.faultString}",
            "message": f"Odoo server error: {e.faultString}"
        }
    except ConnectionRefusedError:
        return {
            "success": False,
            "uid": None,
            "error": "Connection refused",
            "message": f"Cannot connect to Odoo at {ODOO_URL}. Is the server running?"
        }
    except Exception as e:
        return {
            "success": False,
            "uid": None,
            "error": str(e),
            "message": f"Connection error: {str(e)}"
        }


def get_server_proxy():
    """
    Get authenticated Odoo server proxy
    
    Returns:
        tuple: (success, proxy or None, uid or None, error or None)
    """
    try:
        common = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
        uid = common.authenticate(ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD, {})
        
        if not uid:
            return False, None, None, "Authentication failed"
        
        # Get object proxy for API calls
        models = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")
        
        return True, models, uid, None
        
    except Exception as e:
        return False, None, None, str(e)


def ensure_folders():
    """Ensure required folders exist"""
    LOGS_FOLDER.mkdir(parents=True, exist_ok=True)
    PENDING_APPROVAL_FOLDER.mkdir(parents=True, exist_ok=True)


if __name__ == "__main__":
    # Test connection when run directly
    print("Testing Odoo Connection...")
    print(f"URL: {ODOO_URL}")
    print(f"Database: {ODOO_DB}")
    print(f"Username: {ODOO_USERNAME}")
    print("-" * 50)
    
    result = test_connection()
    
    if result["success"]:
        print(f"[OK] SUCCESS: {result['message']}")
    else:
        print(f"[FAIL] FAILED: {result['message']}")
        print(f"  Error: {result['error']}")
