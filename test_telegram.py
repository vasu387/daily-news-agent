
import json
import os
import urllib.parse
import urllib.request

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

message = (
    "Hello Vasu! 🐝🚀\n\n"
    "Your Daily News Agent is connected successfully!\n"
    "Next: India 🇮🇳 | Technology & AI 🤖 | World 🌍 | Cricket 🏏"
)

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = urllib.parse.urlencode({
    "chat_id": CHAT_ID,
    "text": message,
}).encode()

request = urllib.request.Request(url, data=payload)

with urllib.request.urlopen(request, timeout=20) as response:
    result = json.loads(response.read().decode())

if not result.get("ok"):
    raise RuntimeError("Telegram could not send the test message.")

print("Success! Telegram test message sent.")
