
import json
import os
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

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

def fetch_headlines(feed_url, limit=5):
    request = urllib.request.Request(
        feed_url,
        headers={"User-Agent": "DailyNewsAgent/1.0"},
    )

    with urllib.request.urlopen(request, timeout=20) as response:
        root = ET.fromstring(response.read())

    headlines = []

    for item in root.findall("./channel/item"):
        title = item.findtext("title", "").strip()
        link = item.findtext("link", "").strip()
        pub_date = item.findtext("pubDate", "").strip()

        if title and link:
            headlines.append({
                "title": title,
                "link": link,
                "pub_date": pub_date,
            })

        if len(headlines) >= limit:
            break

    return headlines

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

def main():
    today = datetime.now(IST).strftime("%d %b %Y")
    sections = []
    seen_titles = set()
    successful_feeds = 0

    for category, feed_url in FEEDS.items():
        lines = [category]
        try:
            headlines = fetch_headlines(feed_url)
            successful_feeds += 1

            for news in headlines:
                key = news["title"].casefold()
                if key in seen_titles:
                    continue
                seen_titles.add(key)

                lines.append(f"• {news['title']}\n{news['link']}")

            if len(lines) == 1:
                lines.append("No headlines available right now.")

        except Exception as error:
            print(f"Could not fetch {category}: {error}")
            lines.append("Feed temporarily unavailable.")

        sections.append("\n\n".join(lines))

    if successful_feeds == 0:
        raise RuntimeError("All news feeds failed. No briefing sent.")

    message = (
        f"🗞️ VASU'S DAILY NEWS BRIEFING\n"
        f"📅 {today}\n\n"
        + "\n\n━━━━━━━━━━━━━━\n\n".join(sections)
        + "\n\n🔗 Headlines and links via Google News RSS"
    )

    # Telegram text messages have a 4096-character limit.
    # Split at section boundaries when possible.
    chunks = []
    current = ""

    for section in message.split("\n\n━━━━━━━━━━━━━━\n\n"):
        candidate = f"{current}\n\n━━━━━━━━━━━━━━\n\n{section}" if current else section

        if len(candidate) > 3900 and current:
            chunks.append(current)
            current = section
        else:
            current = candidate

    if current:
        chunks.append(current)

    for chunk in chunks:
        send_telegram(chunk)

    print(f"Briefing sent. Successful feeds: {successful_feeds}/4")

if __name__ == "__main__":
    main()
