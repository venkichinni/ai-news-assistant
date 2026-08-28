"""
state.py
Tracks which articles have already been sent, so the pipeline can avoid
repeating the same story on consecutive days. This is the project's "memory"
-- a simple JSON file committed back to the repo after each run (see the
GitHub Actions workflow), which keeps things at zero cost (no database needed).
"""

import json
import os
from datetime import datetime, timezone, timedelta

STATE_FILE = os.path.join(os.path.dirname(__file__), "sent_history.json")
RETENTION_DAYS = 14  # how long we remember a sent link, to bound file growth


def load_sent_links():
    """Returns a set of article links sent in the last RETENTION_DAYS."""
    if not os.path.exists(STATE_FILE):
        return set()

    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"[warn] Could not read state file, starting fresh: {e}")
        return set()

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    links = set()
    for entry in data.get("sent", []):
        try:
            sent_at = datetime.fromisoformat(entry["sent_at"])
        except (KeyError, ValueError):
            continue
        if sent_at >= cutoff:
            links.add(entry["link"])
    return links


def record_sent(top3):
    """Appends today's sent links to the state file (pruning old entries)."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=RETENTION_DAYS)

    existing = []
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                existing = json.load(f).get("sent", [])
        except (json.JSONDecodeError, OSError):
            existing = []

    # prune anything older than retention window
    kept = []
    for entry in existing:
        try:
            sent_at = datetime.fromisoformat(entry["sent_at"])
        except (KeyError, ValueError):
            continue
        if sent_at >= cutoff:
            kept.append(entry)

    for item in top3:
        kept.append({"link": item["link"], "title": item["title"], "sent_at": now.isoformat()})

    with open(STATE_FILE, "w") as f:
        json.dump({"sent": kept}, f, indent=2)

    print(f"[info] Recorded {len(top3)} sent links. {len(kept)} total tracked (last {RETENTION_DAYS} days).")
