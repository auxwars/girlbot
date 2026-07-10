"""Central configuration, loaded from environment / .env.

Env vars are DEFAULTS. Most of these (API keys, model, toggles) can also be set
per-account from the in-app Settings page, which takes precedence.
"""
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend
FRONTEND_DIR = BASE_DIR.parent / "frontend"

load_dotenv(BASE_DIR / ".env")


def _data_dir() -> Path:
    # On Railway, mount a Volume and point GIRLBOT_DATA_DIR at it (e.g. /data)
    # so the SQLite database — and therefore all memory — survives redeploys.
    override = os.getenv("GIRLBOT_DATA_DIR", "").strip()
    p = Path(override) if override else (BASE_DIR / "data")
    p.mkdir(parents=True, exist_ok=True)
    return p


DATA_DIR = _data_dir()


class Settings:
    # --- Anthropic (default; overridable per-account in Settings) ---------
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8").strip()

    # --- Research providers (default; overridable per-account) ------------
    exa_api_key: str = os.getenv("EXA_API_KEY", "").strip()
    openalex_mailto: str = os.getenv("OPENALEX_MAILTO", "").strip()

    # --- storage ----------------------------------------------------------
    db_path: Path = DATA_DIR / "girlbot.db"

    # --- session signing --------------------------------------------------
    # MUST be set to a fixed value in production or logins drop on restart.
    secret_key: str = os.getenv("SECRET_KEY", "").strip() or ("dev-" + secrets.token_hex(8))

    # --- Google OAuth (optional; enables permanent per-account memory) ----
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    # Exact redirect URI registered in Google Cloud Console, e.g.
    #   https://your-app.up.railway.app/auth/callback
    google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "").strip()

    port: int = int(os.getenv("PORT", "8000"))

    @property
    def has_google(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)


settings = Settings()
