"""Orchestration: take the user's question, run the ML read, pull memory, pull
research if asked, blend it all per the RELIANCE slider, and hand a single prompt
to the bot.

RELIANCE is 0..100:
    100 -> trust HER data (the from-scratch ML) almost entirely
      0 -> trust OUTSIDE RESEARCH almost entirely
It shifts how much of each we surface AND how we tell the bot to weigh them.
"""
from . import claude_client, db
from .ml.engine import engine
from .research import aggregator


def _blend_counts(reliance: int, use_research: bool) -> tuple[int, int, int]:
    """Return (n_ml_cases, n_social, n_research) based on the slider."""
    # More reliance -> more of her cases, fewer research snippets.
    n_ml = 2 + round(reliance / 25)            # 2..6
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
        return ("mostly on her own data, using outside research as backup and for "
                "general framing.")
    if reliance >= 25:
        return ("a balance — use her data for the specifics and outside research for "
                "the general pattern, and say when they disagree.")
    return ("mostly on outside research and general communication patterns, using her "
            "own data only as a light sanity-check.")


def _fmt_analysis(analysis) -> str:
    a = analysis.to_dict()
    if not a["trained"]:
        return "HER-SPECIFIC MODEL: (no training data yet — nothing learned about her.)"

    lines = ["HER-SPECIFIC MODEL (learned from labeled examples of her messages):"]
    if a["top_intent"]:
        lines.append(
            f"- Best read: {a['top_intent']} ({int(a['confidence'] * 100)}% confidence)"
            f" — {a['top_intent_desc']}"
        )
    # show the next couple of contenders
    dist = sorted(a["distribution"].items(), key=lambda kv: -kv[1])[1:3]
    if dist:
        others = ", ".join(f"{k} {int(v*100)}%" for k, v in dist if v > 0.05)
        if others:
            lines.append(f"- Other possibilities: {others}")
    if a["similar_cases"]:
        lines.append("- Similar past messages you already decoded:")
        for c in a["similar_cases"]:
            lines.append(
                f'    • she said "{c["her_message"]}"'
                + (f' ({c["context"]})' if c["context"] else "")
                + f' -> you said it meant: {c["true_meaning"]} '
                f'[{c["intent"]}, {int(c["similarity"]*100)}% similar]'
            )
    if a["note"]:
        lines.append(f"- Model note: {a['note']}")
    return "\n".join(lines)


def _fmt_events(events: list[dict]) -> str:
    if not events:
        return "RECENT EVENTS: (none logged.)"
    lines = ["RECENT EVENTS (most recent first — context for what's going on):"]
    for e in events:
        lines.append(f"- {e['text']}")
    return "\n".join(lines)


def _fmt_research(items: list[dict]) -> str:
    if not items:
        return "OUTSIDE RESEARCH: (none pulled for this one.)"
    lines = ["OUTSIDE RESEARCH (general patterns from the web + psychology papers):"]
    for r in items:
        tag = "🧵 social" if r["source"] == "social" else "📄 research"
        lines.append(f"- [{tag}] {r['title']}: {r['snippet']}")
    return "\n".join(lines)


def _fmt_history(history: list) -> str:
    if not history:
        return ""
    turns = history[-8:]
    lines = ["EARLIER IN THIS CONVO:"]
    for t in turns:
        who = "you" if t.role == "user" else "me"
        lines.append(f"- {who}: {t.content}")
    return "\n".join(lines)


async def get_advice(question: str, reliance: int, use_research: bool,
                     history: list) -> dict:
    n_ml, n_social, n_research = _blend_counts(reliance, use_research)

    analysis = engine.analyze(question, k=n_ml)
    events = db.list_events(limit=8)

    research: list[dict] = []
    if use_research and (n_social + n_research) > 0:
        research = await aggregator.gather(question, n_social, n_research)

    prompt_sections = [
        _fmt_history(history),
        f"HIS QUESTION: {question}",
        "",
        f"RELIANCE SETTING: {reliance}/100. Lean {_reliance_label(reliance)}",
        "",
        _fmt_analysis(analysis),
        "",
        _fmt_events(events),
        "",
        _fmt_research(research),
        "",
        "Now answer him like his bro. Read the situation, weigh the sources per the "
        "reliance setting, and give him a straight take plus one concrete move.",
    ]
    prompt = "\n".join(s for s in prompt_sections if s is not None)

    reply = await claude_client.generate(prompt)

    return {
        "reply": reply,
        "analysis": analysis.to_dict(),
        "research": research,
        "events_used": events,
        "blend": {"ml_cases": n_ml, "social": n_social, "research": n_research},
    }
