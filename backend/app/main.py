"""FastAPI app: the API under /api, the two-page frontend served at /."""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from . import advice, db
from .config import settings
from .ml.engine import engine
from .ml.seed import ensure_seed
from .ml.taxonomy import INTENTS
from .schemas import AdviceIn, AnalyzeIn, EventIn, ExampleIn

app = FastAPI(title="girlbot", version="0.1.0")


@app.on_event("startup")
def _startup() -> None:
    db.init_db()
    ensure_seed()


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "claude_enabled": settings.has_claude,
        "model": settings.anthropic_model,
        "exa_enabled": settings.has_exa,
        "example_count": db.count_examples(),
    }


@app.get("/api/intents")
def intents() -> dict:
    return {"intents": INTENTS}


# ---- training data -------------------------------------------------------

@app.get("/api/examples")
def get_examples() -> dict:
    return {"examples": db.list_examples()}


@app.post("/api/examples")
def create_example(body: ExampleIn) -> dict:
    new_id = db.add_example(body.her_message, body.context,
                            body.true_meaning, body.intent, is_seed=0)
    return {"id": new_id}


@app.delete("/api/examples/{example_id}")
def remove_example(example_id: int) -> dict:
    db.delete_example(example_id)
    return {"ok": True}


@app.post("/api/examples/clear-seed")
def clear_seed() -> dict:
    removed = db.clear_seed_examples()
    return {"removed": removed}


# ---- events (memory) -----------------------------------------------------

@app.get("/api/events")
def get_events() -> dict:
    return {"events": db.list_events()}


@app.post("/api/events")
def create_event(body: EventIn) -> dict:
    new_id = db.add_event(body.text)
    return {"id": new_id}


@app.delete("/api/events/{event_id}")
def remove_event(event_id: int) -> dict:
    db.delete_event(event_id)
    return {"ok": True}


# ---- ML preview (transparency) -------------------------------------------

@app.post("/api/analyze")
def analyze(body: AnalyzeIn) -> dict:
    return engine.analyze(body.message, body.context).to_dict()


# ---- the actual chat -----------------------------------------------------

@app.post("/api/advice")
async def get_advice(body: AdviceIn) -> dict:
    if not body.question.strip():
        raise HTTPException(400, "empty question")
    return await advice.get_advice(
        question=body.question,
        reliance=body.reliance,
        use_research=body.use_research,
        history=body.history,
    )


# --------------------------------------------------------------------------
# Frontend (mounted last so /api/* routes win). html=True serves index.html
# at "/" and train.html at "/train.html".
# --------------------------------------------------------------------------
from .config import FRONTEND_DIR  # noqa: E402

app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
