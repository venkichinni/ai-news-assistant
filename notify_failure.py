"""
notify_failure.py
Sends a short Telegram alert when a day's run is skipped or fails, so you
get a heads-up instead of just silently not receiving a digest and wondering
why. Uses the same Telegram bot as the main digest.
"""

import os
import requests


def notify_failure(reason):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print(f"[warn] Cannot send failure alert (missing Telegram config). Reason was: {reason}")
        return

    text = f"⚠️ AI News Assistant: today's digest was skipped.\n\nReason: {reason}"
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        requests.post(url, data={"chat_id": chat_id, "text": text}, timeout=8)
        print("[info] Failure alert sent via Telegram.")
    except requests.RequestException as e:
        # Don't let a failed alert crash the pipeline further -- just log it.
        print(f"[warn] Could not send failure alert: {e}")
