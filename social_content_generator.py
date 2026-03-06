#!/usr/bin/env python3
"""
Social Content Generator - 2026 Version
AI-powered content generation for Twitter/X, LinkedIn, and Instagram
Uses Gemini API for intelligent content creation
"""

import os
import sys
import json
import random
import re
import argparse
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Try to import Google Generative AI
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

# Load environment variables
load_dotenv()

# Configuration
VAULT_PATH = Path(os.getenv("VAULT_PATH", r"F:\AI_Employee_Vault"))
LOGS_FOLDER = VAULT_PATH / "Logs"
SOCIAL_PENDING = VAULT_PATH / "Social_Content" / "pending"
SOCIAL_DRAFTS = VAULT_PATH / "Social_Content" / "drafts"
COMPANY_HANDBOOK = VAULT_PATH / "Company_Handbook.md"
BUSINESS_GOALS = VAULT_PATH / "Business_Goals.md"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"

# Environment settings
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def ensure_folders_exist():
    """Ensure all required folders exist"""
    for folder in [LOGS_FOLDER, SOCIAL_PENDING, SOCIAL_DRAFTS]:
        folder.mkdir(parents=True, exist_ok=True)


def log_action(action_type, details, success=True):
    """Log a generator action"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "[OK]" if success else "[ERROR]"
    log_entry = f"[{timestamp}] {status} {action_type}: {details}"
    print(log_entry)


def load_company_context():
    """Load company context from files"""
    context = {
        "company_name": "AI Employee",
        "achievements": [],
        "goals": [],
        "current_tasks": 0
    }
    
    # Read Company Handbook
    if COMPANY_HANDBOOK.exists():
        try:
            with open(COMPANY_HANDBOOK, "r", encoding="utf-8") as f:
                content = f.read()
            
            name_match = re.search(r'#?\s*(\w+\s*Employee)', content)
            if name_match:
                context["company_name"] = name_match.group(1)
        except Exception:
            pass
    
    # Read Dashboard
    if DASHBOARD_FILE.exists():
        try:
            with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            
            tasks_match = re.search(r'Completed Tasks:\s*(\d+)', content)
            if tasks_match:
                context["current_tasks"] = int(tasks_match.group(1))
                context["achievements"].append(f"Completed {tasks_match.group(1)} tasks")
        except Exception:
            pass
    
    # Read Business Goals
    if BUSINESS_GOALS.exists():
        try:
            with open(BUSINESS_GOALS, "r", encoding="utf-8") as f:
                content = f.read()
            
            revenue_match = re.search(r'Monthly goal:.*?\$?([\d,]+)', content)
            if revenue_match:
                context["goals"].append(f"Monthly revenue target: ${revenue_match.group(1)}")
        except Exception:
            pass
    
    return context


def generate_with_gemini(prompt, topic):
    """Generate content using Gemini AI"""
    if not HAS_GENAI:
        log_action("gemini_unavailable", "google-generativeai not installed", success=False)
        return None
    
    if not GEMINI_API_KEY:
        log_action("gemini_no_key", "GEMINI_API_KEY not set in .env", success=False)
        return None
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-pro')
        
        response = model.generate_content(prompt)
        return response.text
    
    except Exception as e:
        log_action("gemini_error", str(e), success=False)
        return None


def generate_twitter_content(topic, context=None):
    """
    Generate Twitter/X content (max 280 chars, punchy)
    """
    print("\n" + "=" * 60)
    print("GENERATING TWITTER CONTENT")
    print("=" * 60)
    print(f"Topic: {topic}")
    
    company_name = context["company_name"] if context else "AI Employee"
    
    # AI-powered generation prompt
    ai_prompt = f"""Generate a professional business tweet about: {topic}

Requirements:
- Maximum 280 characters
- Punchy and engaging tone
- Include 2-3 relevant hashtags
- Mention {company_name} if relevant
- No emojis or maximum 1 professional emoji

Tweet:"""

    # Try AI generation first
    content = generate_with_gemini(ai_prompt, topic)
    
    if content:
        content = content.strip()
        # Ensure under 280 chars
        if len(content) > 280:
            content = content[:277] + "..."
        if len(content) <= 280:
            log_action("twitter_generated", f"AI-generated: {content[:50]}...")
            return content
    
    # Fallback templates
    templates = [
        f"🚀 {topic}\n\nDriving innovation at {company_name}. #BusinessGrowth #AI #Innovation",
        f"💼 Update: {topic}\n\nCommitted to excellence. #Productivity #Success",
        f"📈 {topic}\n\nBuilding the future with {company_name}. #FutureOfWork #Automation",
        f"✨ {topic}\n\nExcellence is our standard. #ProfessionalExcellence #Business",
    ]
    
    content = random.choice(templates)
    
    if len(content) > 280:
        content = content[:277] + "..."
    
    log_action("twitter_generated", f"Template: {content[:50]}...")
    return content


def generate_linkedin_content(topic, context=None):
    """
    Generate LinkedIn content (professional, 150-300 words)
    """
    print("\n" + "=" * 60)
    print("GENERATING LINKEDIN CONTENT")
    print("=" * 60)
    print(f"Topic: {topic}")
    
    company_name = context["company_name"] if context else "AI Employee"
    achievements = context.get("achievements", []) if context else []
    
    # AI-powered generation prompt
    ai_prompt = f"""Generate a professional LinkedIn post about: {topic}

Requirements:
- 150-300 words
- Professional, business-appropriate tone
- Include relevant industry insights
- Add 3-5 professional hashtags at the end
- Mention {company_name} where appropriate
- Start with an engaging hook
- Include a call-to-action or thought-provoking question

Company achievements: {', '.join(achievements) if achievements else 'Continuous growth and innovation'}

Post:"""

    # Try AI generation first
    content = generate_with_gemini(ai_prompt, topic)
    
    if content:
        content = content.strip()
        word_count = len(content.split())
        if 100 <= word_count <= 400:
            log_action("linkedin_generated", f"AI-generated: {word_count} words")
            return content
    
    # Fallback templates
    achievement_text = ""
    if achievements:
        achievement_text = f"\n\nKey achievements include: {', '.join(achievements)}."
    
    templates = [
        f"""🚀 Business Update

{topic}

At {company_name}, we're committed to driving innovation and delivering exceptional results. Our team continues to push boundaries and set new standards in the industry.{achievement_text}

We believe that success comes from consistent effort, attention to detail, and an unwavering focus on value creation.

What strategies is your team using to drive innovation?

#ProfessionalExcellence #BusinessGrowth #Innovation #Leadership #IndustryInsights""",

        f"""💼 Professional Insight

{topic}

The business landscape continues to evolve, and staying ahead requires adaptability, strategic thinking, and dedication to excellence.

At {company_name}, we've embraced these principles to deliver outstanding outcomes for our stakeholders.{achievement_text}

Looking ahead, we're focused on:
• Continuous improvement
• Innovation in every task
• Building lasting partnerships

How is your organization preparing for the future?

#BusinessStrategy #Growth #TeamWork #Success #ProfessionalDevelopment""",

        f"""📈 Company Milestone

{topic}

We're proud to share this progress with our network. This achievement reflects our team's dedication and collaborative spirit.

At {company_name}, excellence isn't just a goal—it's our standard.{achievement_text}

Thank you to our team, partners, and stakeholders for their continued support.

#CompanyNews #Achievement #BusinessExcellence #Innovation #TeamSuccess""",
    ]
    
    content = random.choice(templates)
    word_count = len(content.split())
    log_action("linkedin_generated", f"Template: {word_count} words")
    return content


def generate_instagram_content(topic, context=None):
    """
    Generate Instagram content (hashtag-heavy caption)
    """
    print("\n" + "=" * 60)
    print("GENERATING INSTAGRAM CONTENT")
    print("=" * 60)
    print(f"Topic: {topic}")
    
    company_name = context["company_name"] if context else "AI Employee"
    
    # AI-powered generation prompt
    ai_prompt = f"""Generate an Instagram caption about: {topic}

Requirements:
- Engaging, visual language
- Include 1-2 relevant emojis at the start
- Write 2-3 short paragraphs
- Add 12-15 relevant hashtags at the end
- Keep it positive and inspiring
- Mention {company_name} naturally

Caption:"""

    # Try AI generation first
    content = generate_with_gemini(ai_prompt, topic)
    
    if content:
        content = content.strip()
        # Check if it has hashtags
        if "#" in content and len(content) <= 2200:
            log_action("instagram_generated", f"AI-generated caption")
            return content
    
    # Fallback templates
    emojis = ["🚀", "✨", "💡", "🎯", "📈", "🌟", "🏆", "💼"]
    
    hashtags = [
        "#BusinessGrowth", "#Innovation", "#Success", "#Motivation",
        "#Leadership", "#Productivity", "#AI", "#Automation", "#Entrepreneur",
        "#Mindset", "#Growth", "#Inspiration", "#Technology", "#FutureOfWork",
        "#DigitalTransformation", "#BusinessStrategy", "#Excellence", "#TeamWork"
    ]
    
    selected_hashtags = " ".join(random.sample(hashtags, 12))
    
    templates = [
        f"""{random.choice(emojis)} {topic}

Driving innovation and excellence at {company_name}. Every day brings new opportunities to grow and achieve more.

Success is built on consistent effort and unwavering commitment to quality.

{selected_hashtags}""",

        f"""{random.choice(emojis)} Exciting updates: {topic}

We're pushing boundaries and setting new standards. Join us on this journey of innovation and growth.

The future of work is here, and we're leading the way.

{selected_hashtags}""",

        f"""{random.choice(emojis)} Focus on excellence: {topic}

At {company_name}, we believe in delivering value through smart solutions and dedicated effort.

Together, we achieve more.

{selected_hashtags}""",
    ]
    
    content = random.choice(templates)
    log_action("instagram_generated", f"Template caption generated")
    return content


def generate_all_platforms(topic, context=None):
    """
    Generate content for all platforms from a single topic
    Returns dict with platform-specific content
    """
    print("\n" + "=" * 60)
    print("GENERATING MULTI-PLATFORM CONTENT")
    print("=" * 60)
    print(f"Topic: {topic}")
    
    if context is None:
        context = load_company_context()
    
    content = {
        "topic": topic,
        "generated_at": datetime.now().isoformat(),
        "twitter": generate_twitter_content(topic, context),
        "linkedin": generate_linkedin_content(topic, context),
        "instagram": generate_instagram_content(topic, context)
    }
    
    return content


def save_content(content, save_as_draft=False):
    """
    Save generated content to pending or drafts folder
    Returns file path
    """
    if save_as_draft:
        folder = SOCIAL_DRAFTS
        prefix = "draft"
    else:
        folder = SOCIAL_PENDING
        prefix = "pending"
    
    ensure_folders_exist()
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{prefix}_social_{timestamp}.json"
    filepath = folder / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)
    
    log_action("content_saved", f"Saved to {filepath.name}")
    return filepath


def generate_from_business_update(update_type="achievement"):
    """
    Generate content from business update type
    """
    context = load_company_context()
    
    update_templates = {
        "achievement": f"Major milestone reached: {context['company_name']} continues to exceed expectations with innovative solutions and dedicated service.",
        "innovation": f"Introducing new automation capabilities that streamline workflows and boost productivity for businesses.",
        "growth": f"Expanding our reach and impact. {context['company_name']} is committed to delivering excellence at scale.",
        "team": f"Our team's dedication drives success. Celebrating the people behind our achievements.",
        "insight": f"Industry insight: The future of work is automated, intelligent, and human-centered.",
    }
    
    topic = update_templates.get(update_type, update_templates["achievement"])
    
    return generate_all_platforms(topic, context)


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Social Content Generator')
    parser.add_argument('--topic', type=str, help='Topic for content generation')
    parser.add_argument('--platform', type=str, choices=['twitter', 'linkedin', 'instagram', 'all'], 
                       default='all', help='Target platform')
    parser.add_argument('--draft', action='store_true', help='Save as draft')
    parser.add_argument('--update-type', type=str, dest='update_type',
                       choices=['achievement', 'innovation', 'growth', 'team', 'insight'],
                       help='Generate from business update type')
    parser.add_argument('--output', action='store_true', help='Print content without saving')
    args = parser.parse_args()

    print("=" * 60)
    print("Social Content Generator - AI Employee System (2026)")
    print("=" * 60)
    print(f"Vault: {VAULT_PATH}")
    print(f"AI Generation: {'Gemini API' if HAS_GENAI and GEMINI_API_KEY else 'Templates (AI unavailable)'}")
    print("=" * 60)

    ensure_folders_exist()

    # Load company context
    context = load_company_context()
    print(f"\nCompany: {context['company_name']}")
    print(f"Achievements: {context['achievements']}")

    # Generate content
    if args.update_type:
        content = generate_from_business_update(args.update_type)
    elif args.topic:
        if args.platform == 'all':
            content = generate_all_platforms(args.topic, context)
        elif args.platform == 'twitter':
            content = {"twitter": generate_twitter_content(args.topic, context)}
        elif args.platform == 'linkedin':
            content = {"linkedin": generate_linkedin_content(args.topic, context)}
        elif args.platform == 'instagram':
            content = {"instagram": generate_instagram_content(args.topic, context)}
        content["topic"] = args.topic
        content["generated_at"] = datetime.now().isoformat()
    else:
        # Default: generate from achievement
        content = generate_from_business_update("achievement")

    # Output or save
    if args.output:
        print("\n" + "=" * 60)
        print("GENERATED CONTENT")
        print("=" * 60)
        for platform, text in content.items():
            if platform not in ["topic", "generated_at"] and text:
                print(f"\n[{platform.upper()}]")
                print("-" * 40)
                print(text)
    else:
        # Save content
        filepath = save_content(content, save_as_draft=args.draft)
        print(f"\n[OK] Content saved to: {filepath}")
        
        if args.draft:
            print("Saved as DRAFT (review before posting)")
        else:
            print("Saved to PENDING (will be posted by scheduler)")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nGenerator stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
