# girlbot

A private chatbot that learns *your specific* girlfriend's communication patterns
from your conversations, blends that with outside research, and gives you honest,
casual advice in the voice of a bro who's been taking notes.

> She knows this exists and is on board with it. Keep it that way. Your data
> stays in your account's database; only the messages you send go to the Claude
> API to generate replies.

## What it is now

- **One chat page + a settings page.** Just talk to it. Everything else lives in
  Settings.
- **Persistent memory.** Every conversation is saved to your account, so it
  remembers what's been going on across sessions and devices — not just the
  current tab.
- **You choose if it learns.** A "Learn from our conversations" switch in
  Settings. When on, it quietly turns what you tell it ("she said X, it meant Y")
  into training data + remembered facts, so it gets sharper about *her* over time.
  When off, it just chats.
- **From-scratch ML** (no scikit-learn): a hand-written TF-IDF vectorizer tuned
  for texting tone (trailing periods, "k", ellipses, emojis, terse replies), a
  Multinomial Naive Bayes classifier for the likely *meaning*, and cosine k-NN to
  pull up similar things she said before.
- **Outside research** via Exa (Reddit/forums — "when we say X we mean Y") and
  OpenAlex (relationship-psychology papers). A reliance slider blends *her data*
  vs. *outside research* per message.
- **Google sign-in (optional)** so memory is permanent and private per account.
- **Claude** (default `claude-opus-4-8`) writes the replies.

## Where to paste your keys

Open the app → **⚙️ Settings → Connections**. Paste each key into its field and
hit **Save settings**:

| Key | Where to get it | Needed for |
|---|---|---|
| **Anthropic API key** (`sk-ant-…`) | [console.anthropic.com → Settings → API Keys](https://console.anthropic.com/settings/keys) | the bot to reply (required) |
| **Exa API key** | [dashboard.exa.ai → API Keys](https://dashboard.exa.ai/api-keys) | social / Reddit research (optional) |
| **OpenAlex email** | any email you use (no signup) | science / psychology research (optional) |

The model dropdown is set to **claude-opus-4-8** by default. You can instead put
any of these in the server's `.env` (see `backend/.env.example`) as defaults.

## Run it locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # optional — you can paste keys in the UI instead
uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000>. With no Google keys set it runs in **local mode**
(single user, no login). It ships with demo data so the ML works immediately —
wipe it from Settings once you've built up your own.

## Deploy on Railway (permanent memory)

1. Push this repo to GitHub and create a Railway project from it. Railway
   auto-detects Python (via the root `requirements.txt`) and starts it with the
   `Procfile` / `railway.json`.
2. **Add a Volume** (Railway → your service → *Volumes*) and mount it at `/data`.
   Then set the variable `GIRLBOT_DATA_DIR=/data` so the database — and all
   memory — survives redeploys.
3. **Set environment variables** (Railway → *Variables*):
   - `SECRET_KEY` — a long random string (`python -c "import secrets;print(secrets.token_hex(32))"`). Required, or logins drop on restart.
   - `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL=claude-opus-4-8` (or paste per-account in Settings).
   - `EXA_API_KEY`, `OPENALEX_MAILTO` (optional).
4. **Turn on Google sign-in** (for permanent, per-person memory):
   - Google Cloud Console → *APIs & Services → Credentials → Create OAuth client ID → Web application*.
   - Authorized redirect URI: `https://YOUR-APP.up.railway.app/auth/callback`
   - Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and
     `GOOGLE_REDIRECT_URI=https://YOUR-APP.up.railway.app/auth/callback` in Railway.
   - Redeploy. Now the app requires Google login and each account gets its own
     permanent memory.

## Layout

```
backend/app/
  ml/            from-scratch ML: features (TF-IDF), naive_bayes, knn, engine, taxonomy, seed
  research/      exa.py (social), openalex.py (academic), aggregator.py
  auth.py        Google OAuth (falls back to local mode)
  prefs.py       merges per-account settings over env defaults
  extract.py     auto-learning: turns your messages into examples + memory (when training is on)
  claude_client.py   the bro persona + Claude call
  advice.py      blends ML + memory + research per the reliance slider
  db.py          SQLite: users, per-user settings, conversation memory, examples, events
  main.py        FastAPI: /api/*, /auth/*, serves the frontend
frontend/        index.html (chat), settings.html, app.js, settings.js, styles.css
Procfile, railway.json, requirements.txt   # Railway deploy
```

## Honest limits

No model can read her mind. This plays the odds on patterns *it learns from you*,
and it's built to say when it's unsure rather than fake confidence. The more you
talk to it (with learning on), the better it gets. It's a tool for understanding,
not a substitute for actually talking to her.
