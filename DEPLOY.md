# girlbot — Full Setup Guide (from zero)

This walks you all the way from nothing to a private, always-online girlbot with
permanent memory and Google login. No prior experience assumed. Do the parts in
order. Budget ~30–45 minutes.

## What you're building

A private website only you can use, running 24/7 in the cloud (Railway), that
remembers everything permanently (Postgres database), lets you log in with
Google, and is powered by Claude.

## Accounts you'll need (all free to start)

| Service | What for | Cost |
|---|---|---|
| **GitHub** | holds the code (you already have this — the repo is `auxwars/girlbot`) | free |
| **Anthropic** | the bot's brain (Claude API) | pay-per-use, ~cents per chat; needs a small prepaid balance (start with $5) |
| **Railway** | runs the app online | small monthly cost (~$5) or a free trial |
| **Google Cloud** | the "Sign in with Google" login | free |
| **Exa** (optional) | Reddit/social research | free tier |

You don't need to install anything on your computer for this. It's all done in
the browser.

---

# PART 1 — Get your Anthropic API key (the bot's brain)

Without this the bot can't talk, so do it first.

1. Go to **https://console.anthropic.com** and sign up / log in.
2. Add a little money: click **Billing** (or **Plans & Billing**) → **Add
   credits** / set up a payment method → add **$5**. (Each chat costs a fraction
   of a cent; $5 lasts a long time for personal use.)
3. Click **API Keys** (or go to https://console.anthropic.com/settings/keys) →
   **Create Key** → give it a name like `girlbot` → **Copy** the key. It starts
   with `sk-ant-...`.
4. Paste it somewhere safe for a minute (a notes app). **Treat it like a
   password** — don't share it. You'll put it into Railway in Part 3.

✅ You now have: `ANTHROPIC_API_KEY = sk-ant-...`

---

# PART 2 — Make one secret string

The app signs your login cookie with a secret. You just need one long random
string. Pick any ONE of these:

- Open **https://www.random.org/strings/** → set length 32, generate a couple,
  mash them together into one long string, OR
- Use any password manager's "generate password" at length ~40, OR
- If you're comfortable with a terminal: `python3 -c "import secrets;print(secrets.token_hex(32))"`

It just needs to be long and random, like `9f2a7c...` (40+ characters). Save it.

✅ You now have: `SECRET_KEY = <your long random string>`

---

# PART 3 — Put the app online with Railway

### 3.1 Sign up

1. Go to **https://railway.app** → **Login** → **Login with GitHub**. Authorize
   Railway to see your GitHub.

### 3.2 Deploy the code

2. Click **New Project** → **Deploy from GitHub repo**.
3. If asked, click **Configure GitHub App** and give Railway access to your
   `auxwars/girlbot` repo (you can grant just that one repo).
4. Pick **`auxwars/girlbot`** from the list. Railway starts building it.

### 3.3 Point it at the right branch

The finished code is on a branch called `claude/relationship-chatbot-ml-1xklxg`.
Tell Railway to use it:

5. Click your service (the box that appears) → **Settings** tab → find **Source**
   → **Branch** → choose **`claude/relationship-chatbot-ml-1xklxg`**.
   - *(Alternatively, if you merge that branch into `main` on GitHub first, you
     can just leave it on `main`. Either works.)*

### 3.4 Add the Postgres database (permanent memory)

6. In your project view, click **New** (or the **+** / **Create**) →
   **Database** → **Add PostgreSQL**. A Postgres box appears next to your app.
   Railway manages it for you.

### 3.5 Set the environment variables

7. Click your **app service** (not the Postgres one) → **Variables** tab.
8. Add these one at a time (**New Variable** → name, then value):

   | Variable name | Value |
   |---|---|
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` — type it exactly, with the `${{ }}`. This links your app to the database. |
   | `SECRET_KEY` | the long random string from Part 2 |
   | `ANTHROPIC_API_KEY` | your `sk-ant-...` key from Part 1 |
   | `ANTHROPIC_MODEL` | `claude-opus-4-8` |

   Optional (add later if you want research):
   | `EXA_API_KEY` | your Exa key (see Part 6) |
   | `OPENALEX_MAILTO` | any email you use |

   💡 Tip: there's a **Raw Editor** button in Variables — you can paste all of
   them at once in `NAME=value` form.

### 3.6 Give it a public web address

9. Still in your app service → **Settings** tab → **Networking** → **Public
   Networking** → **Generate Domain**. Railway gives you a URL like
   `https://girlbot-production-xxxx.up.railway.app`. **Copy it** — this is your
   app's address. Keep it for Part 4.

### 3.7 Let it redeploy

10. Any time you change variables, Railway redeploys automatically (watch the
    **Deployments** tab — wait for it to go green / "Success"). If it doesn't,
    hit **Deploy** / **Redeploy**.

### 3.8 Check it works

11. Open your Railway URL in a browser. You should see the **girlbot chat
    window** (Mac Messages style). At this point there's no login yet (that's
    Part 4). Tap the **⚙︎** and you can already start using it. 🎉

If you see the chat, the hard part is done.

---

# PART 4 — Turn on "Sign in with Google" (permanent, private memory)

This makes the app require your Google login, so your chats are tied to your
account and stay private and permanent. (Skip this only if you're the sole user
and don't care about a login screen — it already works without it.)

### 4.1 Create a Google Cloud project

1. Go to **https://console.cloud.google.com**. Sign in with your Google account.
2. Top bar → project dropdown → **New Project** → name it `girlbot` → **Create**.
   Make sure that project is selected afterward.

### 4.2 Set up the consent screen

3. Left menu → **APIs & Services** → **OAuth consent screen**.
4. Choose **External** → **Create**.
5. Fill the required fields: **App name** = `girlbot`, **User support email** =
   your email, **Developer contact email** = your email. Leave the rest blank →
   **Save and Continue**.
6. **Scopes** step → just **Save and Continue** (no changes needed).
7. **Test users** step → **Add Users** → add your own Gmail address → **Save and
   Continue**. (This lets you log in while the app is in "testing" mode — which
   is fine forever for personal use.)

### 4.3 Create the OAuth credentials

8. Left menu → **APIs & Services** → **Credentials** → **+ Create Credentials**
   → **OAuth client ID**.
9. **Application type** → **Web application**. Name it `girlbot`.
10. Under **Authorized redirect URIs** → **Add URI** → paste **exactly**:
    ```
    https://YOUR-APP.up.railway.app/auth/callback
    ```
    Replace `YOUR-APP.up.railway.app` with your real Railway domain from step
    3.6. It must be `https://`, end in `/auth/callback`, and have **no trailing
    slash** after that. (This exact-match matters — a typo here is the #1 reason
    login fails.)
11. Click **Create**. A popup shows your **Client ID** and **Client secret**.
    Copy both.

### 4.4 Add them to Railway

12. Railway → your app service → **Variables** → add:

    | Variable name | Value |
    |---|---|
    | `GOOGLE_CLIENT_ID` | the Client ID (ends in `.apps.googleusercontent.com`) |
    | `GOOGLE_CLIENT_SECRET` | the Client secret |
    | `GOOGLE_REDIRECT_URI` | `https://YOUR-APP.up.railway.app/auth/callback` (same exact URL as step 10) |

13. Let it redeploy (Deployments tab → wait for green).

### 4.5 Test the login

14. Open your Railway URL again. Now you should see a **Sign in with Google**
    screen → click it → pick your Google account → you're in. Your memory is now
    permanent and tied to your account.

---

# PART 5 — Using it

1. Open your Railway URL, sign in.
2. Tap **⚙︎** (top-right) → **Connections**. If you set the keys as Railway
   variables you're already good; you can also paste keys here instead. Hit
   **Save settings**.
3. In **Behavior**, make sure **"Learn from our conversations"** is on if you
   want it to get smarter about her over time. Set your default **reliance**
   (how much it trusts her data vs. outside research).
4. Go back to the chat and just text it — paste what she said, or describe the
   situation. Tap the **ⓘ** button in the chat header for the per-message
   reliance slider and research toggle.
5. There's built-in demo data so it works immediately. In **Settings → What I've
   learned about her**, hit **Wipe demo examples** once you've built up your own.

---

# PART 6 — (Optional) Exa research key

For the "what are people saying online" (Reddit/forums) research:

1. Go to **https://dashboard.exa.ai** → sign up → **API Keys** → create one →
   copy it.
2. Add it in Railway Variables as `EXA_API_KEY`, **or** paste it in the app's
   ⚙︎ Settings → Connections. Done.

The academic (OpenAlex) research needs no key — just optionally set
`OPENALEX_MAILTO` to any email.

---

# Troubleshooting

**The chat loads but the bot replies with a ⚠️ error about the API key**
→ Your `ANTHROPIC_API_KEY` is missing/typo'd, or your Anthropic account has $0.
Check Part 1 (billing + key) and the Railway variable.

**Google login fails / "redirect_uri_mismatch"**
→ The URL in Google Cloud (Part 4.3 step 10) and the `GOOGLE_REDIRECT_URI`
variable (Part 4.4) must match your Railway domain **exactly** — `https://`, no
trailing slash, ending in `/auth/callback`. Fix both to match and redeploy.

**Login works but logs me out on every redeploy**
→ You didn't set `SECRET_KEY` (Part 2/3.5). Add it.

**Build failed in Railway**
→ Open the **Deployments** tab → click the failed deploy → read the log. Usually
it's a missing variable. Make sure `DATABASE_URL` is `${{Postgres.DATABASE_URL}}`
and the Postgres database exists.

**It forgot everything after a redeploy**
→ You're not on Postgres. Confirm the Postgres database is added and
`DATABASE_URL = ${{Postgres.DATABASE_URL}}` is set on the app service.

**"Application failed to respond" / 502**
→ Give it a minute after a deploy. If it persists, check the deploy log for a
crash (usually a bad variable value).

---

# Costs (be aware)

- **Anthropic**: pay-per-use. Personal chatting is cents. Your $5 goes a long
  way. You can set spend limits in the Anthropic console.
- **Railway**: a small monthly cost (hobby plan ~$5) or a limited free trial.
  The Postgres database usage for one person is tiny.
- **Google Cloud & Exa**: free at this scale.

---

# Local option (only if you want to run it on your own computer)

You don't need this to use the app — Railway is enough. But if you want it local:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env         # then paste your keys into .env
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000. With no Google keys set it runs in local single-user
mode (no login). It uses a local SQLite file, so no database setup needed.
