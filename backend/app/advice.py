"""Orchestration: build the bot's reply for one chat turn.

Pulls together, per the account's effective settings:
  - the from-scratch ML read of the situation (scoped to this user's data)
  - persistent conversation memory (previous turns, from the DB)
  - remembered events/facts
  - outside research (Exa social + OpenAlex papers), weighted by RELIANCE
and hands a single prompt to the bot.

RELIANCE is 0..100: 100 -> trust HER data almost entirely, 0 -> trust outside
research almost entirely. It shifts how much of each we surface and how the bot
is told to weigh them.
"""
from . import claude_client, db
from .ml.engine import engine
from .research import aggregator


def _blend_counts(reliance: int, use_research: bool) -> tuple[int, int, int]:
    n_ml = 2 + round(reliance / 25)             # 2..6
    if not use_research:
        return n_ml, 0, 0
    research_weight = 100 - reliance
    n_social = round(research_weight / 34)      # 0..3
    n_research = round(research_weight / 50)    # 0..2
    return n_ml, n_social, n_research


def _reliance_label(reliance: int) -> str:
    if reliance >= 75:
        return ("HEAVILY on her own data. Lead with what her model shows. Only reach "
                "for general research if her data is thin or unsure.")
    if reliance >= 45:
        return ("mostly on her own data, using outside research as backup and framing.")
    if reliance >= 25:
        return ("a balance — her data for specifics, outside research for the general "
                "pattern; say when they disagree.")
    return ("mostly on outside research and general communication patterns, using her "
            "own data only as a light sanity-check.")


def _fmt_analysis(a: dict) -> str:
    if not a["trained"]:
        return "HER-SPECIFIC MODEL: (no training data yet — nothing learned about her.)"
    lines = ["HER-SPECIFIC MODEL (learned from labeled examples of her messages):"]
    if a["top_intent"]:
        lines.append(f"- Best read: {a['top_intent']} ({int(a['confidence']*100)}% "
                     f"confidence) — {a['top_intent_desc']}")
    dist = sorted(a["distribution"].items(), key=lambda kv: -kv[1])[1:3]
    others = ", ".join(f"{k} {int(v*100)}%" for k, v in dist if v > 0.05)
    if others:
        lines.append(f"- Other possibilities: {others}")
    if a["similar_cases"]:
        lines.append("- Similar past messages he already decoded:")
        for c in a["similar_cases"]:
            lines.append(f'    • she said "{c["her_message"]}"'
                         + (f' ({c["context"]})' if c["context"] else "")
                         + f' -> meant: {c["true_meaning"]} '
                         f'[{c["intent"]}, {int(c["similarity"]*100)}% similar]')
    if a["note"]:
        lines.append(f"- Model note: {a['note']}")
    return "\n".join(lines)


def _fmt_events(events: list[dict]) -> str:
    if not events:
        return "REMEMBERED EVENTS: (none yet.)"
    return "REMEMBERED EVENTS (recent stuff going on):\n" + "\n".join(
        f"- {e['text']}" for e in events)


def _fmt_research(items: list[dict]) -> str:
    if not items:
        return "OUTSIDE RESEARCH: (none pulled for this one.)"
    lines = ["OUTSIDE RESEARCH (general patterns from the web + psychology papers):"]
    for r in items:
        tag = "social" if r["source"] == "social" else "research"
        lines.append(f"- [{tag}] {r['title']}: {r['snippet']}")
    return "\n".join(lines)


def _fmt_history(history: list[dict]) -> str:
    if not history:
        return ""
    lines = ["EARLIER CONVERSATION (most recent last):"]
    for t in history[-12:]:
        who = "him" if t["role"] == "user" else "you"
        lines.append(f"- {who}: {t['content']}")
    return "\n".join(lines)


async def build_reply(user_id: int, question: str, eff: dict,
                      reliance: int, use_research: bool) -> dict:
    n_ml, n_social, n_research = _blend_counts(reliance, use_research)

    analysis = engine.analyze(user_id, question, k=n_ml).to_dict()
    events = db.list_events(user_id, limit=8)
    history = db.list_messages(user_id, limit=12)  # persistent memory

    research: list[dict] = []
    if use_research and (n_social + n_research) > 0:
        research = await aggregator.gather(
            question, eff["exa_key"], eff["openalex_mailto"], n_social, n_research)

    prompt = "\n".join(s for s in [
        _fmt_history(history),
        f"\nHIS NEW MESSAGE: {question}",
        f"\nRELIANCE SETTING: {reliance}/100. Lean {_reliance_label(reliance)}",
        "",
        _fmt_analysis(analysis),
        "",
        _fmt_events(events),
        "",
        _fmt_research(research),
        "",
        "Now answer him like his bro. Use your memory of the convo, weigh the sources "
        "per the reliance setting, and give a straight take plus one concrete move.",
    ] if s is not None)

    reply = await claude_client.generate(prompt, eff["anthropic_key"], eff["model"])

    return {
        "reply": reply,
        "analysis": analysis,
        "research": research,
        "events_used": events,
        "blend": {"ml_cases": n_ml, "social": n_social, "research": n_research},
    }
