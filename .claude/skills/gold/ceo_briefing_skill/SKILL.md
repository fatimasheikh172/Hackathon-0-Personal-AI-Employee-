# CEO Briefing Skill

## Description

This skill generates the Monday Morning CEO Briefing report by analyzing business data from multiple sources, including Business_Goals.md, Odoo financial summary, completed tasks, and pending approvals. Outputs structured executive reports.

## When To Use This Skill

- Every Monday at 8 AM (scheduled)
- When executive summary is requested
- When weekly business review is needed
- When compiling business metrics
- When creating leadership reports

## Step By Step Instructions

### 1. Data Sources to Check

**Required Data Sources:**
```python
DATA_SOURCES = {
    'business_goals': 'Business_Goals.md',
    'odoo_summary': 'Odoo MCP - Financial Summary',
    'completed_tasks': 'Done/ folder',
    'pending_approvals': 'Pending_Approval/ folder',
    'dashboard': 'Dashboard.md',
    'alerts': 'Needs_Action/ALERT_*.md',
}
```

**Data Collection Function:**
```python
def collect_briefing_data():
    """Collect all data for CEO briefing."""
    data = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'week_number': datetime.now().isocalendar()[1],
        'business_goals': None,
        'financial_summary': None,
        'completed_tasks': [],
        'pending_approvals': [],
        'alerts': [],
        'metrics': {},
    }
    
    # Read Business Goals
    data['business_goals'] = read_business_goals()
    
    # Get Odoo Financial Summary
    data['financial_summary'] = get_odoo_financial_summary()
    
    # Scan completed tasks (last 7 days)
    data['completed_tasks'] = scan_completed_tasks(days=7)
    
    # Count pending approvals
    data['pending_approvals'] = scan_pending_approvals()
    
    # Check for alerts
    data['alerts'] = scan_alerts()
    
    # Calculate metrics
    data['metrics'] = calculate_metrics(data)
    
    return data
```

### 2. Read Business Goals

```python
def read_business_goals():
    """Read and parse Business_Goals.md."""
    try:
        content = read_vault_file('Business_Goals.md')
        
        # Parse goals
        goals = {
            'revenue_target': None,
            'current_revenue': None,
            'key_objectives': [],
            'quarterly_goals': [],
            'annual_goals': [],
        }
        
        # Extract revenue target (look for patterns like "$X" or "target: X")
        revenue_match = re.search(r'revenue.*?(\$[\d,]+)', content, re.IGNORECASE)
        if revenue_match:
            goals['revenue_target'] = parse_currency(revenue_match.group(1))
        
        # Extract objectives
        objective_lines = [l.strip() for l in content.split('\n') 
                          if l.strip().startswith('-') or l.strip().startswith('*')]
        goals['key_objectives'] = objective_lines[:10]  # Top 10
        
        return goals
        
    except FileNotFoundError:
        log_warning("Business_Goals.md not found")
        return None
```

### 3. Get Odoo Financial Summary

```python
def get_odoo_financial_summary():
    """Get financial summary from Odoo."""
    try:
        result = odoo_skill.get_financial_summary()
        
        if result['success']:
            return {
                'revenue_this_month': result['data'].get('revenue_this_month', 0),
                'revenue_this_year': result['data'].get('revenue_this_year', 0),
                'total_receivable': result['data'].get('total_receivable', 0),
                'outstanding_invoices': result['data'].get('outstanding_invoices', 0),
                'draft_invoices': result['data'].get('draft_invoices', 0),
            }
        else:
            log_warning(f"Odoo summary failed: {result.get('error')}")
            return None
            
    except Exception as e:
        log_error(f"Financial summary error: {e}")
        return None
```

### 4. Scan Completed Tasks

```python
def scan_completed_tasks(days=7):
    """Scan Done/ folder for completed tasks."""
    done_folder = 'F:/AI_Employee_Vault/Done'
    completed = []
    
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for filename in os.listdir(done_folder):
        if not filename.endswith('.md'):
            continue
        
        filepath = os.path.join(done_folder, filename)
        
        # Check file modification time
        mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        if mod_time < cutoff_date:
            continue
        
        # Extract task info
        task_info = {
            'filename': filename,
            'completed_at': mod_time.strftime('%Y-%m-%d %H:%M'),
            'type': extract_task_type(filename),
            'summary': extract_task_summary(filepath),
        }
        
        completed.append(task_info)
    
    # Sort by completion date (newest first)
    completed.sort(key=lambda x: x['completed_at'], reverse=True)
    
    return completed[:20]  # Top 20 recent tasks
```

### 5. Scan Pending Approvals

```python
def scan_pending_approvals():
    """Scan Pending_Approval/ folder."""
    pending_folder = 'F:/AI_Employee_Vault/Pending_Approval'
    pending = []
    
    for filename in os.listdir(pending_folder):
        if not filename.endswith('.md'):
            continue
        
        filepath = os.path.join(pending_folder, filename)
        
        # Extract approval info
        approval_info = {
            'filename': filename,
            'type': extract_approval_type(filename),
            'created_at': get_file_creation_time(filepath),
            'priority': extract_priority(filepath),
        }
        
        pending.append(approval_info)
    
    return pending
```

### 6. Report Sections

**Complete Report Structure:**
```python
def generate_ceo_briefing(data):
    """Generate complete CEO briefing report."""
    
    report = f"""# CEO Weekly Briefing

**Date:** {data['date']}
**Week:** {data['week_number']}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Executive Summary

{generate_executive_summary(data)}

---

## Revenue vs Target

{generate_revenue_section(data)}

---

## Completed Tasks (Last 7 Days)

{generate_completed_tasks_section(data)}

---

## Bottlenecks

{generate_bottlenecks_section(data)}

---

## Proactive Suggestions

{generate_suggestions_section(data)}

---

## Next Week Priorities

{generate_priorities_section(data)}

---

*Report generated by AI Employee System*
"""
    
    return report
```

### 7. Section Generators

**Executive Summary:**
```python
def generate_executive_summary(data):
    """Generate executive summary section."""
    metrics = data.get('metrics', {})
    
    summary = []
    
    # Overall status
    status = "🟢 OPERATIONAL" if not data.get('alerts') else "🟡 ATTENTION NEEDED"
    summary.append(f"**System Status:** {status}")
    
    # Key metrics
    if metrics.get('revenue_vs_target'):
        summary.append(f"**Revenue Performance:** {metrics['revenue_vs_target']}% of target")
    
    summary.append(f"**Tasks Completed:** {len(data.get('completed_tasks', []))} this week")
    summary.append(f"**Pending Approvals:** {len(data.get('pending_approvals', []))} awaiting decision")
    
    if data.get('alerts'):
        summary.append(f"**Active Alerts:** {len(data['alerts'])}")
    
    return '\n'.join(summary)
```

**Revenue vs Target:**
```python
def generate_revenue_section(data):
    """Generate revenue section."""
    goals = data.get('business_goals', {})
    financials = data.get('financial_summary', {})
    
    if not goals or not financials:
        return "*Data unavailable*"
    
    target = goals.get('revenue_target', 0)
    actual = financials.get('revenue_this_month', 0)
    percentage = (actual / target * 100) if target > 0 else 0
    
    # Progress bar
    bar_length = 30
    filled = int(bar_length * percentage / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    
    status = "✅ On Track" if percentage >= 80 else "⚠️ Behind Target"
    
    return f"""
| Metric | Value |
|--------|-------|
| Monthly Target | ${target:,.2f} |
| Current Revenue | ${actual:,.2f} |
| Progress | {percentage:.1f}% |
| Status | {status} |

**Progress:** [{bar}] {percentage:.1f}%
"""
```

**Completed Tasks:**
```python
def generate_completed_tasks_section(data):
    """Generate completed tasks section."""
    tasks = data.get('completed_tasks', [])
    
    if not tasks:
        return "*No tasks completed this week*"
    
    # Group by type
    by_type = {}
    for task in tasks:
        task_type = task.get('type', 'Other')
        if task_type not in by_type:
            by_type[task_type] = []
        by_type[task_type].append(task)
    
    output = []
    for task_type, type_tasks in by_type.items():
        output.append(f"\n**{task_type}:** {len(type_tasks)}")
        for task in type_tasks[:5]:  # Show top 5 per category
            output.append(f"- {task['summary']} ({task['completed_at']})")
    
    return '\n'.join(output)
```

**Bottlenecks:**
```python
def generate_bottlenecks_section(data):
    """Generate bottlenecks section."""
    bottlenecks = []
    
    # Check pending approvals age
    for approval in data.get('pending_approvals', []):
        age = get_approval_age(approval)
        if age > 24:  # Older than 24 hours
            bottlenecks.append(f"⏳ Approval pending {age:.1f}h: {approval['filename']}")
    
    # Check alerts
    for alert in data.get('alerts', []):
        bottlenecks.append(f"🚨 Alert: {alert['filename']}")
    
    # Check task backlog
    needs_action_count = count_files('Needs_Action')
    if needs_action_count > 20:
        bottlenecks.append(f"📋 Task backlog: {needs_action_count} items in Needs_Action/")
    
    if not bottlenecks:
        return "*No bottlenecks identified*"
    
    return '\n'.join(bottlenecks)
```

**Proactive Suggestions:**
```python
def generate_suggestions_section(data):
    """Generate proactive suggestions."""
    suggestions = []
    
    # Based on metrics
    metrics = data.get('metrics', {})
    
    if metrics.get('revenue_vs_target', 100) < 70:
        suggestions.append("💡 Revenue below target - consider accelerating collections")
    
    if len(data.get('pending_approvals', [])) > 5:
        suggestions.append("💡 High pending approvals - consider batch review session")
    
    if metrics.get('task_completion_rate', 100) < 80:
        suggestions.append("💡 Task completion rate low - review prioritization")
    
    if not suggestions:
        suggestions.append("✅ All metrics healthy - maintain current operations")
    
    return '\n'.join(suggestions)
```

**Next Week Priorities:**
```python
def generate_priorities_section(data):
    """Generate next week priorities."""
    priorities = []
    
    # Carry over pending approvals
    if data.get('pending_approvals'):
        priorities.append(f"1. Clear {len(data['pending_approvals'])} pending approvals")
    
    # Address alerts
    if data.get('alerts'):
        priorities.append(f"2. Resolve {len(data['alerts'])} active alerts")
    
    # Revenue focus
    metrics = data.get('metrics', {})
    if metrics.get('revenue_vs_target', 100) < 90:
        priorities.append("3. Focus on revenue-generating activities")
    
    # Standard priorities
    priorities.append("4. Continue monitoring system health")
    priorities.append("5. Review and optimize workflows")
    
    return '\n'.join(f"{i}. {p}" for i, p in enumerate(priorities, 1))
```

### 8. Output File

```python
def save_ceo_briefing(report):
    """Save briefing to file."""
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"Briefings/CEO_BRIEFING_{date_str}.md"
    
    write_vault_file(filename, report)
    
    log_info(f"CEO briefing saved: {filename}")
    
    return filename
```

### 9. Schedule: Every Monday 8 AM

```python
def should_generate_briefing():
    """Check if it's time for CEO briefing."""
    now = datetime.now()
    
    # Check if Monday (weekday() returns 0 for Monday)
    if now.weekday() != 0:
        return False
    
    # Check if between 8-9 AM
    if now.hour != 8:
        return False
    
    # Check if already generated today
    date_str = now.strftime('%Y-%m-%d')
    existing = f"Briefings/CEO_BRIEFING_{date_str}.md"
    
    if os.path.exists(existing):
        return False
    
    return True

# In main orchestrator:
# if ceo_briefing_skill.should_generate_briefing():
#     data = collect_briefing_data()
#     report = generate_ceo_briefing(data)
#     save_ceo_briefing(report)
```

## Examples

### Example Output

```markdown
# CEO Weekly Briefing

**Date:** 2026-03-07
**Week:** 10
**Generated:** 2026-03-07 08:00:00

---

## Executive Summary

**System Status:** 🟢 OPERATIONAL
**Revenue Performance:** 78% of target
**Tasks Completed:** 23 this week
**Pending Approvals:** 3 awaiting decision

---

## Revenue vs Target

| Metric | Value |
|--------|-------|
| Monthly Target | $50,000.00 |
| Current Revenue | $39,000.00 |
| Progress | 78.0% |
| Status | ⚠️ Behind Target |

**Progress:** [██████████████████████░░░░] 78.0%

---

## Completed Tasks (Last 7 Days)

**Email Replies:** 8
- Reply to Client ABC (2026-03-06 15:30)
- Reply to Vendor XYZ (2026-03-06 10:15)

**Invoices Created:** 5
- INV-2026-015 for Client DEF (2026-03-05 14:00)
- INV-2026-014 for Client GHI (2026-03-04 11:30)

**Social Posts:** 10
- LinkedIn post: Product update (2026-03-05 09:00)
- Twitter thread: Industry insights (2026-03-04 16:00)

---

## Bottlenecks

⏳ Approval pending 48.5h: APPROVAL_invoice_post_20260305_100000.md
📋 Task backlog: 25 items in Needs_Action/

---

## Proactive Suggestions

💡 Revenue below target - consider accelerating collections
💡 High pending approvals - consider batch review session

---

## Next Week Priorities

1. Clear 3 pending approvals
2. Resolve 2 active alerts
3. Focus on revenue-generating activities
4. Continue monitoring system health
5. Review and optimize workflows

---

*Report generated by AI Employee System*
```

## Error Handling

### Data Source Unavailable

```python
if data['financial_summary'] is None:
    log_warning("Financial summary unavailable")
    # Use placeholder in report
    revenue_section = "*Financial data temporarily unavailable*"
```

### Business Goals Not Found

```python
if data['business_goals'] is None:
    log_warning("Business_Goals.md not found")
    # Create briefing without goals comparison
    data['metrics']['revenue_vs_target'] = None
```

## Human Escalation Rules

**Escalate When:**
1. Briefing generation fails (alert CEO)
2. Critical data sources unavailable
3. Revenue < 50% of target (urgent alert)
4. Pending approvals > 10 (bottleneck alert)
5. System alerts > 5 (system health concern)

## Related Skills

- `odoo_skill` - Financial summary data
- `vault_manager_skill` - File operations
- `hitl_skill` - Pending approval tracking
- `error_recovery_skill` - Error handling
