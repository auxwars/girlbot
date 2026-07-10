"""Resolve the *effective* settings for a user: their saved values take
precedence, falling back to the environment defaults from config.
"""
from . import db
from .config import settings


def effective(user_id: int) -> dict:
    s = db.get_settings(user_id)
    return {
        "anthropic_key": (s["anthropic_key"] or "").strip() or settings.anthropic_api_key,
        "model": (s["model"] or "").strip() or settings.anthropic_model,
        "exa_key": (s["exa_key"] or "").strip() or settings.exa_api_key,
        "openalex_mailto": (s["openalex_mailto"] or "").strip() or settings.openalex_mailto,
        "training_enabled": bool(s["training_enabled"]),
        "reliance": int(s["reliance"]),
        "use_research": bool(s["use_research"]),
    }
