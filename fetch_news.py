"""
fetch_news.py
Pulls the latest AI-related articles from a curated list of reputable RSS
feeds, plus community-vetted stories from Hacker News. No API key required.
"""

import feedparser
import requests
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

# Hacker News stories tagged/matching "AI" with at least this many upvotes are
# a genuinely different quality signal from RSS: community-vetted rather than
# just published. Free API (Algolia's HN search), no key needed.
HN_MIN_POINTS = 50
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"


def _entry_datetime(entry):
    """Best-effort parse of an RSS entry's published time -> aware UTC datetime."""
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime(*t[:6], tzinfo=timezone.utc)
    return None


def _fetch_rss_articles(cutoff):
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
    return articles


def _fetch_hn_articles(cutoff):
    """
    Community-vetted signal: HN stories matching "AI"-related terms with
    enough upvotes to indicate real reader interest, not just publication.
    """
    articles = []
    cutoff_ts = int(cutoff.timestamp())

    params = {
        "query": "AI OR LLM OR agent OR Anthropic OR OpenAI",
        "tags": "story",
        "numericFilters": f"points>={HN_MIN_POINTS},created_at_i>{cutoff_ts}",
        "hitsPerPage": 20,
    }

    try:
        resp = requests.get(HN_SEARCH_URL, params=params, timeout=10)
        resp.raise_for_status()
        hits = resp.json().get("hits", [])
    except Exception as e:
        print(f"[warn] Failed to fetch Hacker News: {e}")
        return articles

    for hit in hits:
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        title = (hit.get("title") or "").strip()
        if not title or not url:
            continue
        articles.append({
            "title": title,
            "link": url,
            "summary": f"Hacker News community discussion, {hit.get('points', 0)} points, "
                       f"{hit.get('num_comments', 0)} comments.",
            "source": "Hacker News",
            "published": hit.get("created_at", "unknown"),
        })
    return articles


def fetch_recent_articles():
    """
    Returns a list of dicts: {title, link, summary, source, published}
    for articles published within LOOKBACK_HOURS across all feeds, plus
    highly-upvoted Hacker News stories in the same window.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)

    articles = _fetch_rss_articles(cutoff)
    rss_count = len(articles)

    hn_articles = _fetch_hn_articles(cutoff)
    articles.extend(hn_articles)

    print(f"[info] Fetched {rss_count} articles from {len(FEEDS)} RSS feeds "
          f"+ {len(hn_articles)} from Hacker News (>={HN_MIN_POINTS} points).")
    return articles


if __name__ == "__main__":
    for a in fetch_recent_articles():
        print(f"- [{a['source']}] {a['title']} ({a['link']})")
