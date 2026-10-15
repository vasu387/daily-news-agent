
import json
import os
import smtplib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
GMAIL_ADDRESS = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"].replace(" ", "")

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

        if title and link:
            headlines.append({"title": title, "link": link})

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


def send_email(subject, message):
    email = EmailMessage()
    email["From"] = GMAIL_ADDRESS
    email["To"] = GMAIL_ADDRESS
    email["Subject"] = subject
    email.set_content(message)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        smtp.send_message(email)


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
        + "\n\nHeadlines and links via Google News RSS"
    )

    # Telegram has a 4096-character message limit.
    chunks = []
    current = ""

    for section in message.split("\n\n━━━━━━━━━━━━━━\n\n"):
        candidate = (
            f"{current}\n\n━━━━━━━━━━━━━━\n\n{section}"
            if current else section
        )

        if len(candidate) > 3900 and current:
            chunks.append(current)
            current = section
        else:
            current = candidate

    if current:
        chunks.append(current)

    # Send Telegram messages first.
    for chunk in chunks:
        send_telegram(chunk)

    print("Telegram briefing sent.")

    # Send the complete briefing by email.
    subject = f"Your Daily News Briefing - {today}"
    send_email(subject, message)

    print(f"Email briefing sent to {GMAIL_ADDRESS}.")
    print(f"Successful news feeds: {successful_feeds}/4")


if __name__ == "__main__":
    main()
