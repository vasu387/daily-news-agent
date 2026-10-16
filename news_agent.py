
import html
import json
import os
import re
import smtplib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage

from openai import OpenAI

# ============================================================
# CONFIGURATION
# ============================================================

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "").strip()

MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"

MAX_SUMMARIES = 8
STORIES_PER_CATEGORY = 5
SUMMARIES_PER_CATEGORY = 2
TELEGRAM_CHUNK_LIMIT = 3900

IST = timezone(timedelta(hours=5, minutes=30))

FEEDS = {
    "🇮🇳 INDIA": (
        "https://news.google.com/rss/search?"
        "q=India+news&hl=en-IN&gl=IN&ceid=IN:en"
    ),
    "🤖 TECHNOLOGY & AI": (
        "https://news.google.com/rss/search?"
        "q=artificial+intelligence+OR+technology&hl=en-IN&gl=IN&ceid=IN:en"
    ),
    "🌍 WORLD": (
        "https://news.google.com/rss/search?"
        "q=world+news&hl=en-IN&gl=IN&ceid=IN:en"
    ),
    "🏏 CRICKET & SPORTS": (
        "https://news.google.com/rss/search?"
        "q=cricket+OR+sports&hl=en-IN&gl=IN&ceid=IN:en"
    ),
}

nvidia_client = (
    OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY,
        timeout=30.0,
        max_retries=0,
    )
    if NVIDIA_API_KEY
    else None
)


# ============================================================
# FETCH RSS NEWS
# ============================================================

def clean_description(value):
    """Convert an RSS HTML description into readable plain text."""
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def fetch_headlines(feed_url, limit=STORIES_PER_CATEGORY):
    request = urllib.request.Request(
        feed_url,
        headers={"User-Agent": "DailyNewsAgent/2.0"},
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        root = ET.fromstring(response.read())

    headlines = []

    for item in root.findall("./channel/item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        description = clean_description(
            item.findtext("description", "")
        )

        if title and link:
            headlines.append({
                "title": title,
                "link": link,
                "description": description[:1500],
            })

        if len(headlines) >= limit:
            break

    return headlines


# ============================================================
# NVIDIA LLM SUMMARIZATION
# ============================================================

def summarize_news(news):
    """
    Summarize RSS headline and description only.
    Return None on failure so the original headline can be used.
    """
    if not nvidia_client:
        return None

    if not news["description"]:
        return None

    prompt = f"""
Summarize this news item for a daily news briefing.

Headline: {news["title"]}
RSS description: {news["description"]}

Instructions:
- Write 3 to 5 concise bullet points in simple English.
- Use only the headline and RSS description supplied above.
- Do not invent facts, names, dates, statistics, causes, or conclusions.
- If details are insufficient, clearly state that information is limited.
- Put each bullet point on a separate line.
- Return only the bullet points, with no introduction.
"""

    try:
        response = nvidia_client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=400,
            temperature=0.2,
            extra_body={
                "chat_template_kwargs": {
                    "enable_thinking": False
                }
            },
        )

        content = response.choices[0].message.content

        if not content or not content.strip():
            print(f"Empty summary for: {news['title']}")
            return None

        return content.strip()

    except Exception as error:
        # Never print the API key or request headers.
        print(
            f"Summary failed for '{news['title']}': "
            f"{type(error).__name__}"
        )
        return None


# ============================================================
# FORMAT STORIES AND BUILD BRIEFING
# ============================================================

def format_story(news, summary=None):
    if summary:
        return (
            f"📰 {news['title']}\n"
            f"{summary}\n"
            f"Source: {news['link']}"
        )

    # Fallback: preserve the original headline and link.
    return f"• {news['title']}\n{news['link']}"


def build_briefing():
    today = datetime.now(IST).strftime("%d %b %Y")

    sections = []
    seen_titles = set()
    successful_feeds = 0
    summaries_used = 0
    summary_attempts = 0

    for category, feed_url in FEEDS.items():
        try:
            headlines = fetch_headlines(feed_url)
            successful_feeds += 1

        except Exception as error:
            print(
                f"Could not fetch {category}: "
                f"{type(error).__name__}"
            )
            sections.append(
                f"{category}\nFeed temporarily unavailable."
            )
            continue

        unique_stories = []

        for news in headlines:
            key = news["title"].casefold()

            if key in seen_titles:
                continue

            seen_titles.add(key)
            unique_stories.append(news)

        lines = [category]

        if not unique_stories:
            lines.append("No headlines available right now.")
        else:
            category_summaries = 0

            for news in unique_stories:
                summary = None

                # Aim for two summaries per category,
                # with eight attempts maximum overall.
                if (
                    summary_attempts < MAX_SUMMARIES
                    and category_summaries < SUMMARIES_PER_CATEGORY
                    and nvidia_client
                ):
                    # Count attempts, including failed ones.
                    summary_attempts += 1
                    summary = summarize_news(news)

                    if summary:
                        summaries_used += 1
                        category_summaries += 1

                lines.append(format_story(news, summary))

        sections.append("\n\n".join(lines))

    if successful_feeds == 0:
        raise RuntimeError(
            "All news feeds failed. No briefing sent."
        )

    message = (
        f"🗞️ VASU'S DAILY NEWS BRIEFING\n"
        f"📅 {today}\n\n"
        + "\n\n━━━━━━━━━━━━━━\n\n".join(sections)
        + "\n\nHeadlines and links via Google News RSS"
        + f"\nAI summaries generated: {summaries_used}"
    )

    if not nvidia_client:
        message += "\nAI summaries unavailable: API key not configured."

    return (
        today,
        message,
        sections,
        summaries_used,
        successful_feeds,
    )


# ============================================================
# TELEGRAM DELIVERY
# ============================================================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": "true",
    }).encode()

    request = urllib.request.Request(url, data=payload)

    with urllib.request.urlopen(request, timeout=20) as response:
        result = json.loads(response.read().decode())

    if not result.get("ok"):
        raise RuntimeError("Telegram message delivery failed.")


def make_telegram_chunks(sections, today, summaries_used):
    header = (
        f"🗞️ VASU'S DAILY NEWS BRIEFING\n"
        f"📅 {today}\n\n"
    )

    footer = (
        f"AI summaries generated: {summaries_used}\n"
        "Headlines and links via Google News RSS"
    )

    chunks = []
    current = header

    for section in sections:
        separator = "\n\n━━━━━━━━━━━━━━\n\n"
        addition = section + separator

        if (
            len(current) + len(addition) + len(footer) > TELEGRAM_CHUNK_LIMIT
            and current != header
        ):
            chunks.append(current.rstrip())
            current = header

        # Keep an individual section within Telegram's message limit.
        if len(header) + len(section) + len(footer) > TELEGRAM_CHUNK_LIMIT:
            section = section[:TELEGRAM_CHUNK_LIMIT - len(header) - len(footer) - 20]

        current += section + separator

    if len(current) + len(footer) > TELEGRAM_CHUNK_LIMIT:
        chunks.append(current.rstrip())
        current = header

    current += footer
    chunks.append(current.rstrip())

    return chunks


# ============================================================
# EMAIL DELIVERY
# ============================================================

def send_email(subject, message):
    email = EmailMessage()
    email["From"] = GMAIL_ADDRESS
    email["To"] = GMAIL_ADDRESS
    email["Subject"] = subject
    email.set_content(message)

    with smtplib.SMTP_SSL(
        "smtp.gmail.com",
        465,
        timeout=30,
    ) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.send_message(email)


# ============================================================
# MAIN
# ============================================================

def main():
    (
        today,
        message,
        sections,
        summaries_used,
        successful_feeds,
    ) = build_briefing()

    # Send Telegram messages first, as in the original agent.
    for chunk in make_telegram_chunks(
        sections,
        today,
        summaries_used,
    ):
        send_telegram(chunk)

    print("Telegram briefing sent.")
    print(f"AI summaries generated: {summaries_used}")

    # Email includes the complete briefing.
    subject = f"Your Daily News Briefing - {today}"
    send_email(subject, message)

    print(f"Email briefing sent to {GMAIL_ADDRESS}.")
    print(f"Successful news feeds: {successful_feeds}/4")


if __name__ == "__main__":
    main()
