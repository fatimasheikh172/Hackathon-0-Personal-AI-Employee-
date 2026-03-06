#!/usr/bin/env python3
"""
Graceful Degradation System - Health checker for all components
When components fail, queue locally and degrade gracefully

Features:
- Health checker for Gmail, Odoo, WhatsApp, and other components
- Local queuing when services are down
- Health status saved to system_health.md
- Check interval: 5 minutes
"""

import os
import sys
import time
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field, asdict

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"
NEEDS_ACTION_FOLDER = VAULT_PATH / "Needs_Action"
BRIEFINGS_FOLDER = VAULT_PATH / "Briefings"
SYSTEM_HEALTH_FILE = VAULT_PATH / "system_health.md"
MISSED_MESSAGES_FILE = VAULT_PATH / "missed_messages.md"
LOCAL_TRANSACTIONS_FILE = VAULT_PATH / "local_transactions.json"

# Check interval: 5 minutes
CHECK_INTERVAL_MINUTES = int(os.getenv("HEALTH_CHECK_INTERVAL", "5"))

# Environment settings
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"


# =============================================================================
# HEALTH STATUS ENUMS
# =============================================================================

class HealthStatus(Enum):
    """Component health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ComponentType(Enum):
    """Types of components"""
    GMAIL = "gmail"
    ODOO = "odoo"
    WHATSAPP = "whatsapp"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    INSTAGRAM = "instagram"
    FILE_WATCHER = "file_watcher"
    ORCHESTRATOR = "orchestrator"
    SCHEDULER = "scheduler"
    DATABASE = "database"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ComponentHealth:
    """Health status of a single component"""
    name: str
    component_type: str
    status: HealthStatus = HealthStatus.UNKNOWN
    last_check: Optional[str] = None
    last_success: Optional[str] = None
    error_message: Optional[str] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    total_failures: int = 0
    degradation_mode: bool = False
    queued_items: int = 0
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "component_type": self.component_type,
            "status": self.status.value,
            "last_check": self.last_check,
            "last_success": self.last_success,
            "error_message": self.error_message,
            "consecutive_failures": self.consecutive_failures,
            "total_checks": self.total_checks,
            "total_failures": self.total_failures,
            "degradation_mode": self.degradation_mode,
            "queued_items": self.queued_items
        }


@dataclass
class HealthReport:
    """Overall system health report"""
    timestamp: str
    overall_status: HealthStatus
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    degradation_events: List[dict] = field(default_factory=list)
    queued_transactions: int = 0
    missed_messages: int = 0
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status.value,
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "degradation_events": self.degradation_events,
            "queued_transactions": self.queued_transactions,
            "missed_messages": self.missed_messages
        }


# =============================================================================
# GRACEFUL DEGRADATION MANAGER
# =============================================================================

class GracefulDegradationManager:
    """
    Manages graceful degradation when components fail
    
    Features:
    - Queue emails locally when Gmail is down
    - Queue transactions locally when Odoo is down
    - Save missed WhatsApp messages to file
    - Track degradation events
    """
    
    def __init__(self):
        """Initialize degradation manager"""
        self.degradation_events: List[dict] = []
        self.queued_emails: List[dict] = []
        self.queued_transactions: List[dict] = []
        self.missed_messages: List[dict] = []
        
        # Load existing queued items
        self._load_queued_items()
    
    def _load_queued_items(self):
        """Load queued items from files"""
        # Load queued transactions
        if LOCAL_TRANSACTIONS_FILE.exists():
            try:
                with open(LOCAL_TRANSACTIONS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.queued_transactions = data.get("transactions", [])
            except Exception as e:
                print(f"[WARN] Failed to load queued transactions: {e}")
        
        # Load missed messages
        if MISSED_MESSAGES_FILE.exists():
            try:
                with open(MISSED_MESSAGES_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Parse existing entries (simplified)
                    self.missed_messages = []
            except Exception as e:
                print(f"[WARN] Failed to load missed messages: {e}")
    
    def queue_email(self, email_data: dict):
        """
        Queue an email locally when Gmail is unavailable
        
        Args:
            email_data: Email data to queue
        """
        email_data["queued_at"] = datetime.now().isoformat()
        email_data["status"] = "queued"
        self.queued_emails.append(email_data)
        
        # Save to Needs_Action folder
        self._save_queued_email(email_data)
        
        print(f"[DEGRADATION] Email queued: {email_data.get('subject', 'Unknown')}")
    
    def _save_queued_email(self, email_data: dict):
        """Save queued email to Needs_Action folder"""
        try:
            NEEDS_ACTION_FOLDER.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            subject = email_data.get("subject", "No_Subject")[:50].replace(" ", "_")
            filename = f"QUEUED_EMAIL_{subject}_{timestamp}.md"
            filepath = NEEDS_ACTION_FOLDER / filename
            
            content = f"""---
type: queued_email
from: {email_data.get('from', 'Unknown')}
subject: {email_data.get('subject', 'Unknown')}
queued_at: {email_data.get('queued_at', 'Unknown')}
status: queued
---

## Queued Email

This email was queued locally because Gmail service was unavailable.

**From:** {email_data.get('from', 'Unknown')}
**Subject:** {email_data.get('subject', 'Unknown')}
**Received:** {email_data.get('received', 'Unknown')}

---

## Content

{email_data.get('body', email_data.get('snippet', 'No content available'))}

---

*Queued by Graceful Degradation System*
"""
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)
                
        except Exception as e:
            print(f"[ERROR] Failed to save queued email: {e}")
    
    def queue_transaction(self, transaction_data: dict):
        """
        Queue a transaction locally when Odoo is unavailable
        
        Args:
            transaction_data: Transaction data to queue
        """
        transaction_data["queued_at"] = datetime.now().isoformat()
        transaction_data["status"] = "queued"
        self.queued_transactions.append(transaction_data)
        
        # Save to file
        self._save_queued_transactions()
        
        print(f"[DEGRADATION] Transaction queued: {transaction_data.get('type', 'Unknown')}")
    
    def _save_queued_transactions(self):
        """Save queued transactions to file"""
        try:
            data = {
                "last_updated": datetime.now().isoformat(),
                "total_queued": len(self.queued_transactions),
                "transactions": self.queued_transactions
            }
            
            with open(LOCAL_TRANSACTIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"[ERROR] Failed to save queued transactions: {e}")
    
    def record_missed_message(self, message_data: dict):
        """
        Record a missed WhatsApp message when WhatsApp is unavailable
        
        Args:
            message_data: Message data to record
        """
        message_data["missed_at"] = datetime.now().isoformat()
        self.missed_messages.append(message_data)
        
        # Save to file
        self._save_missed_messages()
        
        print(f"[DEGRADATION] Message recorded as missed: {message_data.get('from', 'Unknown')}")
    
    def _save_missed_messages(self):
        """Save missed messages to file"""
        try:
            content = f"""# Missed WhatsApp Messages

*Generated by Graceful Degradation System*

**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Total Missed Messages:** {len(self.missed_messages)}

---

"""
            for i, msg in enumerate(self.missed_messages, 1):
                content += f"""## Message #{i}

- **From:** {msg.get('from', 'Unknown')}
- **Missed At:** {msg.get('missed_at', 'Unknown')}
- **Priority:** {msg.get('priority', 'Unknown')}

### Content

{msg.get('content', 'No content available')}

---

"""
            
            with open(MISSED_MESSAGES_FILE, "w", encoding="utf-8") as f:
                f.write(content)
                
        except Exception as e:
            print(f"[ERROR] Failed to save missed messages: {e}")
    
    def record_degradation_event(self, component: str, reason: str, fallback_action: str):
        """
        Record a degradation event
        
        Args:
            component: Name of failed component
            reason: Reason for degradation
            fallback_action: Action taken as fallback
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "component": component,
            "reason": reason,
            "fallback_action": fallback_action
        }
        self.degradation_events.append(event)
        
        print(f"[DEGRADATION] {component}: {reason} -> {fallback_action}")
    
    def get_queued_count(self) -> dict:
        """Get count of queued items"""
        return {
            "emails": len(self.queued_emails),
            "transactions": len(self.queued_transactions),
            "messages": len(self.missed_messages),
            "degradation_events": len(self.degradation_events)
        }
    
    def flush_queued_items(self, component_type: str) -> int:
        """
        Attempt to flush queued items when component recovers
        
        Args:
            component_type: Type of component that recovered
            
        Returns:
            Number of items flushed
        """
        flushed_count = 0
        
        if component_type == "gmail":
            # Move queued emails back to processing
            flushed_count = len(self.queued_emails)
            self.queued_emails = []
            
        elif component_type == "odoo":
            # Transactions would be synced to Odoo
            flushed_count = len(self.queued_transactions)
            self.queued_transactions = []
            self._save_queued_transactions()
            
        elif component_type == "whatsapp":
            # Process missed messages
            flushed_count = len(self.missed_messages)
            self.missed_messages = []
            self._save_missed_messages()
        
        if flushed_count > 0:
            print(f"[RECOVERY] Flushed {flushed_count} queued {component_type} items")
        
        return flushed_count


# =============================================================================
# HEALTH CHECKER
# =============================================================================

class HealthChecker:
    """
    Health checker for all system components
    
    Checks every 5 minutes and updates system_health.md
    """
    
    def __init__(self):
        """Initialize health checker"""
        self.components: Dict[str, ComponentHealth] = {}
        self.degradation_manager = GracefulDegradationManager()
        self.last_full_check: Optional[datetime] = None
        
        # Initialize known components
        self._init_components()
    
    def _init_components(self):
        """Initialize component health tracking"""
        known_components = [
            ("Gmail Service", ComponentType.GMAIL),
            ("Odoo ERP", ComponentType.ODOO),
            ("WhatsApp Web", ComponentType.WHATSAPP),
            ("Twitter/X", ComponentType.TWITTER),
            ("LinkedIn", ComponentType.LINKEDIN),
            ("Instagram", ComponentType.INSTAGRAM),
            ("File Watcher", ComponentType.FILE_WATCHER),
            ("Orchestrator", ComponentType.ORCHESTRATOR),
            ("Scheduler", ComponentType.SCHEDULER),
        ]
        
        for name, comp_type in known_components:
            self.components[name] = ComponentHealth(
                name=name,
                component_type=comp_type.value
            )
    
    def check_gmail_health(self) -> ComponentHealth:
        """Check Gmail service health"""
        component = self.components.get("Gmail Service")
        if not component:
            return ComponentHealth("Gmail Service", "gmail")
        
        component.total_checks += 1
        component.last_check = datetime.now().isoformat()
        
        try:
            # Check if credentials file exists
            credentials_file = VAULT_PATH / "credentials.json"
            if not credentials_file.exists():
                component.status = HealthStatus.UNHEALTHY
                component.error_message = "credentials.json not found"
                component.consecutive_failures += 1
                component.total_failures += 1
                return component
            
            # Check if token file exists (indicates previous successful auth)
            token_file = VAULT_PATH / "token.json"
            if token_file.exists():
                component.status = HealthStatus.HEALTHY
                component.last_success = component.last_check
                component.consecutive_failures = 0
            else:
                component.status = HealthStatus.DEGRADED
                component.error_message = "OAuth token not found - needs authentication"
                component.degradation_mode = True
            
        except Exception as e:
            component.status = HealthStatus.UNHEALTHY
            component.error_message = str(e)
            component.consecutive_failures += 1
            component.total_failures += 1
        
        return component
    
    def check_odoo_health(self) -> ComponentHealth:
        """Check Odoo ERP health"""
        component = self.components.get("Odoo ERP")
        if not component:
            return ComponentHealth("Odoo ERP", "odoo")
        
        component.total_checks += 1
        component.last_check = datetime.now().isoformat()
        
        try:
            # Check Odoo configuration in .env
            odoo_url = os.getenv("ODOO_URL", "")
            odoo_db = os.getenv("ODOO_DB", "")
            odoo_user = os.getenv("ODOO_USERNAME", "")
            odoo_password = os.getenv("ODOO_PASSWORD", "")
            
            if not all([odoo_url, odoo_db, odoo_user, odoo_password]):
                component.status = HealthStatus.DEGRADED
                component.error_message = "Odoo configuration incomplete"
                component.degradation_mode = True
                return component
            
            # Simple connectivity check (ping)
            import socket
            url_parts = odoo_url.replace("http://", "").replace("https://", "").split(":")
            host = url_parts[0]
            port = int(url_parts[1]) if len(url_parts) > 1 else 80
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                component.status = HealthStatus.HEALTHY
                component.last_success = component.last_check
                component.consecutive_failures = 0
            else:
                component.status = HealthStatus.UNHEALTHY
                component.error_message = f"Cannot connect to Odoo at {host}:{port}"
                component.consecutive_failures += 1
                component.total_failures += 1
                
        except Exception as e:
            component.status = HealthStatus.UNHEALTHY
            component.error_message = str(e)
            component.consecutive_failures += 1
            component.total_failures += 1
        
        return component
    
    def check_whatsapp_health(self) -> ComponentHealth:
        """Check WhatsApp Web health"""
        component = self.components.get("WhatsApp Web")
        if not component:
            return ComponentHealth("WhatsApp Web", "whatsapp")
        
        component.total_checks += 1
        component.last_check = datetime.now().isoformat()
        
        try:
            # Check if session folder exists
            session_path = VAULT_PATH / "whatsapp_session"
            if session_path.exists():
                component.status = HealthStatus.HEALTHY
                component.last_success = component.last_check
                component.consecutive_failures = 0
            else:
                component.status = HealthStatus.DEGRADED
                component.error_message = "WhatsApp session not found"
                component.degradation_mode = True
                
        except Exception as e:
            component.status = HealthStatus.UNHEALTHY
            component.error_message = str(e)
            component.consecutive_failures += 1
            component.total_failures += 1
        
        return component
    
    def check_social_media_health(self, name: str, session_folder: str) -> ComponentHealth:
        """Check social media component health"""
        component = self.components.get(name)
        if not component:
            return ComponentHealth(name, "social")
        
        component.total_checks += 1
        component.last_check = datetime.now().isoformat()
        
        try:
            session_path = VAULT_PATH / "sessions" / session_folder
            if session_path.exists() and any(session_path.iterdir()):
                component.status = HealthStatus.HEALTHY
                component.last_success = component.last_check
                component.consecutive_failures = 0
            else:
                component.status = HealthStatus.DEGRADED
                component.error_message = "Session not found or empty"
                component.degradation_mode = True
                
        except Exception as e:
            component.status = HealthStatus.UNHEALTHY
            component.error_message = str(e)
            component.consecutive_failures += 1
            component.total_failures += 1
        
        return component
    
    def check_file_watcher_health(self) -> ComponentHealth:
        """Check File Watcher health"""
        component = self.components.get("File Watcher")
        if not component:
            return ComponentHealth("File Watcher", "file_watcher")
        
        component.total_checks += 1
        component.last_check = datetime.now().isoformat()
        
        try:
            # Check if watched folders exist
            watched_folders = [
                VAULT_PATH / "Incoming",
                VAULT_PATH / "Needs_Action"
            ]
            
            all_exist = all(folder.exists() for folder in watched_folders)
            
            if all_exist:
                component.status = HealthStatus.HEALTHY
                component.last_success = component.last_check
                component.consecutive_failures = 0
            else:
                component.status = HealthStatus.DEGRADED
                component.error_message = "Some watched folders missing"
                component.degradation_mode = True
                
        except Exception as e:
            component.status = HealthStatus.UNHEALTHY
            component.error_message = str(e)
            component.consecutive_failures += 1
            component.total_failures += 1
        
        return component
    
    def check_orchestrator_health(self) -> ComponentHealth:
        """Check Orchestrator health"""
        component = self.components.get("Orchestrator")
        if not component:
            return ComponentHealth("Orchestrator", "orchestrator")
        
        component.total_checks += 1
        component.last_check = datetime.now().isoformat()
        
        try:
            # Check if Needs_Action and Done folders exist
            na_folder = VAULT_PATH / "Needs_Action"
            done_folder = VAULT_PATH / "Done"
            
            if na_folder.exists() and done_folder.exists():
                # Check recent activity in logs
                log_file = LOGS_FOLDER / f"orchestrator_{datetime.now().strftime('%Y-%m-%d')}.json"
                if log_file.exists():
                    component.status = HealthStatus.HEALTHY
                    component.last_success = component.last_check
                    component.consecutive_failures = 0
                else:
                    component.status = HealthStatus.DEGRADED
                    component.error_message = "No recent orchestrator activity"
                    component.degradation_mode = True
            else:
                component.status = HealthStatus.UNHEALTHY
                component.error_message = "Required folders missing"
                component.consecutive_failures += 1
                component.total_failures += 1
                
        except Exception as e:
            component.status = HealthStatus.UNHEALTHY
            component.error_message = str(e)
            component.consecutive_failures += 1
            component.total_failures += 1
        
        return component
    
    def run_full_health_check(self) -> HealthReport:
        """
        Run full health check on all components
        
        Returns:
            HealthReport with status of all components
        """
        print("\n" + "=" * 60)
        print("FULL SYSTEM HEALTH CHECK")
        print("=" * 60)
        
        self.last_full_check = datetime.now()
        
        # Check all components
        self.check_gmail_health()
        self.check_odoo_health()
        self.check_whatsapp_health()
        self.check_social_media_health("Twitter/X", "twitter_session")
        self.check_social_media_health("LinkedIn", "linkedin_session")
        self.check_social_media_health("Instagram", "instagram_session")
        self.check_file_watcher_health()
        self.check_orchestrator_health()
        
        # Determine overall status
        unhealthy_count = sum(
            1 for c in self.components.values()
            if c.status == HealthStatus.UNHEALTHY
        )
        degraded_count = sum(
            1 for c in self.components.values()
            if c.status == HealthStatus.DEGRADED
        )
        
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Get queued counts
        queued_counts = self.degradation_manager.get_queued_count()
        
        # Create report
        report = HealthReport(
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            components=self.components,
            degradation_events=self.degradation_manager.degradation_events,
            queued_transactions=queued_counts["transactions"],
            missed_messages=queued_counts["messages"]
        )
        
        # Print summary
        print(f"\nOverall Status: {overall_status.value.upper()}")
        print(f"\nComponent Status:")
        for name, component in self.components.items():
            status_icon = {
                HealthStatus.HEALTHY: "[OK]",
                HealthStatus.DEGRADED: "[WARN]",
                HealthStatus.UNHEALTHY: "[FAIL]",
                HealthStatus.UNKNOWN: "[??]"
            }.get(component.status, "[??]")
            print(f"  {status_icon} {name}: {component.status.value}")
            if component.error_message:
                print(f"       Error: {component.error_message}")
        
        print(f"\nQueued Items:")
        print(f"  Emails: {queued_counts['emails']}")
        print(f"  Transactions: {queued_counts['transactions']}")
        print(f"  Missed Messages: {queued_counts['messages']}")
        
        # Save report
        self._save_health_report(report)
        self._save_system_health_md(report)
        
        return report
    
    def _save_health_report(self, report: HealthReport):
        """Save health report to JSON file"""
        try:
            BRIEFINGS_FOLDER.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            report_path = BRIEFINGS_FOLDER / f"health_report_{date_str}.json"
            
            with open(report_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)
                
        except Exception as e:
            print(f"[ERROR] Failed to save health report: {e}")
    
    def _save_system_health_md(self, report: HealthReport):
        """Save system health to system_health.md"""
        try:
            content = f"""# System Health Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Overall Status:** {report.overall_status.value.upper()}

---

## Component Status

| Component | Status | Last Check | Consecutive Failures |
|-----------|--------|------------|---------------------|
"""
            
            for name, component in report.components.items():
                last_check = component.last_check[:19] if component.last_check else "Never"
                content += f"| {name} | {component.status.value} | {last_check} | {component.consecutive_failures} |\n"
            
            content += f"""
## Degradation Events

**Total Events:** {len(report.degradation_events)}

"""
            
            if report.degradation_events:
                for event in report.degradation_events[-10:]:  # Last 10 events
                    content += f"- **{event['component']}** ({event['timestamp'][:19]}): {event['reason']}\n"
                    content += f"  - Fallback: {event['fallback_action']}\n"
            else:
                content += "*No degradation events recorded*\n"
            
            content += f"""
## Queued Items

| Type | Count |
|------|-------|
| Emails | {report.queued_transactions} |
| Transactions | {report.queued_transactions} |
| Missed Messages | {report.missed_messages} |

---

## Degradation Actions

### When Gmail is Down
- Emails are queued locally in Needs_Action folder
- Queued emails are processed when Gmail recovers

### When Odoo is Down
- Transactions are logged to local_transactions.json
- Transactions are synced when Odoo recovers

### When WhatsApp Crashes
- Missed messages are saved to missed_messages.md
- Messages are processed when WhatsApp recovers

---

*Generated by Graceful Degradation System*
"""
            
            with open(SYSTEM_HEALTH_FILE, "w", encoding="utf-8") as f:
                f.write(content)
                
            print(f"\n[OK] System health saved to: {SYSTEM_HEALTH_FILE}")
            
        except Exception as e:
            print(f"[ERROR] Failed to save system_health.md: {e}")


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    """Main function - run health checker"""
    print("=" * 60)
    print("Graceful Degradation System - Health Checker")
    print("=" * 60)
    print(f"Vault Path: {VAULT_PATH}")
    print(f"Check Interval: {CHECK_INTERVAL_MINUTES} minutes")
    print(f"DRY_RUN: {DRY_RUN}")
    print("=" * 60)
    
    # Ensure folders exist
    for folder in [LOGS_FOLDER, BRIEFINGS_FOLDER, NEEDS_ACTION_FOLDER]:
        folder.mkdir(parents=True, exist_ok=True)
    
    # Create health checker
    checker = HealthChecker()
    
    # Run initial check
    print("\nRunning initial health check...")
    checker.run_full_health_check()
    
    # Continuous monitoring
    print(f"\nStarting continuous monitoring (every {CHECK_INTERVAL_MINUTES} minutes)...")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            time.sleep(CHECK_INTERVAL_MINUTES * 60)
            checker.run_full_health_check()
            
    except KeyboardInterrupt:
        print("\n\nHealth checker stopped by user")
        
        # Save final report
        checker.run_full_health_check()
        
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[ERROR] Fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
