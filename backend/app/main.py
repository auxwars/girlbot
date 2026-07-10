"""FastAPI app: the API under /api, Google auth under /auth, the two-page
frontend (chat + settings) served at /.
"""
import asyncio

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import advice, auth, db, extract, prefs
from .config import FRONTEND_DIR, settings
from .ml.engine import engine
from .ml.seed import ensure_seed
from .ml.taxonomy import INTENTS
from .schemas import AnalyzeIn, ChatIn, SettingsIn

app = FastAPI(title="girlbot", version="0.2.0")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key, same_site="lax")
app.include_router(auth.router)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


def user_dep(request: Request) -> dict:
    return auth.require_user(request)


def _seed_once(user_id: int) -> None:
    """Load demo data the first time an account is used (not after a clear)."""
    if not db.get_settings(user_id).get("seeded"):
        ensure_seed(user_id)
        db.mark_seeded(user_id)


# --------------------------------------------------------------------------
# session / account
# --------------------------------------------------------------------------

@app.get("/api/me")
def me(request: Request) -> dict:
    user = auth.current_user(request)
    base = {
        "google_enabled": settings.has_google,
        "authenticated": user is not None,
    }
    if user is None:
        return base
    _seed_once(user["id"])
    eff = prefs.effective(user["id"])
    return {
        **base,
        "user": {"name": user.get("name"), "email": user.get("email"),
                 "picture": user.get("picture")},
        "prefs": {
            "reliance": eff["reliance"],
            "use_research": eff["use_research"],
            "training_enabled": eff["training_enabled"],
            "model": eff["model"],
            "has_anthropic": bool(eff["anthropic_key"]),
            "has_exa": bool(eff["exa_key"]),
            "has_openalex": bool(eff["openalex_mailto"]),
        },
        "example_count": db.count_examples(user["id"]),
    }


@app.get("/api/settings")
def get_settings(user: dict = Depends(user_dep)) -> dict:
    s = db.get_settings(user["id"])
    # returns the account's own saved values (behind its own login) for prefill
    return {
        "anthropic_key": s["anthropic_key"],
        "exa_key": s["exa_key"],
        "openalex_mailto": s["openalex_mailto"],
        "model": s["model"],
        "training_enabled": bool(s["training_enabled"]),
        "reliance": s["reliance"],
        "use_research": bool(s["use_research"]),
        "env_defaults": {
            "anthropic": bool(settings.anthropic_api_key),
            "exa": bool(settings.exa_api_key),
            "openalex": bool(settings.openalex_mailto),
            "model": settings.anthropic_model,
        },
    }


@app.post("/api/settings")
def update_settings(body: SettingsIn, user: dict = Depends(user_dep)) -> dict:
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if "training_enabled" in fields:
        fields["training_enabled"] = 1 if fields["training_enabled"] else 0
    if "use_research" in fields:
        fields["use_research"] = 1 if fields["use_research"] else 0
    db.save_settings(user["id"], **fields)
    return {"ok": True}


# --------------------------------------------------------------------------
# chat (with persistent memory + optional auto-learning)
# --------------------------------------------------------------------------

@app.get("/api/history")
def history(user: dict = Depends(user_dep)) -> dict:
    return {"messages": db.list_messages(user["id"])}


@app.post("/api/memory/clear")
def clear_memory(user: dict = Depends(user_dep)) -> dict:
    n = db.clear_messages(user["id"])
    return {"removed": n}


@app.post("/api/chat")
async def chat(body: ChatIn, user: dict = Depends(user_dep)) -> dict:
    uid = user["id"]
    _seed_once(uid)
    eff = prefs.effective(uid)
    reliance = body.reliance if body.reliance is not None else eff["reliance"]
    use_research = body.use_research if body.use_research is not None else eff["use_research"]

    result = await advice.build_reply(uid, body.message, eff, reliance, use_research)

    # persist this turn to memory (after building, so history stays clean)
    db.add_message(uid, "user", body.message)
    db.add_message(uid, "assistant", result["reply"])

    # auto-learn from what he said, in the background, only if training is on
    if eff["training_enabled"] and eff["anthropic_key"]:
        asyncio.create_task(
            extract.extract_and_store(uid, body.message, eff["anthropic_key"], eff["model"])
        )

    result["training_on"] = eff["training_enabled"]
    return result


# --------------------------------------------------------------------------
# learned data (viewed / managed from Settings)
# --------------------------------------------------------------------------

@app.get("/api/intents")
def intents() -> dict:
    return {"intents": INTENTS}


@app.get("/api/examples")
def get_examples(user: dict = Depends(user_dep)) -> dict:
    return {"examples": db.list_examples(user["id"])}


@app.delete("/api/examples/{example_id}")
def remove_example(example_id: int, user: dict = Depends(user_dep)) -> dict:
    db.delete_example(user["id"], example_id)
    return {"ok": True}


@app.post("/api/examples/clear-seed")
def clear_seed(user: dict = Depends(user_dep)) -> dict:
    return {"removed": db.clear_seed_examples(user["id"])}


@app.post("/api/examples/clear-all")
def clear_all_examples(user: dict = Depends(user_dep)) -> dict:
    return {"removed": db.clear_all_examples(user["id"])}


@app.get("/api/events")
def get_events(user: dict = Depends(user_dep)) -> dict:
    return {"events": db.list_events(user["id"])}


@app.delete("/api/events/{event_id}")
def remove_event(event_id: int, user: dict = Depends(user_dep)) -> dict:
    db.delete_event(user["id"], event_id)
    return {"ok": True}


@app.post("/api/analyze")
def analyze(body: AnalyzeIn, user: dict = Depends(user_dep)) -> dict:
    return engine.analyze(user["id"], body.message, body.context).to_dict()


# --------------------------------------------------------------------------
# frontend (mounted last so /api/* and /auth/* win)
# --------------------------------------------------------------------------
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
