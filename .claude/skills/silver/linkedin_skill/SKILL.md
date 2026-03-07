# LinkedIn Skill

## Description

This skill generates professional LinkedIn posts, maintains appropriate tone and length, determines optimal posting times, and manages content approval workflows.

## When To Use This Skill

- When creating LinkedIn content from topics
- When adapting content for professional audience
- When scheduling LinkedIn posts
- When managing LinkedIn engagement
- When requiring content approval before posting

## Step By Step Instructions

### 1. Generate LinkedIn Posts

```python
def generate_linkedin_post(topic, details=None, tone='professional'):
    """Generate a LinkedIn post from topic."""
    
    # Post structure
    post = {
        'hook': '',      # Opening line to grab attention
        'body': '',      # Main content (2-4 paragraphs)
        'cta': '',       # Call to action
        'hashtags': []   # 3-5 relevant hashtags
    }
    
    # Generate hook (first line is critical on LinkedIn)
    hooks = [
        f"Exciting news about {topic}!",
        f"Here's what we learned about {topic}:",
        f"Big announcement: {topic}",
        f"Thoughts on {topic}:",
    ]
    post['hook'] = random.choice(hooks)
    
    # Generate body based on details
    if details:
        post['body'] = expand_details(details, max_words=200)
    else:
        post['body'] = generate_from_topic(topic, max_words=200)
    
    # Add call to action
    ctas = [
        "What are your thoughts? Share in the comments! 👇",
        "Let's connect and discuss! 🤝",
        "Reach out if you'd like to learn more! 📩",
        "Tag someone who needs to see this! 🔔",
    ]
    post['cta'] = random.choice(ctas)
    
    # Generate hashtags
    post['hashtags'] = generate_hashtags(topic, max_count=5)
    
    return format_linkedin_post(post)
```

### 2. Professional Tone Rules

**Tone Guidelines:**
- **Professional but approachable:** Friendly yet business-appropriate
- **Positive and constructive:** Focus on solutions, not problems
- **Inclusive language:** Avoid jargon, be accessible
- **Authentic voice:** Sound human, not corporate robot
- **Value-driven:** Provide insights, not just promotion

**Language Do's:**
- ✅ Use "we" and "our team" for company announcements
- ✅ Share learnings and insights
- ✅ Acknowledge others (tag when relevant)
- ✅ Use emojis sparingly (1-3 per post)
- ✅ Include specific details and numbers

**Language Don'ts:**
- ❌ Overly salesy language ("Buy now!", "Best ever!")
- ❌ Controversial topics (politics, religion)
- ❌ Negative comments about competitors
- ❌ Excessive hashtags (max 5)
- ❌ All caps or excessive punctuation!!!
- ❌ Sensitive company information

```python
def check_professional_tone(text):
    """Validate post maintains professional tone."""
    issues = []
    
    # Check for salesy language
    salesy_words = ['buy now', 'best ever', 'amazing deal', 'limited offer']
    for word in salesy_words:
        if word.lower() in text.lower():
            issues.append(f"Salesy language detected: {word}")
    
    # Check emoji count
    emoji_count = sum(1 for char in text if char in '😀😃😄😊👍🎉🚀📈🤝')
    if emoji_count > 3:
        issues.append(f"Too many emojis: {emoji_count}")
    
    # Check for all caps
    words = text.split()
    caps_words = [w for w in words if w.isupper() and len(w) > 2]
    if len(caps_words) > 2:
        issues.append(f"Excessive caps: {caps_words}")
    
    return len(issues) == 0, issues
```

### 3. Post Length Rules

**Length Requirements:**
- **Minimum:** 150 words
- **Maximum:** 300 words
- **Optimal:** 200-250 words

**Structure:**
```
[Hook - 1 line, ~20 words]
[Line break]
[Body paragraph 1 - ~80 words]
[Line break]
[Body paragraph 2 - ~80 words]
[Line break]
[Call to action - ~20 words]
[Line break]
[Hashtags - 3-5 tags]
```

```python
def validate_post_length(post):
    """Validate post is within length requirements."""
    word_count = len(post.split())
    
    if word_count < 150:
        return False, f"Post too short: {word_count} words (min 150)"
    elif word_count > 300:
        return False, f"Post too long: {word_count} words (max 300)"
    else:
        return True, f"Good length: {word_count} words"
```

### 4. When to Post

**Optimal Posting Times:**
- **Best:** Tuesday-Thursday, 8-10 AM
- **Good:** Monday-Friday, 7-9 AM, 12-1 PM
- **Avoid:** Weekends, after 6 PM, before 6 AM

**Posting Schedule:**
```python
def is_good_posting_time():
    """Check if current time is good for LinkedIn posting."""
    now = datetime.now()
    
    # Avoid weekends
    if now.weekday() >= 5:  # Saturday=5, Sunday=6
        return False, "Avoid weekend posting"
    
    # Best times: 8-10 AM
    hour = now.hour
    if hour in [8, 9] and now.weekday() in [1, 2, 3]:  # Tue-Thu
        return True, "Optimal posting time"
    
    # Good times: 7-9 AM, 12-1 PM on weekdays
    if hour in [7, 8] or hour == 12:
        return True, "Good posting time"
    
    return False, "Outside optimal posting hours"
```

**Post Frequency:**
- Maximum 2 posts per day
- Minimum 3 posts per week (for active presence)
- Space posts at least 4 hours apart

### 5. Content Approval Rules

**Content Requiring Approval:**
1. All posts before first-time publishing
2. Posts mentioning company financials
3. Posts about partnerships or clients (tagging others)
4. Posts about sensitive topics (layoffs, controversies)
5. Posts with images/videos (visual review needed)

**Approval Workflow:**
```python
def submit_for_approval(post_content, post_type='standard'):
    """Submit LinkedIn post for human approval."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    approval_file = f"Pending_Approval/LINKEDIN_{timestamp}.md"
    
    content = f"""---
approval_type: linkedin_post
post_type: {post_type}
created_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
status: pending_approval
requires_visual_review: {has_media(post_content)}
---

# LinkedIn Post Approval Required

## Post Content
{post_content}

## Post Details
- **Word Count:** {len(post_content.split())}
- **Hashtags:** {extract_hashtags(post_content)}
- **Mentions:** {extract_mentions(post_content)}
- **Scheduled Time:** {get_suggested_post_time()}

## Approval Checklist
- [ ] Content is accurate
- [ ] Tone is appropriate
- [ ] No sensitive information
- [ ] Tags/mentions are correct
- [ ] Visuals approved (if applicable)

## Action Required
Please review and approve/reject this post.
"""
    
    write_vault_file(approval_file, content)
    return approval_file
```

**Approval Response Format:**
```markdown
---
decision: approved|rejected|needs_revision
reviewer: <name>
reviewed_at: <timestamp>
notes: <optional notes>
---
```

## Examples

### Example 1: Product Launch Post

**Input:**
```
Topic: New AI Employee Product Launch
Details: Launching Monday, automated task processing, email handling, 
social media management
```

**Generated Post:**
```
Exciting news about our new AI Employee system! 🚀

We're thrilled to announce the launch of our AI Employee platform this 
Monday. This innovative system automates routine business tasks including 
email management, social media posting, and task processing.

Our team has worked tirelessly to create a solution that helps businesses 
save time and focus on what matters most. The AI Employee handles 
incoming communications, drafts responses, and manages your digital 
presence across multiple platforms.

Ready to transform your workflow? Let's connect and discuss how AI can 
elevate your business! 🤝

#AIEmployee #Automation #BusinessEfficiency #Innovation #ProductLaunch
```

**Validation:**
```python
word_count = len(post.split())  # 156 words ✓
emoji_count = 2  # ✓
hashtags = 5  # ✓
tone_ok, issues = check_professional_tone(post)  # True ✓
```

### Example 2: Company Update Post

**Generated Post:**
```
Here's what we learned about business automation this week:

Automation isn't just about saving time—it's about enabling teams to 
focus on creative, strategic work that drives real value. Our latest 
data shows that businesses using AI assistants report 40% more time for 
high-impact projects.

The key is finding the right balance between automation and human 
oversight. That's why our system includes built-in approval workflows 
for sensitive actions.

What's your experience with business automation? Share your thoughts 
below! 👇

#BusinessAutomation #AI #Productivity #Leadership
```

## Error Handling

### Post Generation Failure

```python
try:
    post = generate_linkedin_post(topic, details)
except GenerationError as e:
    log_error(f"Post generation failed: {e}")
    # Create fallback post
    post = create_fallback_post(topic)
```

### Length Validation Failed

```python
valid, message = validate_post_length(post)
if not valid:
    log_warning(f"Post length issue: {message}")
    # Trim or expand as needed
    if 'too long' in message:
        post = trim_post(post, target_words=250)
    else:
        post = expand_post(post, target_words=200)
```

### Tone Check Failed

```python
tone_ok, issues = check_professional_tone(post)
if not tone_ok:
    log_warning(f"Tone issues: {issues}")
    # Flag for human review
    submit_for_approval(post, post_type='requires_revision')
```

## Human Escalation Rules

**Always Submit for Approval:**
1. First post on any new topic
2. Posts mentioning specific clients or partners
3. Posts with financial data or metrics
4. Posts about company changes (hiring, layoffs, restructuring)
5. Posts responding to controversies or negative events
6. Posts with images, videos, or documents attached
7. Posts scheduled outside business hours

**Escalation Format:**
```markdown
---
approval_type: linkedin_post
post_type: requires_approval
reason: <approval_reason>
timestamp: 2026-03-07 09:30:00
---

# LinkedIn Post Approval Required

**Topic:** [Topic]
**Reason for Approval:** [Why approval needed]
**Suggested Post Time:** [Date/Time]

## Post Content
[Full post content]

## Review Checklist
- [ ] Content accuracy
- [ ] Tone appropriateness
- [ ] No sensitive information
- [ ] Tags/mentions correct
```

## Related Skills

- `hitl_skill` - For approval workflows
- `twitter_skill` - For Twitter content adaptation
- `instagram_skill` - For Instagram content adaptation
- `social_content_skill` - For multi-platform content strategy
