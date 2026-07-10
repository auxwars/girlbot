# girlbot

A private, local chatbot that learns *your specific* girlfriend's communication
patterns from examples you label, blends that with outside research, and gives
you honest, casual advice in the voice of a bro who's been taking notes.

> She knows this exists and is on board with it. Keep it that way — all the data
> stays on your machine (a local SQLite file); only the specific question you ask
> is sent to the Claude API to generate a reply.

## What it does

- **Two pages.**
  - **Ask** — chat with the bot. Paste what she said, get a read. A slider lets
    you choose how much the bot leans on *her data* vs. *outside research*.
  - **Train** — label her messages ("she said X → it meant Y"), and log recent
    events so the bot knows what's going on.
- **From-scratch ML** (no scikit-learn) reads a new message the way you've taught
  it: a hand-written TF-IDF vectorizer tuned for texting tone (trailing periods,
  "k", ellipses, emojis…), a Naive Bayes classifier for the likely *meaning*, and
  cosine k-NN to pull up similar things she said before.
- **Outside research** via Exa (Reddit/forums — "when we say X we mean Y") and
  OpenAlex (relationship-psychology papers). Optional; toggled per message.
- **Memory** of recent events so advice is grounded in your actual situation.
- **Claude** (default `claude-opus-4-8`) writes the final reply, weighing all of
  the above according to your reliance slider.

## How the "reliance" works

The slider is 0–100. **100** = trust the model trained on *her* almost entirely.
**0** = trust general outside research almost entirely. It changes both how much
of each source gets surfaced and how the bot is told to weigh them.

## Run it

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then edit .env and add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000> . Go to **Train** first, label a handful of her
messages (there's built-in demo data so it works immediately — wipe it once
you've added your own), then head to **Ask**.

### Keys
- `ANTHROPIC_API_KEY` — required for the bot to actually reply. The ML read and
  research still work without it.
- `EXA_API_KEY` — optional, enables web/social research. Get one at exa.ai.
- `OPENALEX_MAILTO` — optional, just an email for the free academic API.

Model can be swapped in `.env` (`ANTHROPIC_MODEL=claude-sonnet-5` is cheaper).

## Layout

```
backend/app/
  ml/            from-scratch ML: features (TF-IDF), naive_bayes, knn, engine, taxonomy, seed
  research/      exa.py (social), openalex.py (academic), aggregator.py
  claude_client.py   the bro persona + Claude call
  advice.py      blends ML + research + memory per the reliance slider
  main.py        FastAPI: /api/* + serves the frontend
frontend/        index.html (Ask), train.html (Train), app.js, train.js, styles.css
```

## Honest limits

No model can read her mind. This plays the odds on patterns *you* label, and it's
built to tell you when it's unsure rather than fake confidence. The more real
examples you add, the better it gets. It's a tool for understanding, not a
substitute for actually talking to her.
