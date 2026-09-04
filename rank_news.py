"""
rank_news.py
Agentic ranking step, using the Gemini API (free tier).

What makes this "agentic" rather than a single blind pass:
  1. The model is told which links were already sent recently, and decides
     for itself which candidates to skip as repeats -- it isn't just handed
     a pre-filtered list.
  2. The model can ASK for the full text of up to 2 articles it's unsure
     about (rather than only ever seeing the short RSS summary), by naming
     them in a "need_full_text" field. The pipeline honors that request,
     fetches the text via tools.fetch_full_article, and re-prompts with it.
  3. Before finalizing, the model is asked to self-check its own picks
     against the guardrail rules. If our own validation still fails, we
     retry once with the specific error fed back to the model.

Requires: GEMINI_API_KEY environment variable (free, no credit card --
https://aistudio.google.com/apikey).
"""

import json
import os
from google import genai

from tools import fetch_full_article
from retry_utils import retry_with_backoff

# Flash-Lite has the highest free-tier daily request allowance of Google's
# current models. Swap to "gemini-2.5-flash" for slightly stronger reasoning
# and still stay on the free tier.
MODEL = "gemini-3.5-flash-lite"
MAX_FULL_TEXT_FETCHES = 2  # cap how many full-article fetches the agent can request per run


def _build_prompt(articles, already_sent_links, extra_context=None, retry_note=None):
    numbered = "\n".join(
        f"{i+1}. [{a['source']}] {a['title']}\n   Link: {a['link']}\n   Summary: {a['summary']}"
        for i, a in enumerate(articles)
    )

    sent_block = ""
    if already_sent_links:
        sent_list = "\n".join(f"- {link}" for link in sorted(already_sent_links))
        sent_block = f"""
Links already sent to the user in the last 14 days (DO NOT pick these, or
close variants of the same underlying story, again):
{sent_list}
"""

    context_block = ""
    if extra_context:
        context_block = "\n\nAdditional full-text context you requested:\n" + "\n\n".join(
            f"--- Full text for: {title} ---\n{text}" for title, text in extra_context.items()
        )

    retry_block = ""
    if retry_note:
        retry_block = f"\n\nYour previous attempt was rejected for this reason: {retry_note}\nPlease correct it.\n"

    return f"""You are curating a daily "Top 3 AI News" digest for a senior data engineer
who is upskilling in AI engineering (RAG, agents, LLMOps). From the candidate articles
below, pick and RANK the 3 most significant, DISTINCT AI news items from the last day.

RUBRIC -- use this to RANK candidates against each other, from strongest to weakest.
This is a relative preference, not a pass/fail gate: you must still deliver exactly 3
picks whenever at least 3 distinct, non-duplicate, not-already-sent candidates exist in
the list below, even on a quiet news day where nothing is a home run. Prefer stories that:
  - CONCRETE IMPACT: are a shipped model/product/feature real users or developers can
    actually use today (not a teaser, roadmap, or "coming soon").
  - MEANINGFUL SCALE: funding, acquisition, or partnership news where the number or
    parties involved are genuinely large relative to the AI industry, not a routine
    seed round.
  - PRACTITIONER RELEVANCE: would change how an engineer builds with RAG, agents, or
    LLMOps -- a new technique, a notable open-source release, a real incident/postmortem
    with lessons.
  - SAFETY/POLICY WEIGHT: regulatory action or safety research with actual near-term
    consequences, not opinion pieces.
Rank down (but don't refuse to pick if nothing better is available): listicles, generic
trend pieces, minor incremental updates, and anything you can't back with a specific
concrete fact. A "Hacker News" sourced item passed a real community filter (upvotes) --
weigh that, but still rank it against the same criteria.

WRITING STYLE for each blurb -- make it genuinely engaging to read, not a dry summary:
  - Open with the concrete hook: the specific number, product name, or claim -- not
    "In a recent development..." or "This article discusses...".
  - One sentence on what happened, one on why it actually matters to a practitioner or
    the industry. Active voice, plain words, no filler ("in today's fast-moving AI
    landscape", "it remains to be seen", "significant development").
  - Specific beats vague: "$1B in debt to buy GPUs" beats "raised significant funding".

Deduplication rule: if two or more candidates describe the SAME underlying event, treat
them as ONE story. Your final 3 must be 3 DIFFERENT underlying stories.
{sent_block}
Candidates:
{numbered}
{context_block}
{retry_block}
You have two options for this response:

OPTION A -- you're confident in your picks. Respond with ONLY this JSON (no markdown
fences, no preamble):
{{
  "action": "final",
  "top3": [
    {{"title": "...", "link": "...", "blurb": "punchy 1-2 sentence summary, hook first"}},
    {{"title": "...", "link": "...", "blurb": "..."}},
    {{"title": "...", "link": "...", "blurb": "..."}}
  ]
}}

OPTION B -- a short RSS summary isn't enough for 1 or 2 candidates you think are strong
contenders, and reading the full article would materially change your blurb or your
decision to include it. Respond with ONLY this JSON instead:
{{
  "action": "need_full_text",
  "titles": ["exact title of article 1", "exact title of article 2"]
}}
(Request at most {MAX_FULL_TEXT_FETCHES} titles, and only if you genuinely need them --
prefer OPTION A whenever the summaries are already enough to decide confidently.)
"""


def _is_valid_top3(top3, already_sent_links):
    """
    Guardrail: exactly 3 items, each with non-empty title/blurb and a real
    http(s) link, no duplicate links among the 3, and none of them a link
    that was already sent recently.
    """
    if not isinstance(top3, list) or len(top3) != 3:
        return False, "top3 must contain exactly 3 items"

    seen_links = set()
    for item in top3:
        if not isinstance(item, dict):
            return False, "each item must be an object"
        title = item.get("title", "").strip()
        link = item.get("link", "").strip()
        blurb = item.get("blurb", "").strip()

        if not title or not blurb:
            return False, "each item needs a non-empty title and blurb"
        if not (link.startswith("http://") or link.startswith("https://")):
            return False, f"invalid link: {link!r}"
        if link in seen_links:
            return False, "duplicate link across the 3 picks"
        if link in already_sent_links:
            return False, f"link was already sent recently: {link}"
        seen_links.add(link)

    return True, None


def _call_gemini(prompt):
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = retry_with_backoff(
        lambda: client.models.generate_content(model=MODEL, contents=prompt),
        attempts=3,
        base_delay_seconds=2,
        what="Gemini API call",
    )
    raw_text = (response.text or "").strip()
    return raw_text.replace("```json", "").replace("```", "").strip()


def pick_top3(articles, already_sent_links=None):
    """
    Returns a validated list of exactly 3 {title, link, blurb} dicts, or an
    empty list if nothing trustworthy could be produced. Callers should
    treat an empty list as "skip sending today."
    """
    already_sent_links = already_sent_links or set()

    if not articles:
        print("[warn] No candidate articles supplied -- nothing to rank.")
        return []

    if not os.environ.get("GEMINI_API_KEY"):
        print("[error] GEMINI_API_KEY not set -- skipping ranking.")
        return []

    extra_context = {}
    retry_note = None

    # Up to 4 rounds now: 1 initial pass (which may ask for full text), then
    # up to 3 guardrail-triggered retries -- gives the model more chances to
    # self-correct on a thin news day instead of skipping too eagerly.
    for round_num in range(5):
        prompt = _build_prompt(articles, already_sent_links, extra_context, retry_note)

        try:
            raw_text = _call_gemini(prompt)
        except Exception as e:
            print(f"[error] Gemini API call failed after retries: {e}")
            return []

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            print(f"[error] Could not parse model output as JSON: {e}\nRaw output:\n{raw_text}")
            return []

        action = data.get("action")

        if action == "need_full_text" and not extra_context:
            # Only honor this once per run, and only up to MAX_FULL_TEXT_FETCHES titles.
            titles_wanted = data.get("titles", [])[:MAX_FULL_TEXT_FETCHES]
            print(f"[info] Agent requested full text for: {titles_wanted}")

            by_title = {a["title"]: a for a in articles}
            for title in titles_wanted:
                article = by_title.get(title)
                if not article:
                    continue
                text = fetch_full_article(article["link"])
                if text:
                    extra_context[title] = text
            continue  # re-prompt with the extra context now available

        if action == "final":
            top3 = data.get("top3", [])
            valid, error = _is_valid_top3(top3, already_sent_links)
            if valid:
                return top3
            print(f"[warn] Guardrail rejected output: {error}")
            retry_note = error
            continue

        # Unexpected/malformed action field
        print(f"[warn] Unexpected model response shape: {data}")
        retry_note = "response must have an 'action' field set to 'final' or 'need_full_text'"

    print("[error] Could not produce a valid top3 after all attempts -- skipping send today.")
    return []


if __name__ == "__main__":
    from fetch_news import fetch_recent_articles
    from state import load_sent_links
    top3 = pick_top3(fetch_recent_articles(), load_sent_links())
    print(json.dumps(top3, indent=2))
