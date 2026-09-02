# AI News Assistant — Daily Top 3 Digest (Agentic, Production-Hardened)

A zero-cost, fully automated pipeline that reads the day's AI news for you and
sends the 3 stories that actually matter — to your email and Telegram, every
morning, on its own.

---

## What it does, in order

1. **Fetches** the latest AI articles from 8 curated RSS feeds — a mix of
   AI-native sources (MIT Technology Review AI, OpenAI News, Anthropic News,
   Hugging Face Blog) and general tech outlets with strong AI desks
   (VentureBeat, TechCrunch, The Verge, Ars Technica) — plus highly-upvoted
   Hacker News stories (50+ points) as a community-vetted signal that pure
   RSS doesn't provide. Free, no API key needed for either.
2. **Loads memory** of what's already been sent in the last 14 days
   (`sent_history.json`), so you never get the same story twice.
3. **Agentically ranks** the candidates using Google's Gemini API (free
   tier, $0/month), against an explicit rubric rather than a vague
   "pick what's significant" instruction:
   - A story only qualifies if it clears at least one bar: concrete
     shipped impact, genuinely large-scale funding/M&A, real practitioner
     relevance (RAG/agents/LLMOps), or safety/policy weight with real
     near-term consequences.
   - The prompt explicitly tells the model to *avoid* listicles, opinion
     pieces, minor incremental updates dressed up as news, and anything it
     can't back with a specific concrete fact.
   - The model is told what's already been sent and actively avoids
     repeating stories — including different write-ups of the same
     underlying event, not just exact duplicate links.
   - The model can **request the full text** of up to 2 articles it's
     unsure about, instead of only seeing the short RSS summary. This is a
     genuine tool-use decision the model makes for itself.
   - The model's own output is **validated** (exactly 3 items, real
     title/link/blurb, no duplicates, nothing already sent). A failed
     validation is fed back to the model for **one self-correction retry**
     before the pipeline gives up for the day.
4. **Sends** the digest by Email and Telegram, both dated (e.g. *"Your Top 3
   AI News — August 28, 2026"*), each wrapped in **retry-with-backoff** (3
   attempts) so a single transient failure doesn't kill the day's send.
5. **Records** what was sent, for tomorrow's memory — and automatically
   forgets anything older than 14 days, so the file never grows unbounded.
6. **Alerts you on Telegram** if anything is skipped or fails, so a missing
   digest doesn't go unnoticed.
7. Runs automatically every day via **GitHub Actions** (free tier — no
   server to maintain), which also commits the updated memory file back to
   the repo after each run.

### Where this sits on the RAG / agentic spectrum

This is **not classic RAG** — there's no vector store or semantic
retrieval; sources are fixed RSS feeds read the same way every day. It **is
agentic** in a real, if modest, sense: the model decides whether it needs
more information before answering (tool use) and checks its own output
before finalizing (self-correction), rather than being one blind function
call. A natural next step toward fuller RAG would be embedding articles
into a vector store once the source volume grows large enough to need
semantic search over a simple ranked list.

---

## Project structure

| File | Role |
|---|---|
| `fetch_news.py` | Pulls candidate articles from the RSS feeds |
| `rank_news.py` | The agentic core: prompts Gemini, handles the full-text tool request, validates output, retries on guardrail failure |
| `tools.py` | The one tool the agent can call: `fetch_full_article(url)` |
| `state.py` | Reads/writes `sent_history.json` — the pipeline's memory |
| `notify_email.py` / `notify_telegram.py` | Send the dated digest |
| `notify_failure.py` | Sends a Telegram alert if the run is skipped or fails |
| `retry_utils.py` | Generic retry-with-backoff helper |
| `main.py` | Orchestrates all of the above |
| `.github/workflows/daily_news.yml` | Daily cron trigger + commits memory back to the repo |

---

## 1. Set up the repo

```bash
cd ai-news-assistant
git init
git add .
git commit -m "Initial commit: AI news assistant"
gh repo create ai-news-assistant --private --source=. --push
# (or create the repo on github.com and follow its git remote add / push instructions)
```

**Before your first commit**, make sure `.env` is excluded so real credentials
never reach GitHub. Create a `.gitignore` file containing at minimum:
```
.env
__pycache__/
*.pyc
```
`sent_history.json` is fine to commit — it holds only article links and
titles, nothing sensitive.

---

## 2. Get your credentials

### Gemini API key (free, no credit card required)
1. Go to https://aistudio.google.com/apikey
2. Sign in with a Google account, click **Create API key**, copy it (starts
   with `AIza`).
3. **Model name note:** Google periodically retires older Flash-Lite model
   versions for new API keys. If you get a `404 NOT_FOUND` error mentioning
   a model name, check the error message — it tells you the current
   replacement model to use in `MODEL = "..."` at the top of `rank_news.py`.

### Gmail App Password (for sending email)
1. Turn on **2-Step Verification**: https://myaccount.google.com/security
2. Go to https://myaccount.google.com/apppasswords and create one named
   "AI News Assistant" — copy the 16-character code.
3. **Paste it into `.env` with the spaces removed** (Google displays it as
   `abcd efgh ijkl mnop`; it should go in as one continuous string).
4. **Known gotcha:** if your account has a **passkey** set up for sign-in,
   Google disables app passwords entirely and the App Passwords page shows
   *"The setting you are looking for is not available for your account."*
   Fix: remove the passkey under Security → Passkeys and security keys (your
   account stays protected via 2-Step Verification through phone/Google
   prompt), then the App Passwords page unlocks.

### Telegram Bot
1. Message **@BotFather** on Telegram, send `/newbot`, follow the prompts.
   Copy the token it gives you (`TELEGRAM_BOT_TOKEN`) — the full string,
   including the numeric ID before the colon (e.g. `123456789:AAxxxx...`).
2. **Message your new bot first** — search for its username and send it
   anything (e.g. "hi"). Telegram won't let a bot message you until you've
   messaged it.
3. Get your real chat ID by visiting (in a browser, with your actual token):
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```
   Look for `"chat":{"id": ...}` in the response — that number is your
   `TELEGRAM_CHAT_ID`. (Using @userinfobot also works as a shortcut, but
   `getUpdates` is the most reliable if that ever gives an unexpected ID.)
4. **Sanity-check the token** any time you suspect it's wrong:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getMe
   ```
   `{"ok":true, ...}` confirms the token is valid; a 404 means it's mistyped
   or stale.

---

## 3. Local setup (Windows)

```powershell
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in all 6 real values (no quotes, no
spaces inside values).

PowerShell doesn't auto-load `.env` files the way Mac/Linux shells do. Load
your values into the current terminal session with:
```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^([^=]+)=(.*)$') { [System.Environment]::SetEnvironmentVariable($matches[1], $matches[2]) } }
```
Run this once per new terminal session, and again any time you edit `.env`.

Then run the pipeline:
```powershell
python main.py
```
Watch the terminal output — it shows articles fetched, whether the agent
requested full text, and confirms each send. Check your inbox and Telegram
afterward.

*(Mac/Linux: `export $(cat .env | xargs)` does the same job as the
PowerShell command above.)*

---

## 4. Add secrets to GitHub

**Settings → Secrets and variables → Actions → New repository secret.** Add
all 6, using the exact same values as your local `.env`:

| Secret name | Value |
|---|---|
| `GEMINI_API_KEY` | starts with `AIza` |
| `EMAIL_SENDER` | your Gmail address |
| `EMAIL_APP_PASSWORD` | 16-char app password, no spaces |
| `EMAIL_RECIPIENT` | where you want the digest |
| `TELEGRAM_BOT_TOKEN` | full token, number + colon + key |
| `TELEGRAM_CHAT_ID` | numeric chat ID from `getUpdates` |

The workflow needs permission to commit `sent_history.json` back to the
repo after each run — this is already set (`permissions: contents: write`
in the workflow file). No action needed unless your org has branch
protection rules that would block it.

---

## 5. Test it live, then let it run

Go to the **Actions** tab → "Daily AI News Digest" → **Run workflow**
(manual trigger). Check email/Telegram within a minute or two, and check
the run logs for anything unexpected.

The cron schedule fires automatically at **07:30 UTC** (1:00 PM IST) daily
after that — no laptop needed. Edit the `cron` line in
`.github/workflows/daily_news.yml` to change the time —
[crontab.guru](https://crontab.guru) helps translate schedules.

---

## Customizing

- **Sources**: edit the `FEEDS` list in `fetch_news.py` for RSS, or
  `HN_MIN_POINTS` (default 50) to raise/lower the Hacker News upvote bar.
- **Topic focus**: edit the prompt in `rank_news.py` (`_build_prompt`) —
  e.g. weight toward agentic AI / RAG / LLMOps news specifically.
- **Memory window**: change `RETENTION_DAYS` in `state.py` (default 14 days).
- **Agent's full-text fetch limit**: `MAX_FULL_TEXT_FETCHES` in
  `rank_news.py` (default 2).
- **Delivery time**: edit the `cron` line in
  `.github/workflows/daily_news.yml`.
- **Only email or only Telegram**: remove the corresponding line in
  `main.py`'s `main()`.

---

## Guardrails in place

- **Output validation**: exactly 3 items, non-empty title/blurb, real
  `http(s)://` link, no duplicate links, nothing repeated from the last 14
  days of memory.
- **Self-correction**: a failed validation is fed back to the model once,
  with the specific reason, before the pipeline gives up for the day.
- **Bounded tool use**: the agent can request full text for at most 2
  articles per run, and only once per run.
- **Retries with backoff**: the Gemini call and both send steps each retry
  up to 3 times before being treated as a failure.
- **Failure alerting**: any skip or failure sends a Telegram message
  explaining why.
- **Secrets stay out of code**: all credentials are GitHub Actions secrets
  and local `.env` (gitignored), never committed to the repo.
- **Single daily run**: no loop or retry logic that could cause repeated
  sends.
- **Human-in-the-loop judgment still matters**: there's no fact-checking
  step — treat blurbs as a pointer to read the source, not verified fact,
  especially for numbers (funding amounts, valuations).

---

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| `404 NOT_FOUND` on the Gemini call, mentioning a model name | That model version was retired for new keys. Use the replacement model name from the error message in `MODEL = "..."` in `rank_news.py`. |
| `503 UNAVAILABLE` on the Gemini call | Google's free tier is temporarily overloaded. The pipeline already retries automatically; just re-run in a few minutes if all 3 attempts fail. |
| Email fails with `535 Username and Password not accepted` | You're likely using your normal Gmail password instead of an app password, the app password has spaces in it, or 2-Step Verification isn't actually on. See the Gmail section above, including the passkey gotcha. |
| App Passwords page says *"setting not available for your account"* | You have a passkey configured. Remove it under Security → Passkeys, then the page unlocks. |
| Telegram `400 Bad Request` | Almost always the chat ID is wrong, or you haven't messaged your bot yet. Message the bot first, then re-fetch your chat ID via `getUpdates` (see Telegram section). |
| Telegram `404` on `getMe` | The token is mistyped, incomplete (missing the numeric ID + colon prefix), or stale from before a `/revoke`. Get a fresh one via `/token` in BotFather and re-test with `getMe` before updating `.env`. |
| `Import "requests" could not be resolved` (VS Code warning) | Cosmetic Pylance warning, not a real error — usually means VS Code's selected interpreter differs from the one `pip install` used. Fix via `Ctrl+Shift+P` → "Python: Select Interpreter", or just ignore it; the code runs fine regardless. |
| Guardrail keeps rejecting output during testing | Expected if you've run the pipeline multiple times in one day — today's top stories are already in `sent_history.json`. Reset it to `{"sent": []}` for a clean test run, or just wait for real daily use where this isn't an issue. |

**Security note:** if a real credential (API key, bot token, app password)
is ever pasted somewhere outside your own `.env` file — a chat, a shared
doc, a public repo — treat it as compromised and rotate it immediately
(Gemini: regenerate the key in AI Studio; Telegram: `/revoke` via
BotFather; Gmail: delete the old app password and generate a new one).

---

## Cost

- **GitHub Actions**: free. ~15 minutes/month used of a 2,000 minute free
  allowance.
- **Gemini API**: free. 1–2 requests/day (2 if the agent requests full
  text), well within the free daily quota for Flash/Flash-Lite models. No
  credit card required.
- **Gmail + Telegram**: free.
- **Rough total**: genuinely $0/month. The guardrail and retry logic mean a
  quota hiccup skips a day's send (with an alert) rather than costing
  anything or crashing loudly.
