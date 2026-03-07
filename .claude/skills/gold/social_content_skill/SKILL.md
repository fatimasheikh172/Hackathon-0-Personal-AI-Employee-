# Social Content Skill

## Description

This skill adapts one topic for all social platforms (Twitter, LinkedIn, Instagram), enforces platform-specific rules, manages content approval workflows, handles scheduling, and manages failed posts.

## When To Use This Skill

- When creating multi-platform social content
- When adapting content for different audiences
- When scheduling social media posts
- When managing content approval
- When handling posting failures

## Step By Step Instructions

### 1. Adapt One Topic for All Platforms

```python
def adapt_content_for_all_platforms(topic, details=None):
    """Adapt one topic for Twitter, LinkedIn, and Instagram."""
    
    # Base content generation
    base_content = generate_base_content(topic, details)
    
    # Platform-specific adaptations
    adaptations = {
        'twitter': adapt_for_twitter(base_content),
        'linkedin': adapt_for_linkedin(base_content),
        'instagram': adapt_for_instagram(base_content),
    }
    
    return adaptations

def generate_base_content(topic, details):
    """Generate base content from topic."""
    return {
        'topic': topic,
        'key_message': extract_key_message(topic, details),
        'tone': 'professional',
        'call_to_action': get_appropriate_cta(topic),
        'hashtags': generate_base_hashtags(topic),
        'details': details or {},
    }
```

### 2. Platform-Specific Rules

**Twitter Rules:**
```python
def adapt_for_twitter(base_content):
    """Adapt content for Twitter."""
    return {
        'platform': 'twitter',
        'content': generate_tweet(base_content['topic']),
        'max_length': 280,
        'max_hashtags': 2,
        'tone': 'punchy',
        'emoji_limit': 2,
        'rate_limit': '5/hour',
        'dry_run_required': True,
    }

# Twitter-specific validation
def validate_twitter_content(content):
    """Validate Twitter content."""
    issues = []
    
    # Length check
    if len(content) > 280:
        issues.append(f"Too long: {len(content)} chars (max 280)")
    
    # Hashtag check
    hashtag_count = content.count('#')
    if hashtag_count > 2:
        issues.append(f"Too many hashtags: {hashtag_count} (max 2)")
    
    # Emoji check
    emoji_count = sum(1 for c in content if c in '😀😃😄😊👍🎉🚀📈')
    if emoji_count > 2:
        issues.append(f"Too many emojis: {emoji_count} (max 2)")
    
    return len(issues) == 0, issues
```

**LinkedIn Rules:**
```python
def adapt_for_linkedin(base_content):
    """Adapt content for LinkedIn."""
    return {
        'platform': 'linkedin',
        'content': generate_linkedin_post(base_content['topic']),
        'min_length': 150,
        'max_length': 300,
        'max_hashtags': 5,
        'tone': 'professional',
        'emoji_limit': 3,
        'rate_limit': '2/day',
        'approval_required': True,
    }

# LinkedIn-specific validation
def validate_linkedin_content(content):
    """Validate LinkedIn content."""
    issues = []
    
    # Length check
    word_count = len(content.split())
    if word_count < 150:
        issues.append(f"Too short: {word_count} words (min 150)")
    elif word_count > 300:
        issues.append(f"Too long: {word_count} words (max 300)")
    
    # Hashtag check
    hashtag_count = content.count('#')
    if hashtag_count > 5:
        issues.append(f"Too many hashtags: {hashtag_count} (max 5)")
    
    return len(issues) == 0, issues
```

**Instagram Rules:**
```python
def adapt_for_instagram(base_content):
    """Adapt content for Instagram."""
    return {
        'platform': 'instagram',
        'content': generate_instagram_caption(base_content['topic']),
        'max_hashtags': 10,
        'tone': 'visual_focused',
        'emoji_limit': 5,
        'rate_limit': '5/day',
        'requires_image': True,
        'approval_required': True,
    }

# Instagram-specific validation
def validate_instagram_content(content, image_path=None):
    """Validate Instagram content."""
    issues = []
    
    # Hashtag check
    hashtags = re.findall(r'#[\w]+', content)
    if len(hashtags) > 10:
        issues.append(f"Too many hashtags: {len(hashtags)} (max 10)")
    
    # Image check
    if image_path and not os.path.exists(image_path):
        issues.append(f"Image not found: {image_path}")
    
    return len(issues) == 0, issues
```

### 3. Content Comparison Table

```python
def generate_platform_comparison(topic, adaptations):
    """Generate comparison of adapted content."""
    
    comparison = f"""# Multi-Platform Content Adaptation

**Topic:** {topic}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Platform Comparison

| Platform | Length | Hashtags | Tone | Status |
|----------|--------|----------|------|--------|
| Twitter | {len(adaptations['twitter']['content'])} chars | 2 max | Punchy | Ready |
| LinkedIn | {len(adaptations['linkedin']['content'].split())} words | 5 max | Professional | Ready |
| Instagram | {len(adaptations['instagram']['content'].split())} words | 10 max | Visual | Ready |

---

## Twitter Content
```
{adaptations['twitter']['content']}
```

---

## LinkedIn Content
```
{adaptations['linkedin']['content']}
```

---

## Instagram Content
```
{adaptations['instagram']['content']}
```
"""
    
    return comparison
```

### 4. Content Approval Workflow

```python
def submit_for_approval(adaptations, topic):
    """Submit all platform content for approval."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    approval_file = f"Pending_Approval/SOCIAL_CONTENT_{timestamp}.md"
    
    content = f"""---
approval_type: social_content
topic: {topic}
created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
platforms: twitter, linkedin, instagram
status: pending_approval
---

# Social Content Approval Required

**Topic:** {topic}
**Platforms:** Twitter, LinkedIn, Instagram
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Twitter Content
```
{adaptations['twitter']['content']}
```
**Length:** {len(adaptations['twitter']['content'])} chars
**Validation:** {'✅ Pass' if validate_twitter_content(adaptations['twitter']['content'])[0] else '❌ Fail'}

---

## LinkedIn Content
```
{adaptations['linkedin']['content']}
```
**Length:** {len(adaptations['linkedin']['content'].split())} words
**Validation:** {'✅ Pass' if validate_linkedin_content(adaptations['linkedin']['content'])[0] else '❌ Fail'}

---

## Instagram Content
```
{adaptations['instagram']['content']}
```
**Hashtags:** {len(re.findall(r'#[\w]+', adaptations['instagram']['content']))}
**Validation:** {'✅ Pass' if validate_instagram_content(adaptations['instagram']['content'])[0] else '❌ Fail'}

---

## Approval Decision

- [ ] **Approve All** - Post to all platforms
- [ ] **Approve Selected** - Approve specific platforms only
- [ ] **Reject** - Revise and resubmit
- [ ] **Reject All** - Cancel this content

### Platform Selection (if partial approval)
- [ ] Twitter only
- [ ] LinkedIn only
- [ ] Instagram only

### Reviewer Notes
_________________________________

**Reviewer:** ________________
**Date:** ________________
**Decision:** ________________
"""
    
    write_vault_file(approval_file, content)
    return approval_file
```

### 5. Scheduling Rules

```python
OPTIMAL_POSTING_TIMES = {
    'twitter': {
        'best': ['9:00', '12:00', '15:00'],  # 9 AM, 12 PM, 3 PM
        'days': [0, 1, 2, 3, 4],  # Mon-Fri
        'avoid': [0, 1, 2, 3, 4, 5, 22, 23],  # Early morning and late night
    },
    'linkedin': {
        'best': ['8:00', '9:00', '12:00'],  # 8 AM, 9 AM, 12 PM
        'days': [0, 1, 2, 3, 4],  # Mon-Fri
        'avoid': [5, 6],  # Weekends
    },
    'instagram': {
        'best': ['11:00', '13:00', '19:00'],  # 11 AM, 1 PM, 7 PM
        'days': [0, 1, 2, 3, 4, 5, 6],  # All days
        'avoid': [2, 3, 4, 5],  # Very early morning
    },
}

def get_optimal_posting_time(platform, preferred_date=None):
    """Get optimal posting time for platform."""
    optimal = OPTIMAL_POSTING_TIMES.get(platform, {})
    best_times = optimal.get('best', ['12:00'])
    avoid_hours = optimal.get('avoid', [])
    preferred_days = optimal.get('days', [0, 1, 2, 3, 4])
    
    now = datetime.now()
    
    # Start with preferred date or now
    if preferred_date:
        target = preferred_date
    else:
        target = now
    
    # Find next valid day
    while target.weekday() not in preferred_days:
        target += timedelta(days=1)
    
    # Find next valid hour
    for hour_str in best_times:
        hour = int(hour_str.split(':')[0])
        if hour not in avoid_hours:
            target = target.replace(hour=hour, minute=0, second=0, microsecond=0)
            if target > now:
                return target
    
    # Fallback to tomorrow at first best time
    target = now + timedelta(days=1)
    target = target.replace(hour=int(best_times[0].split(':')[0]), 
                           minute=0, second=0, microsecond=0)
    
    return target

def schedule_posts(adaptations, topic):
    """Schedule posts for all platforms."""
    schedules = {}
    
    for platform in ['twitter', 'linkedin', 'instagram']:
        scheduled_time = get_optimal_posting_time(platform)
        
        schedules[platform] = {
            'content': adaptations[platform]['content'],
            'scheduled_time': scheduled_time.strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'scheduled',
            'platform': platform,
        }
    
    # Save schedule
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    schedule_file = f"Drafts/SOCIAL_SCHEDULE_{timestamp}.md"
    
    content = f"""---
schedule_type: social_media
topic: {topic}
created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---

# Social Media Schedule

**Topic:** {topic}

## Scheduled Posts

"""
    
    for platform, schedule in schedules.items():
        content += f"""### {platform.title()}
**Scheduled:** {schedule['scheduled_time']}
**Content:**
```
{schedule['content']}
```

"""
    
    write_vault_file(schedule_file, content)
    return schedules
```

### 6. Failed Post Handling

```python
def handle_failed_post(platform, content, error):
    """Handle failed social media post."""
    log_error(f"{platform} post failed: {error}")
    
    # Categorize failure
    failure_type = categorize_failure(error)
    
    # Create failed post record
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    failed_file = f"Logs/FAILED_POST_{platform}_{timestamp}.md"
    
    record = f"""---
failure_type: {failure_type}
platform: {platform}
timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
retry_possible: {failure_type == 'transient'}
---

# Failed Post Record

**Platform:** {platform}
**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Failure Type:** {failure_type}

## Content
```
{content}
```

## Error
{str(error)}

## Recommended Action
{get_failure_recommendation(failure_type)}

## Retry Status
"""
    
    if failure_type == 'transient':
        record += "- [ ] Retry after delay\n"
    elif failure_type == 'validation':
        record += "- [ ] Fix content and resubmit\n"
    elif failure_type == 'auth':
        record += "- [ ] Fix authentication and resubmit\n"
    else:
        record += "- [ ] Manual review required\n"
    
    write_vault_file(failed_file, record)
    
    # Create alert if needed
    if failure_type in ['auth', 'system']:
        create_alert(f"{platform} posting failed: {failure_type}")
    
    return {
        'status': 'failed',
        'failure_type': failure_type,
        'record_file': failed_file,
        'retry_possible': failure_type == 'transient'
    }

def categorize_failure(error):
    """Categorize post failure."""
    error_message = str(error).lower()
    
    if 'auth' in error_message or 'token' in error_message:
        return 'auth'
    elif 'validation' in error_message or 'invalid' in error_message:
        return 'validation'
    elif 'rate limit' in error_message:
        return 'rate_limit'
    elif 'timeout' in error_message or 'network' in error_message:
        return 'transient'
    else:
        return 'unknown'

def get_failure_recommendation(failure_type):
    """Get recommendation for failure type."""
    recommendations = {
        'auth': 'Check API credentials and re-authenticate',
        'validation': 'Review content against platform rules',
        'rate_limit': 'Wait for rate limit to reset',
        'transient': 'Retry after a short delay',
        'unknown': 'Manual review required',
    }
    return recommendations.get(failure_type, 'Unknown error - manual review')
```

## Examples

### Example: Multi-Platform Adaptation

**Input Topic:**
```python
topic = "AI Employee System Launch"
details = {
    'key_features': ['Email automation', 'Task processing', 'Social media management'],
    'launch_date': 'March 10, 2026',
    'target_audience': 'Small business owners'
}
```

**Generated Adaptations:**

**Twitter:**
```
🚀 AI Employee System launches March 10!

Automate emails, tasks, and social media in one platform.

Perfect for small business owners ready to scale.

#AI #Automation
```

**LinkedIn:**
```
Exciting news about our new AI Employee system! 🚀

We're launching March 10 with a comprehensive platform designed for small business owners. The system automates routine tasks including email management, task processing, and social media posting.

Our goal is to help businesses save time and focus on high-impact work. Early adopters report 40% time savings in the first week.

Ready to transform your workflow? Let's connect and discuss! 🤝

#AIEmployee #Automation #SmallBusiness #Productivity
```

**Instagram:**
```
✨ AI Employee System launches March 10!

Transform how you work with automated:
📧 Email management
✅ Task processing
📱 Social media posting

Perfect for small business owners ready to scale! 🚀

Tag someone who needs this! 👇

#AIEmployee #Automation #SmallBusiness #Productivity #Entrepreneur #TechStartup #BusinessGrowth #Innovation #AI #DigitalTransformation
```

## Error Handling

### Platform API Unavailable

```python
try:
    post_to_twitter(content)
except APIUnavailableError:
    handle_failed_post('twitter', content, "API unavailable")
    # Queue for retry
    queue_for_retry('twitter', content)
```

### Content Validation Failed

```python
valid, issues = validate_linkedin_content(content)
if not valid:
    handle_failed_post('linkedin', content, f"Validation failed: {issues}")
    # Return to draft for revision
    revise_content(content, issues)
```

## Human Escalation Rules

**Escalate When:**
1. Multiple failed posts on same platform (systematic issue)
2. Authentication failures (credentials need refresh)
3. Content rejected by platform (policy violation)
4. Scheduled posts not posting (scheduling system issue)
5. Negative engagement on posts (PR concern)

## Related Skills

- `twitter_skill` - Twitter posting
- `linkedin_skill` - LinkedIn posting
- `instagram_skill` - Instagram posting
- `hitl_skill` - Approval workflows
