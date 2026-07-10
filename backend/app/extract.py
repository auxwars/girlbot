"""Auto-learning: when 'training' is on, quietly turn what you tell the bot into
structured data it can learn from.

After each of your messages we ask Claude (structured output) to pull out:
  - labeled examples: "she said X, and it meant Y" -> feeds the from-scratch ML
  - notable events/facts worth remembering -> feeds long-term memory

Runs in the background so it never slows down the reply. If training is off, this
never runs and nothing is learned — you just chat.
"""
import json

from anthropic import AsyncAnthropic

from . import db
from .ml.taxonomy import INTENT_KEYS

_SCHEMA = {
    "type": "object",
    "properties": {
        "examples": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "her_message": {"type": "string"},
                    "context": {"type": "string"},
                    "true_meaning": {"type": "string"},
                    "intent": {"type": "string", "enum": INTENT_KEYS},
                },
                "required": ["her_message", "context", "true_meaning", "intent"],
                "additionalProperties": False,
            },
        },
        "events": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["examples", "events"],
    "additionalProperties": False,
}

_INSTRUCTIONS = (
    "You extract structured data from a guy talking about the girl he's dating.\n"
    "From HIS latest message only, pull two things:\n"
    "1. examples — only when he states, as fact, what one of HER specific messages or "
    "behaviors actually MEANT (e.g. 'when she says do whatever she's actually mad'). "
    "her_message = what she said/did, context = the situation, true_meaning = what it "
    "really meant, intent = the best-fitting category. Do NOT invent examples; if he's "
    "just asking a question or venting with no stated meaning, return an empty list.\n"
    "2. events — notable relationship facts or recent happenings worth remembering "
    "(a fight, her exams, an upcoming date, something she likes/hates). Short strings. "
    "Skip trivia and anything already phrased as a question.\n"
    "Return empty arrays when there's nothing solid. Never guess."
)


async def extract_and_store(user_id: int, user_message: str, api_key: str, model: str) -> None:
    if not api_key or not user_message.strip():
        return
    client = AsyncAnthropic(api_key=api_key)
    try:
        resp = await client.messages.create(
            model=model or "claude-opus-4-8",
            max_tokens=800,
            system=_INSTRUCTIONS,
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
            messages=[{"role": "user", "content": user_message}],
        )
    except Exception:  # noqa: BLE001 - learning is best-effort, never breaks chat
        return

    text = next((b.text for b in resp.content if getattr(b, "type", None) == "text"), "")
    if not text:
        return
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return

    for ex in data.get("examples", []):
        her = (ex.get("her_message") or "").strip()
        meaning = (ex.get("true_meaning") or "").strip()
        intent = (ex.get("intent") or "").strip()
        if not her or not meaning or intent not in INTENT_KEYS:
            continue
        if db.example_exists(user_id, her, meaning):
            continue
        db.add_example(user_id, her, ex.get("context", ""), meaning, intent, is_seed=0)

    for ev in data.get("events", []):
        ev = (ev or "").strip()
        if ev and not db.event_exists(user_id, ev):
            db.add_event(user_id, ev)
