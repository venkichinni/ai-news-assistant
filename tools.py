"""
tools.py
The one real "tool" the agent can choose to use: fetching the full text of an
article instead of relying on the short RSS summary. The model decides for
itself, per article, whether it needs this -- that's what makes the ranking
step agentic rather than a single blind pass over fixed data.
"""

import re
import requests

TIMEOUT_SECONDS = 8
MAX_CHARS = 3000  # keep it short -- this is context for a ranking decision, not archival


def fetch_full_article(url):
    """
    Best-effort fetch of an article's visible text. Returns a plain-text
    string (truncated), or None if the fetch fails for any reason. Failures
    are expected and handled gracefully -- this is a "nice to have" for the
    agent, not a required step.
    """
    try:
        resp = requests.get(
            url,
            timeout=TIMEOUT_SECONDS,
            headers={"User-Agent": "Mozilla/5.0 (compatible; AINewsAssistant/1.0)"},
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[warn] Could not fetch full article ({url}): {e}")
        return None

    html = resp.text
    # Strip script/style blocks, then tags -- deliberately simple/dependency-free
    # rather than pulling in a full HTML-parsing library for a "best effort" read.
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return None
    return text[:MAX_CHARS]
