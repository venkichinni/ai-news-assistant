"""
notify_telegram.py
Sends the top-3 digest via a Telegram bot message.

Sent as PLAIN TEXT deliberately (no Markdown parse_mode). Real headlines
routinely contain apostrophes, underscores, asterisks, etc. that Telegram's
Markdown parser treats as formatting syntax and rejects with a 400 error if
they aren't escaped -- plain text sidesteps that entirely and is more
robust for content we don't fully control.

Required environment variables:
  TELEGRAM_BOT_TOKEN - token from @BotFather
  TELEGRAM_CHAT_ID   - your personal chat id (get it from @userinfobot)
"""

import os
from datetime import datetime
import requests


def _format_text(top3, date_str):
    lines = [f"🤖 Today's Top 3 AI News — {date_str}\n"]
    for i, item in enumerate(top3, start=1):
        lines.append(f"{i}. {item['title']}")
        lines.append(item["blurb"])
        lines.append(item["link"])
        lines.append("")  # blank line between items
    return "\n".join(lines)


def send_telegram(top3):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    date_str = datetime.now().strftime("%B %d, %Y")  # e.g. "August 28, 2026"
    text = _format_text(top3, date_str)
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    resp = requests.post(url, data={
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": False,
    }, timeout=15)
    resp.raise_for_status()
    print("[info] Telegram message sent")


if __name__ == "__main__":
    sample = [{"title": "Test", "link": "https://example.com", "blurb": "This is a test."}]
    send_telegram(sample)