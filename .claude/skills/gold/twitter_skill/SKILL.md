# Twitter Skill

## Description

This skill generates tweets, enforces character limits (max 280), maintains professional but engaging tone, manages rate limiting (max 5 posts/hour), implements DRY_RUN mode, and handles session management.

## When To Use This Skill

- When creating Twitter/X content
- When posting company updates
- When engaging with Twitter audience
- When scheduling tweet content
- When testing tweets before posting

## Step By Step Instructions

### 1. Generate Tweets

```python
def generate_tweet(topic, style='professional'):
    """Generate a tweet from topic."""
    
    # Tweet structure
    tweet = {
        'content': '',
        'hashtags': [],
        'mentions': [],
        'media': None
    }
    
    # Generate content based on topic
    content_templates = [
        f"Exciting news: {topic}! 🚀",
        f"Here's what's happening with {topic}:",
        f"Big announcement: {topic}",
        f"Thoughts on {topic}:",
        f"Just launched: {topic}! Check it out.",
    ]
    
    tweet['content'] = random.choice(content_templates)
    
    # Add hashtags (max 2 for Twitter)
    tweet['hashtags'] = generate_hashtags(topic, max_count=2)
    
    # Validate length
    full_tweet = format_tweet(tweet)
    if len(full_tweet) > 280:
        tweet = trim_tweet(tweet, max_length=280)
    
    return tweet
```

**Tweet Best Practices:**
- Lead with the most important information
- Use 1-2 relevant hashtags (not more)
- Include emoji sparingly (1-2 max)
- Add call-to-action when relevant
- Tag relevant accounts when appropriate

### 2. Character Limit Enforcement

**CRITICAL: Max 280 Characters**

```python
def validate_tweet_length(tweet):
    """Validate tweet is within 280 character limit."""
    full_tweet = format_tweet(tweet)
    length = len(full_tweet)
    
    if length > 280:
        return False, f"Tweet too long: {length} chars (max 280)"
    elif length > 250:
        return True, f"Warning: {length} chars (close to limit)"
    else:
        return True, f"Good length: {length} chars"
```

**Trim Function:**
```python
def trim_tweet(tweet, max_length=280):
    """Trim tweet to fit character limit."""
    content = tweet['content']
    
    # First, try removing hashtags
    if tweet.get('hashtags'):
        tweet['hashtags'] = tweet['hashtags'][:1]  # Keep only 1
    
    # Recalculate
    full_tweet = format_tweet(tweet)
    if len(full_tweet) <= max_length:
        return tweet
    
    # Trim content
    max_content_length = max_length - 20  # Reserve space for hashtags
    tweet['content'] = content[:max_content_length-3] + '...'
    
    return tweet
```

**Format Tweet:**
```python
def format_tweet(tweet):
    """Format tweet with hashtags."""
    content = tweet['content']
    
    # Add hashtags
    if tweet.get('hashtags'):
        hashtag_str = ' '.join(f"#{h}" for h in tweet['hashtags'])
        content = f"{content}\n\n{hashtag_str}"
    
    return content
```

### 3. Professional But Engaging Tone

**Tone Guidelines:**
- **Professional:** Business-appropriate language
- **Engaging:** Interesting, not boring
- **Concise:** Get to the point quickly
- **Authentic:** Sound human, not corporate
- **Positive:** Focus on value and solutions

**Language Do's:**
- ✅ Use active voice
- ✅ Include specific details
- ✅ Add relevant emoji (1-2)
- ✅ Ask questions to engage
- ✅ Share insights and learnings

**Language Don'ts:**
- ❌ Overly formal/corporate speak
- ❌ Excessive hashtags (#news #update #company #tech #ai = too many)
- ❌ Controversial topics
- ❌ Negative comments
- ❌ All caps (except for emphasis on 1-2 words)

```python
def check_tweet_tone(tweet_content):
    """Validate tweet tone."""
    issues = []
    
    # Check for corporate speak
    corporate_phrases = ['leverage', 'synergy', 'paradigm shift', 'circle back']
    for phrase in corporate_phrases:
        if phrase.lower() in tweet_content.lower():
            issues.append(f"Corporate speak detected: {phrase}")
    
    # Check emoji count
    emoji_count = sum(1 for char in tweet_content if char in '😀😃😄😊👍🎉🚀📈🤝💡')
    if emoji_count > 2:
        issues.append(f"Too many emojis: {emoji_count}")
    
    # Check hashtag count
    hashtag_count = tweet_content.count('#')
    if hashtag_count > 2:
        issues.append(f"Too many hashtags: {hashtag_count}")
    
    return len(issues) == 0, issues
```

### 4. Rate Limiting: Max 5 Posts/Hour

```python
# Tweet posting log
tweet_post_log = []

def check_tweet_rate_limit():
    """Check if rate limit allows posting."""
    now = datetime.now()
    one_hour_ago = now - timedelta(hours=1)
    
    # Count tweets in last hour
    hour_count = sum(1 for t in tweet_post_log if t > one_hour_ago)
    
    if hour_count >= 5:
        return False, hour_count
    
    return True, hour_count

def get_tweet_wait_time():
    """Calculate wait time until rate limit resets."""
    if not tweet_post_log:
        return 0
    
    oldest_in_hour = min(tweet_post_log)
    wait_until = oldest_in_hour + timedelta(hours=1)
    wait_minutes = (wait_until - datetime.now()).seconds / 60
    
    return max(1, int(wait_minutes))

def log_tweet_post():
    """Log tweet post for rate limiting."""
    tweet_post_log.append(datetime.now())
    
    # Clean old entries
    cutoff = datetime.now() - timedelta(hours=1)
    tweet_post_log[:] = [t for t in tweet_post_log if t > cutoff]
```

### 5. DRY_RUN Rules

**DRY_RUN Mode:**
- When enabled, tweets are generated but NOT posted
- Used for testing and approval workflows
- Always use DRY_RUN for first-time topics
- Always use DRY_RUN outside business hours

```python
def post_tweet(tweet_content, dry_run=True):
    """Post tweet with DRY_RUN support."""
    
    # Validate tweet
    valid, message = validate_tweet_length(tweet_content)
    if not valid:
        return {
            'success': False,
            'error': message
        }
    
    # Check rate limit
    can_post, count = check_tweet_rate_limit()
    if not can_post:
        wait_time = get_tweet_wait_time()
        return {
            'success': False,
            'error': f'Rate limit reached. Wait {wait_time} minutes.',
            'retry_after': wait_time
        }
    
    # DRY_RUN mode
    if dry_run:
        draft_file = save_tweet_draft(tweet_content)
        return {
            'success': True,
            'dry_run': True,
            'draft_file': draft_file,
            'message': 'Tweet generated (DRY_RUN mode - not posted)'
        }
    
    # Actually post
    try:
        client = get_twitter_client()
        result = client.post(status=tweet_content)
        
        log_tweet_post()
        
        return {
            'success': True,
            'tweet_id': result['id'],
            'url': f"https://twitter.com/status/{result['id']}"
        }
        
    except Exception as e:
        log_error(f"Tweet post failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
```

**When to Use DRY_RUN:**
```python
def should_use_dry_run(tweet_details):
    """Determine if DRY_RUN mode should be used."""
    reasons = []
    
    # First time posting this topic
    if is_new_topic(tweet_details.get('topic')):
        reasons.append("New topic")
    
    # Outside business hours
    if is_outside_business_hours():
        reasons.append("Outside business hours")
    
    # Sensitive topic
    if is_sensitive_topic(tweet_details.get('topic')):
        reasons.append("Sensitive topic")
    
    # No approval on file
    if not has_approval(tweet_details):
        reasons.append("No approval on file")
    
    return len(reasons) > 0, reasons
```

### 6. Session Management

```python
# Twitter session handling
twitter_session = {
    'authenticated': False,
    'token': None,
    'token_expiry': None,
    'last_activity': None,
}

def get_twitter_client():
    """Get authenticated Twitter client."""
    
    # Check if session is valid
    if not is_session_valid():
        authenticate_twitter()
    
    # Update last activity
    twitter_session['last_activity'] = datetime.now()
    
    return TwitterClient(token=twitter_session['token'])

def is_session_valid():
    """Check if Twitter session is valid."""
    if not twitter_session['authenticated']:
        return False
    
    if not twitter_session['token']:
        return False
    
    # Check token expiry
    if twitter_session['token_expiry']:
        if datetime.now() > twitter_session['token_expiry']:
            return False
    
    # Check session timeout (30 minutes of inactivity)
    if twitter_session['last_activity']:
        timeout = timedelta(minutes=30)
        if datetime.now() - twitter_session['last_activity'] > timeout:
            return False
    
    return True

def authenticate_twitter():
    """Authenticate with Twitter API."""
    try:
        client = TwitterClient(
            api_key=TWITTER_API_KEY,
            api_secret=TWITTER_API_SECRET,
            access_token=TWITTER_ACCESS_TOKEN,
            access_token_secret=TWITTER_ACCESS_TOKEN_SECRET
        )
        
        twitter_session['authenticated'] = True
        twitter_session['token'] = client.get_token()
        twitter_session['token_expiry'] = datetime.now() + timedelta(hours=2)
        
        return True
        
    except Exception as e:
        log_error(f"Twitter authentication failed: {e}")
        twitter_session['authenticated'] = False
        return False
```

## Examples

### Example 1: Generate Product Launch Tweet

**Input:**
```python
topic = "AI Employee Product Launch"
```

**Generated Tweet:**
```
Exciting news: AI Employee Product Launch! 🚀

Our new system automates routine business tasks so you can focus on 
what matters most.

#AIEmployee #Automation
```

**Validation:**
```python
length = len(tweet)  # 178 chars ✓
hashtags = 2  # ✓
emoji = 1  # ✓
tone_ok, issues = check_tweet_tone(tweet)  # True ✓
```

### Example 2: DRY_RUN Mode

**Processing:**
```python
result = post_tweet(tweet_content, dry_run=True)
# Returns: {
#     'success': True,
#     'dry_run': True,
#     'draft_file': 'Drafts/tweet_draft_20260307_100000.md',
#     'message': 'Tweet generated (DRY_RUN mode - not posted)'
# }
```

## Error Handling

### Authentication Error

```python
if not is_session_valid():
    if not authenticate_twitter():
        return {
            'success': False,
            'error': 'Twitter authentication failed',
            'action': 'check_credentials'
        }
```

### Rate Limit Error

```python
can_post, count = check_tweet_rate_limit()
if not can_post:
    wait_time = get_tweet_wait_time()
    return {
        'success': False,
        'error': f'Rate limit exceeded (5/hour). Wait {wait_time} min',
        'retry_after': wait_time
    }
```

### Length Validation Error

```python
valid, message = validate_tweet_length(tweet)
if not valid:
    return {
        'success': False,
        'error': message,
        'action': 'trim_and_retry'
    }
```

## Human Escalation Rules

**Escalate to Human:**
1. Authentication failures (credentials may need refresh)
2. Rate limit consistently reached
3. Tweet posting failures after retry
4. Sensitive topic tweets (financial, legal, HR)
5. Tweets mentioning specific clients/partners
6. Response to negative mentions or controversies

**Escalation Format:**
```markdown
---
alert_type: twitter_issue
issue: <description>
timestamp: 2026-03-07 10:00:00
---

# Twitter Issue

**Issue:** Authentication failed
**Impact:** Cannot post tweets
**Recommended Action:** Check Twitter API credentials
```

## Related Skills

- `linkedin_skill` - For LinkedIn content
- `instagram_skill` - For Instagram content
- `social_content_skill` - For multi-platform strategy
- `hitl_skill` - For approval workflows
