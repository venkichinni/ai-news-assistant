"""
main.py
Orchestrates the daily pipeline:
  1. Fetch recent AI articles from RSS feeds
  2. Load memory of what's already been sent (last 14 days)
  3. Ask Gemini (agentically -- it can request full article text, and gets
     told what's already been sent) to pick the top 3 + write blurbs
  4. Send the digest via Email and Telegram (with retries)
  5. Record what was sent, for tomorrow's memory
  6. On any failure/skip, send a short Telegram alert so you know it happened

Run manually with: python main.py
Runs automatically via .github/workflows/daily_news.yml
"""

from fetch_news import fetch_recent_articles
from rank_news import pick_top3
from notify_email import send_email
from notify_telegram import send_telegram
from notify_failure import notify_failure
from retry_utils import retry_with_backoff
from state import load_sent_links, record_sent


def main():
    try:
        articles = fetch_recent_articles()
    except Exception as e:
        notify_failure(f"Failed to fetch RSS feeds: {e}")
        return

    if not articles:
        notify_failure("No articles were fetched from any source today.")
        return

    already_sent_links = load_sent_links()

    top3 = pick_top3(articles, already_sent_links)
    if not top3:
        # pick_top3 already validated its own output (exactly 3 items, real
        # title/link/blurb, no duplicates, nothing repeated from recent
        # history). An empty result means something looked off, so we skip
        # sending entirely rather than forward broken or repeated content.
        notify_failure("Could not produce a valid, non-repeated top-3 digest today (see run logs for detail).")
        return

    print("[info] Top 3 selected:")
    for i, item in enumerate(top3, start=1):
        print(f"  {i}. {item['title']}")

    try:
        retry_with_backoff(lambda: send_email(top3), attempts=3, what="send_email")
    except Exception as e:
        notify_failure(f"Failed to send email after retries: {e}")
        # Don't return yet -- still try Telegram, since email failing
        # shouldn't block the channel that's working.

    try:
        retry_with_backoff(lambda: send_telegram(top3), attempts=3, what="send_telegram")
    except Exception as e:
        notify_failure(f"Failed to send Telegram message after retries: {e}")

    record_sent(top3)


if __name__ == "__main__":
    main()
