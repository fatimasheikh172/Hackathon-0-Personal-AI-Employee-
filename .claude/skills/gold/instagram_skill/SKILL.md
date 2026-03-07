# Instagram Skill

## Description

This skill generates Instagram captions, enforces hashtag rules (max 10), creates visual-focused content, manages rate limiting (max 5 posts/day), handles image requirements, and implements DRY_RUN mode.

## When To Use This Skill

- When creating Instagram content
- When generating post captions
- When managing hashtags
- When scheduling Instagram posts
- When creating visual content strategies

## Step By Step Instructions

### 1. Generate Captions

```python
def generate_instagram_caption(topic, image_description=None, style='engaging'):
    """Generate Instagram caption from topic."""
    
    caption = {
        'hook': '',        # First line to grab attention
        'body': '',        # Main content
        'cta': '',         # Call to action
        'hashtags': [],    # Max 10 hashtags
        'emoji_count': 0
    }
    
    # Generate hook (critical for Instagram)
    hooks = [
        f"✨ {topic} is here!",
        f"🔥 Big news about {topic}",
        f"💡 Here's the thing about {topic}...",
        f"📸 Capturing the moment: {topic}",
        f"🎉 Excited to share: {topic}",
    ]
    caption['hook'] = random.choice(hooks)
    
    # Generate body based on image description
    if image_description:
        caption['body'] = create_visual_caption(image_description, max_sentences=3)
    else:
        caption['body'] = generate_from_topic(topic, max_sentences=3)
    
    # Add call to action
    ctas = [
        "Double tap if you agree! ❤️",
        "Share your thoughts below! 👇",
        "Tag someone who needs to see this! 🔔",
        "Save this for later! 📌",
        "Link in bio for more! 🔗",
    ]
    caption['cta'] = random.choice(ctas)
    
    # Generate hashtags (max 10)
    caption['hashtags'] = generate_hashtags(topic, max_count=10)
    
    return format_instagram_caption(caption)
```

**Caption Structure:**
```
[Hook with emoji]

[Body - 2-3 sentences]

[Call to action]

[Hashtags - up to 10]
```

### 2. Hashtag Rules (Max 10)

**Hashtag Guidelines:**
- Maximum 10 hashtags per post (Instagram allows 30, but 10 is optimal)
- Mix of popular and niche hashtags
- Relevant to content only
- No banned or spammy hashtags

```python
def generate_hashtags(topic, max_count=10):
    """Generate relevant hashtags for topic."""
    
    # Hashtag categories
    hashtag_pools = {
        'broad': ['business', 'entrepreneur', 'success', 'motivation'],
        'niche': ['smallbusiness', 'startup', 'growth', 'innovation'],
        'community': ['businesscommunity', 'entrepreneurlife', 'hustle'],
        'topic_specific': []  # Generated from topic
    }
    
    # Generate topic-specific hashtags
    topic_words = topic.lower().split()
    hashtag_pools['topic_specific'] = [
        f"#{word}" for word in topic_words if len(word) > 3
    ]
    
    # Select hashtags strategically
    selected = []
    
    # Always include 2-3 topic-specific
    selected.extend(hashtag_pools['topic_specific'][:3])
    
    # Add 2-3 broad
    selected.extend(random.sample(hashtag_pools['broad'], min(3, len(hashtag_pools['broad']))))
    
    # Add 2-3 niche
    selected.extend(random.sample(hashtag_pools['niche'], min(3, len(hashtag_pools['niche']))))
    
    # Add 2-3 community
    selected.extend(random.sample(hashtag_pools['community'], min(3, len(hashtag_pools['community']))))
    
    # Format and limit
    hashtags = [f"#{h}" if not h.startswith('#') else h for h in selected]
    return hashtags[:max_count]
```

**Hashtag Validation:**
```python
def validate_hashtags(hashtags):
    """Validate hashtag rules."""
    issues = []
    
    # Check count
    if len(hashtags) > 10:
        issues.append(f"Too many hashtags: {len(hashtags)} (max 10)")
    
    # Check for banned hashtags
    banned = ['like4like', 'follow4follow', 'f4f', 'l4l']
    for tag in hashtags:
        if tag.lower().replace('#', '') in banned:
            issues.append(f"Banned hashtag: {tag}")
    
    # Check length (max 30 chars per hashtag)
    for tag in hashtags:
        if len(tag) > 30:
            issues.append(f"Hashtag too long: {tag}")
    
    # Check for spaces
    for tag in hashtags:
        if ' ' in tag:
            issues.append(f"Hashtag contains space: {tag}")
    
    return len(issues) == 0, issues
```

### 3. Visual-Focused Content

**Instagram is Visual-First:**
- Caption should complement the image, not describe it entirely
- Keep text concise (let the image speak)
- Use emojis to add visual interest
- Create captions that encourage engagement

```python
def create_visual_caption(image_description, max_sentences=3):
    """Create caption focused on visual content."""
    
    # Analyze image description
    visual_elements = extract_visual_elements(image_description)
    
    # Create caption that complements (not describes) the image
    caption_templates = [
        f"Behind every great {visual_elements['subject']} is a story worth sharing.",
        f"Moments like these remind us why we do what we do.",
        f"The {visual_elements['setting']} says it all.",
        f"When {visual_elements['action']} happens, magic follows.",
    ]
    
    caption = random.choice(caption_templates)
    
    # Add context if needed
    if len(caption.split()) < 20:
        caption += f" {generate_context_sentence(image_description)}"
    
    return caption
```

**Image-Caption Alignment:**
```python
def check_image_caption_alignment(caption, image_description):
    """Ensure caption aligns with image."""
    # Extract key themes from both
    caption_themes = extract_themes(caption)
    image_themes = extract_themes(image_description)
    
    # Check for major mismatches
    if not any(theme in image_themes for theme in caption_themes):
        return False, "Caption themes don't match image"
    
    return True, "Caption aligns with image"
```

### 4. Rate Limiting: Max 5 Posts/Day

```python
# Instagram posting log
instagram_post_log = []

def check_instagram_rate_limit():
    """Check if rate limit allows posting."""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Count posts today
    today_count = sum(1 for t in instagram_post_log if t > today_start)
    
    if today_count >= 5:
        return False, today_count
    
    return True, today_count

def get_instagram_wait_time():
    """Calculate wait time until tomorrow."""
    now = datetime.now()
    tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    wait_seconds = (tomorrow - now).seconds
    wait_hours = wait_seconds / 3600
    
    return max(1, int(wait_hours))

def log_instagram_post():
    """Log Instagram post for rate limiting."""
    instagram_post_log.append(datetime.now())
    
    # Clean old entries (older than 24 hours)
    cutoff = datetime.now() - timedelta(days=1)
    instagram_post_log[:] = [t for t in instagram_post_log if t > cutoff]
```

### 5. Image Requirements

**Image Specifications:**
```python
IMAGE_REQUIREMENTS = {
    'formats': ['jpg', 'jpeg', 'png'],
    'min_width': 320,
    'max_width': 1080,
    'min_height': 320,
    'max_height': 1350,
    'aspect_ratios': {
        'square': (1, 1),
        'portrait': (4, 5),
        'landscape': (1.91, 1),
    },
    'max_file_size': 30 * 1024 * 1024,  # 30MB
    'min_file_size': 100,  # 100 bytes
}
```

**Image Validation:**
```python
def validate_image(image_path):
    """Validate image meets Instagram requirements."""
    issues = []
    
    # Check file exists
    if not os.path.exists(image_path):
        return False, ["Image file not found"]
    
    # Check format
    ext = os.path.splitext(image_path)[1].lower()
    if ext not in IMAGE_REQUIREMENTS['formats']:
        issues.append(f"Unsupported format: {ext}")
    
    # Check file size
    file_size = os.path.getsize(image_path)
    if file_size > IMAGE_REQUIREMENTS['max_file_size']:
        issues.append(f"File too large: {file_size / 1024 / 1024:.1f}MB (max 30MB)")
    if file_size < IMAGE_REQUIREMENTS['min_file_size']:
        issues.append(f"File too small")
    
    # Check dimensions
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            
            if width < IMAGE_REQUIREMENTS['min_width']:
                issues.append(f"Width too small: {width}px (min {IMAGE_REQUIREMENTS['min_width']})")
            if width > IMAGE_REQUIREMENTS['max_width']:
                issues.append(f"Width too large: {width}px (max {IMAGE_REQUIREMENTS['max_width']})")
            if height < IMAGE_REQUIREMENTS['min_height']:
                issues.append(f"Height too small: {height}px (min {IMAGE_REQUIREMENTS['min_height']})")
            if height > IMAGE_REQUIREMENTS['max_height']:
                issues.append(f"Height too large: {height}px (max {IMAGE_REQUIREMENTS['max_height']})")
    except Exception as e:
        issues.append(f"Cannot read image: {e}")
    
    return len(issues) == 0, issues
```

### 6. DRY_RUN Rules

```python
def post_to_instagram(caption, image_path=None, dry_run=True):
    """Post to Instagram with DRY_RUN support."""
    
    # Validate caption
    valid, issues = validate_hashtags(extract_hashtags(caption))
    if not valid:
        return {
            'success': False,
            'error': '; '.join(issues)
        }
    
    # Validate image if provided
    if image_path:
        valid, issues = validate_image(image_path)
        if not valid:
            return {
                'success': False,
                'error': '; '.join(issues)
            }
    
    # Check rate limit
    can_post, count = check_instagram_rate_limit()
    if not can_post:
        wait_hours = get_instagram_wait_time()
        return {
            'success': False,
            'error': f'Daily limit reached (5/day). Wait {wait_hours} hours.',
            'retry_after': wait_hours
        }
    
    # DRY_RUN mode
    if dry_run:
        draft_file = save_instagram_draft(caption, image_path)
        return {
            'success': True,
            'dry_run': True,
            'draft_file': draft_file,
            'message': 'Instagram post generated (DRY_RUN mode - not posted)'
        }
    
    # Actually post (requires Instagram API integration)
    try:
        client = get_instagram_client()
        result = client.post_media(
            image_path=image_path,
            caption=caption
        )
        
        log_instagram_post()
        
        return {
            'success': True,
            'post_id': result['id'],
            'url': f"https://instagram.com/p/{result['shortcode']}"
        }
        
    except Exception as e:
        log_error(f"Instagram post failed: {e}")
        return {
            'success': False,
            'error': str(e)
        }
```

**When to Use DRY_RUN:**
```python
def should_use_dry_run(post_details):
    """Determine if DRY_RUN mode should be used."""
    reasons = []
    
    # First post of the day
    if is_first_post_today():
        reasons.append("First post today")
    
    # New content type
    if is_new_content_type(post_details.get('type')):
        reasons.append("New content type")
    
    # Outside optimal posting time
    if not is_optimal_instagram_time():
        reasons.append("Outside optimal time")
    
    # No approval on file
    if not has_approval(post_details):
        reasons.append("No approval on file")
    
    return len(reasons) > 0, reasons
```

## Examples

### Example 1: Product Launch Caption

**Input:**
```python
topic = "AI Employee Launch"
image_description = "Product screenshot showing dashboard"
```

**Generated Caption:**
```
✨ AI Employee Launch is here!

Our new system transforms how businesses handle daily tasks. The 
dashboard makes automation simple and intuitive.

Tag someone who needs this! 🔔

#AIEmployee #Automation #Business #Productivity #Innovation #Tech 
#Startup #Entrepreneur #DigitalTransformation #AI
```

**Validation:**
```python
hashtags = 10  # ✓ (max 10)
length = 280  # ✓ (good length)
emoji = 2  # ✓
```

### Example 2: Image Validation

**Processing:**
```python
valid, issues = validate_image('posts/product_launch.jpg')
# Returns: (True, []) if valid
# Returns: (False, ['Width too large: 2000px']) if invalid
```

## Error Handling

### Image Not Found

```python
if not os.path.exists(image_path):
    return {
        'success': False,
        'error': 'Image file not found',
        'action': 'provide_valid_image'
    }
```

### Rate Limit Exceeded

```python
can_post, count = check_instagram_rate_limit()
if not can_post:
    wait_hours = get_instagram_wait_time()
    return {
        'success': False,
        'error': f'Daily limit (5 posts) reached. Try again in {wait_hours} hours',
        'retry_after': wait_hours
    }
```

### Hashtag Validation Failed

```python
valid, issues = validate_hashtags(hashtags)
if not valid:
    return {
        'success': False,
        'error': '; '.join(issues),
        'action': 'fix_hashtags'
    }
```

## Human Escalation Rules

**Escalate to Human:**
1. Image validation failures (need new image)
2. Rate limit consistently reached
3. Posting failures after retry
4. Captions for sensitive topics
5. Posts mentioning clients/partners (need approval)
6. Response to comments requiring human judgment

**Escalation Format:**
```markdown
---
approval_type: instagram_post
caption_preview: <first 100 chars>
image: <image_path>
timestamp: 2026-03-07 10:00:00
---

# Instagram Post Approval Required

**Caption:** [Full caption]
**Image:** [Image path/preview]
**Hashtags:** [List of hashtags]

Please review and approve before posting.
```

## Related Skills

- `twitter_skill` - For Twitter content
- `linkedin_skill` - For LinkedIn content
- `social_content_skill` - For multi-platform strategy
- `hitl_skill` - For approval workflows
