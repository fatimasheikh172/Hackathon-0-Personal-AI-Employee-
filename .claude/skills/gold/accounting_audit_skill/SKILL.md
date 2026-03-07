# Accounting Audit Skill

## Description

This skill audits bank transactions, detects subscription patterns, flags unused subscriptions (30+ days), monitors cost increases (>20%), runs weekly audits, and outputs structured audit reports.

## When To Use This Skill

- Every Sunday at 11 PM (scheduled)
- When auditing financial transactions
- When reviewing subscriptions
- When detecting cost anomalies
- When preparing financial reports

## Step By Step Instructions

### 1. Audit Bank Transactions

```python
def audit_bank_transactions():
    """Audit bank transactions for anomalies."""
    audit_result = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'transactions_reviewed': 0,
        'anomalies_found': [],
        'subscriptions_detected': [],
        'cost_increases': [],
        'unused_subscriptions': [],
    }
    
    # Get transactions from Odoo
    transactions = get_bank_transactions(days=30)
    audit_result['transactions_reviewed'] = len(transactions)
    
    # Analyze each transaction
    for txn in transactions:
        # Check for anomalies
        anomaly = check_transaction_anomaly(txn)
        if anomaly:
            audit_result['anomalies_found'].append(anomaly)
        
        # Detect subscription patterns
        subscription = detect_subscription(txn)
        if subscription:
            audit_result['subscriptions_detected'].append(subscription)
    
    # Check for cost increases
    audit_result['cost_increases'] = detect_cost_increases(transactions)
    
    # Check for unused subscriptions
    audit_result['unused_subscriptions'] = detect_unused_subscriptions()
    
    return audit_result
```

**Transaction Analysis:**
```python
def check_transaction_anomaly(transaction):
    """Check for transaction anomalies."""
    anomalies = []
    
    # Large transaction (> $10,000)
    if transaction.get('amount', 0) > 10000:
        anomalies.append({
            'type': 'large_transaction',
            'amount': transaction['amount'],
            'description': transaction.get('description'),
            'date': transaction.get('date'),
        })
    
    # Duplicate transaction
    if is_duplicate_transaction(transaction):
        anomalies.append({
            'type': 'duplicate',
            'amount': transaction['amount'],
            'description': transaction.get('description'),
            'date': transaction.get('date'),
        })
    
    # Unusual vendor
    if is_new_vendor(transaction):
        anomalies.append({
            'type': 'new_vendor',
            'vendor': transaction.get('vendor'),
            'amount': transaction['amount'],
            'date': transaction.get('date'),
        })
    
    return anomalies if anomalies else None
```

### 2. Subscription Detection Patterns

```python
SUBSCRIPTION_PATTERNS = [
    {'name': 'Software', 'keywords': ['saas', 'subscription', 'license', 'software', 'app']},
    {'name': 'Cloud Services', 'keywords': ['aws', 'azure', 'gcp', 'cloud', 'hosting', 'server']},
    {'name': 'Communication', 'keywords': ['slack', 'zoom', 'teams', 'phone', 'sms', 'email']},
    {'name': 'Professional', 'keywords': ['linkedin', 'adobe', 'office', 'microsoft', 'google']},
    {'name': 'Payment Processing', 'keywords': ['stripe', 'paypal', 'square', 'payment', 'processing']},
]

def detect_subscription(transaction):
    """Detect if transaction is a subscription."""
    description = transaction.get('description', '').lower()
    amount = transaction.get('amount', 0)
    
    for pattern in SUBSCRIPTION_PATTERNS:
        for keyword in pattern['keywords']:
            if keyword in description:
                return {
                    'type': pattern['name'],
                    'vendor': transaction.get('vendor'),
                    'amount': amount,
                    'date': transaction.get('date'),
                    'description': transaction.get('description'),
                    'likely_recurring': is_recurring_amount(amount),
                }
    
    # Check for recurring amounts
    if is_recurring_amount(amount):
        return {
            'type': 'Likely Subscription',
            'vendor': transaction.get('vendor'),
            'amount': amount,
            'date': transaction.get('date'),
            'description': transaction.get('description'),
            'likely_recurring': True,
        }
    
    return None

def is_recurring_amount(amount):
    """Check if amount matches typical subscription pricing."""
    # Common subscription price points
    common_prices = [9, 10, 19, 29, 49, 99, 199, 299, 499]
    
    for price in common_prices:
        if abs(amount - price) < 1:  # Within $1
            return True
        if abs(amount - price * 10) < 10:  # Within $10 for larger amounts
            return True
    
    return False
```

### 3. Flag Unused Subscriptions (30+ Days)

```python
def detect_unused_subscriptions():
    """Detect subscriptions not used in 30+ days."""
    unused = []
    
    # Get all detected subscriptions
    subscriptions = get_all_subscriptions()
    
    for sub in subscriptions:
        # Check last usage
        last_used = get_subscription_last_used(sub['vendor'])
        
        if last_used:
            days_unused = (datetime.now() - last_used).days
            
            if days_unused >= 30:
                unused.append({
                    'vendor': sub['vendor'],
                    'monthly_cost': sub['amount'],
                    'last_used': last_used.strftime('%Y-%m-%d'),
                    'days_unused': days_unused,
                    'annual_waste': sub['amount'] * 12,
                    'recommendation': 'Consider canceling',
                })
    
    return unused

def get_subscription_last_used(vendor):
    """Get last date subscription was used."""
    # Check activity logs for vendor usage
    # This is a placeholder - implement based on actual tracking
    
    activity_log = read_vault_file('Logs/activity_log.json')
    
    for entry in reversed(activity_log):
        if vendor.lower() in entry.get('service', '').lower():
            return datetime.strptime(entry['date'], '%Y-%m-%d')
    
    return None
```

### 4. Cost Increase Alerts (>20%)

```python
def detect_cost_increases(transactions):
    """Detect cost increases > 20%."""
    increases = []
    
    # Group transactions by vendor
    by_vendor = group_transactions_by_vendor(transactions)
    
    for vendor, vendor_txns in by_vendor.items():
        # Sort by date
        vendor_txns.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        if len(vendor_txns) >= 2:
            latest = vendor_txns[0]
            previous = vendor_txns[1]
            
            latest_amount = latest.get('amount', 0)
            previous_amount = previous.get('amount', 0)
            
            if previous_amount > 0:
                increase_pct = ((latest_amount - previous_amount) / previous_amount) * 100
                
                if increase_pct > 20:
                    increases.append({
                        'vendor': vendor,
                        'previous_amount': previous_amount,
                        'current_amount': latest_amount,
                        'increase_pct': round(increase_pct, 1),
                        'increase_amount': latest_amount - previous_amount,
                        'date': latest.get('date'),
                        'recommendation': 'Review and negotiate',
                    })
    
    return increases
```

### 5. Weekly Audit Schedule

```python
def should_run_weekly_audit():
    """Check if it's time for weekly audit."""
    now = datetime.now()
    
    # Check if Sunday (weekday() returns 6 for Sunday)
    if now.weekday() != 6:
        return False
    
    # Check if between 11 PM - midnight
    if now.hour != 23:
        return False
    
    # Check if already run this week
    week_number = now.isocalendar()[1]
    existing = f"Briefings/WEEKLY_AUDIT_{now.strftime('%Y-%m-%d')}.md"
    
    if os.path.exists(existing):
        return False
    
    return True

# In main orchestrator:
# if accounting_audit_skill.should_run_weekly_audit():
#     audit_result = accounting_audit_skill.audit_bank_transactions()
#     report = accounting_audit_skill.generate_audit_report(audit_result)
#     accounting_audit_skill.save_audit_report(report)
```

### 6. Output Format

```python
def generate_audit_report(audit_result):
    """Generate structured audit report."""
    
    report = f"""# Weekly Accounting Audit

**Audit Date:** {audit_result['date']}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Summary

| Metric | Value |
|--------|-------|
| Transactions Reviewed | {audit_result['transactions_reviewed']} |
| Anomalies Found | {len(audit_result['anomalies_found'])} |
| Subscriptions Detected | {len(audit_result['subscriptions_detected'])} |
| Cost Increases | {len(audit_result['cost_increases'])} |
| Unused Subscriptions | {len(audit_result['unused_subscriptions'])} |

---

## Anomalies Found

{format_anomalies(audit_result['anomalies_found'])}

---

## Subscriptions Detected

{format_subscriptions(audit_result['subscriptions_detected'])}

---

## Cost Increases (>20%)

{format_cost_increases(audit_result['cost_increases'])}

---

## Unused Subscriptions (30+ Days)

{format_unused_subscriptions(audit_result['unused_subscriptions'])}

---

## Recommendations

{generate_recommendations(audit_result)}

---

*Report generated by AI Employee Accounting Audit System*
"""
    
    return report

def format_anomalies(anomalies):
    """Format anomalies section."""
    if not anomalies:
        return "*No anomalies detected*"
    
    output = []
    for anomaly in anomalies:
        output.append(f"- **{anomaly['type']}**: ${anomaly['amount']} - {anomaly.get('description', 'N/A')} ({anomaly['date']})")
    
    return '\n'.join(output)

def format_unused_subscriptions(subscriptions):
    """Format unused subscriptions section."""
    if not subscriptions:
        return "*No unused subscriptions detected*"
    
    output = []
    total_waste = sum(s['annual_waste'] for s in subscriptions)
    
    for sub in subscriptions:
        output.append(f"- **{sub['vendor']}**: ${sub['monthly_cost']}/month, unused for {sub['days_unused']} days")
        output.append(f"  - Last used: {sub['last_used']}")
        output.append(f"  - Annual waste: ${sub['annual_waste']}")
        output.append(f"  - Recommendation: {sub['recommendation']}")
    
    output.append(f"\n**Total Potential Annual Savings:** ${total_waste}")
    
    return '\n'.join(output)

def generate_recommendations(audit_result):
    """Generate recommendations based on audit findings."""
    recommendations = []
    
    if audit_result['unused_subscriptions']:
        total_waste = sum(s['annual_waste'] for s in audit_result['unused_subscriptions'])
        recommendations.append(f"1. **Cancel unused subscriptions** - Potential savings: ${total_waste}/year")
    
    if audit_result['cost_increases']:
        recommendations.append("2. **Review cost increases** - Contact vendors to negotiate or understand increases")
    
    if audit_result['anomalies_found']:
        recommendations.append("3. **Review anomalies** - Investigate unusual transactions")
    
    if not recommendations:
        recommendations.append("✅ All financial metrics healthy - continue monitoring")
    
    return '\n'.join(recommendations)
```

## Examples

### Example Audit Report

```markdown
# Weekly Accounting Audit

**Audit Date:** 2026-03-07
**Generated:** 2026-03-07 23:00:00

---

## Summary

| Metric | Value |
|--------|-------|
| Transactions Reviewed | 156 |
| Anomalies Found | 2 |
| Subscriptions Detected | 12 |
| Cost Increases | 1 |
| Unused Subscriptions | 2 |

---

## Anomalies Found

- **new_vendor**: $5,000 - Payment to New Supplier Inc (2026-03-05)
- **large_transaction**: $12,500 - Equipment purchase (2026-03-03)

---

## Subscriptions Detected

- **Software**: Slack - $29/month
- **Cloud Services**: AWS - $499/month
- **Communication**: Zoom - $49/month
- **Professional**: LinkedIn - $99/month

---

## Cost Increases (>20%)

- **AWS**: Previous $399 → Current $499 (+25.1%, +$100)
  - Date: 2026-03-01
  - Recommendation: Review and negotiate

---

## Unused Subscriptions (30+ Days)

- **Adobe Creative Cloud**: $49/month, unused for 45 days
  - Last used: 2026-01-20
  - Annual waste: $588
  - Recommendation: Consider canceling

- **Premium Analytics Tool**: $199/month, unused for 60 days
  - Last used: 2026-01-05
  - Annual waste: $2,388
  - Recommendation: Consider canceling

**Total Potential Annual Savings:** $2,976

---

## Recommendations

1. **Cancel unused subscriptions** - Potential savings: $2,976/year
2. **Review cost increases** - Contact vendors to negotiate or understand increases
3. **Review anomalies** - Investigate unusual transactions

---

*Report generated by AI Employee Accounting Audit System*
```

## Error Handling

### Odoo Connection Failed

```python
try:
    transactions = get_bank_transactions(days=30)
except OdooConnectionError:
    log_error("Cannot connect to Odoo for audit")
    create_alert("Weekly audit failed - Odoo unavailable")
    return None
```

### Report Generation Failed

```python
try:
    report = generate_audit_report(audit_result)
except Exception as e:
    log_error(f"Audit report generation failed: {e}")
    # Save raw data for manual review
    save_raw_audit_data(audit_result)
```

## Human Escalation Rules

**Escalate When:**
1. Anomalies > $10,000 (large transaction review)
2. Unused subscriptions found (cancellation decision)
3. Cost increases > 50% (urgent vendor review)
4. Duplicate payments detected (refund required)
5. New vendor with large payment (verification needed)

## Related Skills

- `odoo_skill` - Transaction data source
- `ceo_briefing_skill` - Financial reporting
- `error_recovery_skill` - Error handling
- `vault_manager_skill` - Report storage
