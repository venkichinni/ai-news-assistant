"""
fetch_news.py
Pulls the latest AI-related articles from a curated list of reputable RSS feeds.
No API key required for this step.
"""

import feedparser
from datetime import datetime, timedelta, timezone

# Curated list of reputable AI-focused RSS feeds.
# Mix of: AI-native publications/labs (higher signal, AI is their full beat)
# plus general tech outlets with strong AI desks (broader industry/business coverage).
# Feel free to add/remove sources here.
FEEDS = [
    # AI-native sources
    ("MIT Technology Review AI", "https://www.technologyreview.com/topic/artificial-intelligence/feed"),
    ("OpenAI News", "https://openai.com/news/rss.xml"),
    ("Anthropic News", "https://www.anthropic.com/news/rss.xml"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
    # General tech outlets with dedicated AI desks (good for funding/business angle)
    ("VentureBeat AI", "https://venturebeat.com/category/ai/feed/"),
    ("TechCrunch AI", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge AI", "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"),
    ("Ars Technica AI", "https://arstechnica.com/ai/feed/"),
]

# Only consider articles published in the last N hours (catches "yesterday's" news too,
# useful for the first run or if a day's cron is missed).
LOOKBACK_HOURS = 30


def _entry_datetime(entry):
    """Best-effort parse of an RSS entry's published time -> aware UTC datetime."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def fetch_recent_articles():
    """
    Returns a list of dicts: {title, link, summary, source, published}
    for articles published within LOOKBACK_HOURS across all feeds.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    articles = []

    for source_name, url in FEEDS:
        try:
            parsed = feedparser.parse(url)
        except Exception as e:
            print(f"[warn] Failed to fetch {source_name}: {e}")
            continue

        for entry in parsed.entries:
            published = _entry_datetime(entry)
            if published and published < cutoff:
                continue  # too old, skip

            articles.append({
                "title": entry.get("title", "").strip(),
                "link": entry.get("link", "").strip(),
                "summary": entry.get("summary", "")[:500].strip(),
                "source": source_name,
                "published": published.isoformat() if published else "unknown",
            })

    print(f"[info] Fetched {len(articles)} candidate articles from {len(FEEDS)} sources.")
    return articles


if __name__ == "__main__":
    for a in fetch_recent_articles():
        print(f"- [{a['source']}] {a['title']} ({a['link']})")
