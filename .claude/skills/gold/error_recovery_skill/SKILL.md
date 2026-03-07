# Error Recovery Skill

## Description

This skill handles error categorization, implements retry logic, manages graceful degradation, creates alert files, and performs health checks. It ensures system resilience and proper error escalation.

## When To Use This Skill

- When any operation fails
- When implementing retry logic
- When categorizing errors
- When creating system alerts
- When performing health checks
- When triggering graceful degradation

## Step By Step Instructions

### 1. Error Categories and Handling

**Error Category Definitions:**
```python
ERROR_CATEGORIES = {
    'TransientError': {
        'description': 'Temporary failures that may resolve on retry',
        'examples': ['Network timeout', 'API rate limit', 'Temporary unavailability'],
        'handling': 'retry_with_backoff',
        'max_retries': 3,
    },
    'AuthError': {
        'description': 'Authentication/authorization failures',
        'examples': ['Invalid credentials', 'Expired token', 'Permission denied'],
        'handling': 'alert_human_and_pause',
        'max_retries': 0,
    },
    'LogicError': {
        'description': 'Business logic or validation failures',
        'examples': ['Invalid input', 'Failed validation', 'Rule violation'],
        'handling': 'human_review_queue',
        'max_retries': 0,
    },
    'DataError': {
        'description': 'Data corruption or integrity issues',
        'examples': ['Corrupted file', 'Missing required field', 'Invalid format'],
        'handling': 'quarantine_and_alert',
        'max_retries': 0,
    },
    'SystemError': {
        'description': 'System-level failures requiring intervention',
        'examples': ['Disk full', 'Service crashed', 'Memory exhausted'],
        'handling': 'watchdog_restart',
        'max_retries': 0,
    },
}
```

**Error Categorization Function:**
```python
def categorize_error(error):
    """Categorize error for appropriate handling."""
    error_message = str(error).lower()
    error_type = type(error).__name__
    
    # Auth errors
    auth_patterns = ['auth', 'unauthorized', 'forbidden', 'permission', 'credential', 'token expired']
    if any(p in error_message for p in auth_patterns):
        return 'AuthError', ERROR_CATEGORIES['AuthError']
    
    # Data errors
    data_patterns = ['corrupt', 'invalid format', 'missing field', 'parse error', 'validation failed']
    if any(p in error_message for p in data_patterns):
        return 'DataError', ERROR_CATEGORIES['DataError']
    
    # Logic errors
    logic_patterns = ['invalid input', 'rule violation', 'business logic', 'constraint']
    if any(p in error_message for p in logic_patterns):
        return 'LogicError', ERROR_CATEGORIES['LogicError']
    
    # System errors
    system_patterns = ['disk', 'memory', 'crash', 'segfault', 'out of resource']
    if any(p in error_message for p in system_patterns):
        return 'SystemError', ERROR_CATEGORIES['SystemError']
    
    # Default to transient (retry)
    return 'TransientError', ERROR_CATEGORIES['TransientError']
```

### 2. TransientError: Retry 3x with Backoff

```python
import time
import random

def retry_with_backoff(func, max_retries=3, base_delay=1, max_delay=60):
    """Retry function with exponential backoff."""
    
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return func()
            
        except Exception as e:
            last_error = e
            category, config = categorize_error(e)
            
            # Don't retry non-transient errors
            if category != 'TransientError':
                log_error(f"Non-transient error, not retrying: {category}")
                raise
            
            # Check if we have retries left
            if attempt >= max_retries:
                log_error(f"Max retries ({max_retries}) exceeded")
                break
            
            # Calculate delay with jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter = random.uniform(0, delay * 0.1)
            total_delay = delay + jitter
            
            log_warning(f"Retry {attempt + 1}/{max_retries} after {total_delay:.1f}s: {e}")
            time.sleep(total_delay)
    
    # All retries failed
    raise last_error
```

**Usage Example:**
```python
def send_email_with_retry(email_details):
    """Send email with retry logic."""
    return retry_with_backoff(
        lambda: mcp_email_skill.send_mcp_email(email_details),
        max_retries=3,
        base_delay=2,
        max_delay=30
    )
```

### 3. AuthError: Alert Human, Pause

```python
def handle_auth_error(error, context):
    """Handle authentication error."""
    log_error(f"Auth error: {error}")
    
    # Pause the affected operation
    pause_operation(context['operation'])
    
    # Create alert for human
    alert_content = f"""---
alert_type: auth_error
severity: critical
timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
operation: {context.get('operation', 'unknown')}
---

# Authentication Error - Human Intervention Required

**Error:** {str(error)}
**Operation:** {context.get('operation')}
**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Impact
The system cannot authenticate and has paused the affected operation.

## Required Action
1. Check API credentials/tokens
2. Verify service account permissions
3. Refresh authentication if needed
4. Resume operation after fixing

## Affected Systems
- {context.get('affected_systems', ['Unknown'])}
"""
    
    create_alert_file(alert_content)
    
    return {
        'status': 'paused',
        'requires_human': True,
        'alert_created': True
    }
```

### 4. LogicError: Human Review Queue

```python
def handle_logic_error(error, context):
    """Handle logic error by queuing for human review."""
    log_error(f"Logic error: {error}")
    
    # Create review request
    review_file = f"Pending_Approval/LOGIC_REVIEW_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    content = f"""---
review_type: logic_error
severity: medium
timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
original_operation: {context.get('operation')}
---

# Logic Error - Human Review Required

**Error:** {str(error)}
**Operation:** {context.get('operation')}
**Context:** {context.get('details', {})}

## Problem Description
The system encountered a business logic or validation error that requires human judgment.

## Data Involved
{format_context_data(context.get('data', {}))}

## Review Options
- [ ] **Override** - Proceed despite error (specify reason)
- [ ] **Modify** - Fix data and retry
- [ ] **Skip** - Skip this operation
- [ ] **Escalate** - Requires senior review

## Reviewer Decision
_________________________________

**Reviewer:** ________________
**Date:** ________________
**Decision:** ________________
"""
    
    write_vault_file(review_file, content)
    
    return {
        'status': 'queued_for_review',
        'review_file': review_file,
        'requires_human': True
    }
```

### 5. DataError: Quarantine + Alert

```python
def handle_data_error(error, context):
    """Handle data error by quarantining and alerting."""
    log_error(f"Data error: {error}")
    
    # Move problematic file to quarantine
    if context.get('file_path'):
        quarantine_file(context['file_path'])
    
    # Create alert
    alert_content = f"""---
alert_type: data_error
severity: high
timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
file: {context.get('file_path', 'N/A')}
---

# Data Error - File Quarantined

**Error:** {str(error)}
**File:** {context.get('file_path', 'N/A')}
**Action Taken:** File moved to Quarantine/

## Problem Description
The file contains corrupted or invalid data that could cause system issues.

## Required Action
1. Review quarantined file
2. Determine if data can be recovered
3. Fix source of corruption
4. Delete or restore file
"""
    
    create_alert_file(alert_content)
    
    return {
        'status': 'quarantined',
        'alert_created': True,
        'requires_human': True
    }

def quarantine_file(file_path):
    """Move file to quarantine."""
    import shutil
    
    quarantine_dir = 'F:/AI_Employee_Vault/Quarantine'
    os.makedirs(quarantine_dir, exist_ok=True)
    
    filename = os.path.basename(file_path)
    quarantine_path = os.path.join(quarantine_dir, f"QUARANTINE_{filename}")
    
    shutil.move(file_path, quarantine_path)
    log_info(f"File quarantined: {quarantine_path}")
    
    return quarantine_path
```

### 6. SystemError: Watchdog Restart

```python
def handle_system_error(error, context):
    """Handle system error with watchdog restart."""
    log_error(f"System error: {error}")
    
    # Attempt graceful restart of affected component
    component = context.get('component', 'unknown')
    
    restart_result = restart_component(component)
    
    # Create alert
    alert_content = f"""---
alert_type: system_error
severity: critical
timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
component: {component}
restart_attempted: {restart_result['success']}
---

# System Error - Watchdog Action Taken

**Error:** {str(error)}
**Component:** {component}
**Restart Result:** {'Success' if restart_result['success'] else 'Failed'}

## Watchdog Actions
1. Detected system error
2. Attempted component restart
3. {'Component recovered' if restart_result['success'] else 'Manual intervention required'}

## Required Action
{'Continue monitoring - system should recover' if restart_result['success'] else 'Immediate human intervention required'}
"""
    
    create_alert_file(alert_content)
    
    return {
        'status': 'restart_attempted',
        'restart_success': restart_result['success'],
        'alert_created': True
    }

def restart_component(component):
    """Attempt to restart a component."""
    try:
        # Component-specific restart logic
        if component == 'file_watcher':
            # Restart file watcher
            import subprocess
            subprocess.Popen(['python', 'file_watcher.py'])
            return {'success': True}
        
        elif component == 'gmail_watcher':
            # Restart Gmail watcher
            import subprocess
            subprocess.Popen(['python', 'gmail_watcher.py'])
            return {'success': True}
        
        else:
            log_warning(f"Unknown component: {component}")
            return {'success': False, 'error': 'Unknown component'}
            
    except Exception as e:
        log_error(f"Restart failed: {e}")
        return {'success': False, 'error': str(e)}
```

### 7. Graceful Degradation Rules

```python
def enable_graceful_degradation(affected_services):
    """Enable graceful degradation mode."""
    
    degradation_config = {
        'mode': 'degraded',
        'affected_services': affected_services,
        'disabled_features': [],
        'fallback_enabled': True,
    }
    
    # Disable non-critical features
    if 'odoo' in affected_services:
        degradation_config['disabled_features'].extend([
            'invoice_creation',
            'financial_summary',
            'customer_management'
        ])
    
    if 'email' in affected_services:
        degradation_config['disabled_features'].extend([
            'bulk_email',
            'email_campaigns'
        ])
        # Enable fallback to draft-only mode
        degradation_config['email_fallback'] = 'draft_only'
    
    if 'social' in affected_services:
        degradation_config['disabled_features'].extend([
            'auto_posting',
            'scheduled_posts'
        ])
        # Enable fallback to draft-only mode
        degradation_config['social_fallback'] = 'draft_only'
    
    # Save degradation state
    write_vault_file('Logs/degradation_state.json', 
                     json.dumps(degradation_config, indent=2))
    
    # Create alert
    create_alert(f"""
Graceful degradation enabled.

**Affected Services:** {', '.join(affected_services)}
**Disabled Features:** {', '.join(degradation_config['disabled_features'])}

System will continue operating with reduced functionality.
""")
    
    return degradation_config
```

### 8. Alert Creation in Needs_Action/ALERT_*.md

```python
def create_alert_file(content):
    """Create alert file in Needs_Action/."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    alert_file = f"Needs_Action/ALERT_{timestamp}.md"
    
    write_vault_file(alert_file, content)
    log_info(f"Alert created: {alert_file}")
    
    return alert_file

def create_alert(message):
    """Create simple alert file."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    alert_file = f"Needs_Action/ALERT_{timestamp}.md"
    
    content = f"""---
alert_type: system_alert
severity: medium
timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---

# System Alert

{message}

**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Action Required:** Review and resolve
"""
    
    write_vault_file(alert_file, content)
    return alert_file
```

### 9. Health Check Rules

```python
def perform_health_check():
    """Perform comprehensive system health check."""
    health = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'healthy',
        'components': {},
        'issues': [],
    }
    
    # Check file system
    health['components']['file_system'] = check_file_system_health()
    
    # Check external services
    health['components']['odoo'] = check_odoo_health()
    health['components']['email'] = check_email_health()
    health['components']['social'] = check_social_health()
    
    # Check queues
    health['components']['queues'] = check_queue_health()
    
    # Check disk space
    health['components']['disk'] = check_disk_health()
    
    # Determine overall status
    unhealthy = [k for k, v in health['components'].items() 
                 if v.get('status') == 'unhealthy']
    degraded = [k for k, v in health['components'].items() 
                if v.get('status') == 'degraded']
    
    if unhealthy:
        health['status'] = 'unhealthy'
        health['issues'].extend(unhealthy)
    elif degraded:
        health['status'] = 'degraded'
        health['issues'].extend(degraded)
    
    # Save health report
    save_health_report(health)
    
    return health

def check_file_system_health():
    """Check file system health."""
    try:
        # Check vault folders exist
        required_folders = ['Inbox', 'Needs_Action', 'Done', 'Pending_Approval']
        for folder in required_folders:
            if not os.path.exists(f'F:/AI_Employee_Vault/{folder}'):
                return {'status': 'unhealthy', 'error': f'Missing folder: {folder}'}
        
        return {'status': 'healthy'}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}

def check_disk_health():
    """Check disk space health."""
    import shutil
    
    try:
        total, used, free = shutil.disk_usage("F:/")
        free_gb = free / (1024**3)
        
        if free_gb < 1:
            return {'status': 'unhealthy', 'error': f'Low disk space: {free_gb:.1f}GB'}
        elif free_gb < 5:
            return {'status': 'degraded', 'warning': f'Disk space low: {free_gb:.1f}GB'}
        else:
            return {'status': 'healthy', 'free_gb': free_gb}
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}

def check_queue_health():
    """Check queue sizes."""
    needs_action_count = count_files('Needs_Action')
    pending_count = count_files('Pending_Approval')
    
    issues = []
    
    if needs_action_count > 100:
        issues.append(f'Large backlog: {needs_action_count} in Needs_Action')
    
    if pending_count > 20:
        issues.append(f'Approval backlog: {pending_count} pending')
    
    if issues:
        return {'status': 'degraded', 'warnings': issues}
    
    return {'status': 'healthy'}
```

## Examples

### Example: Retry with Backoff

```python
try:
    result = retry_with_backoff(
        lambda: send_email(email),
        max_retries=3,
        base_delay=2
    )
except Exception as e:
    # All retries failed
    category, config = categorize_error(e)
    handle_error_by_category(category, e, context)
```

### Example: Health Check Output

```json
{
  "timestamp": "2026-03-07 10:00:00",
  "status": "healthy",
  "components": {
    "file_system": {"status": "healthy"},
    "odoo": {"status": "healthy"},
    "email": {"status": "healthy"},
    "social": {"status": "healthy"},
    "queues": {"status": "healthy"},
    "disk": {"status": "healthy", "free_gb": 50}
  },
  "issues": []
}
```

## Human Escalation Rules

**Always Escalate:**
1. AuthError - requires credential refresh
2. DataError - requires data review
3. SystemError - requires system intervention
4. LogicError after 3 occurrences (pattern detection)
5. Health check shows 'unhealthy' status
6. Graceful degradation enabled

## Related Skills

- All skills - Error handling integration
- `hitl_skill` - Human escalation
- `vault_manager_skill` - Alert file creation
- `ceo_briefing_skill` - Health reporting
