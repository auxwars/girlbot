"""Central configuration, loaded from environment / .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent  # .../backend
FRONTEND_DIR = BASE_DIR.parent / "frontend"
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Load .env sitting next to the backend package.
load_dotenv(BASE_DIR / ".env")


class Settings:
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "").strip()
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8").strip()
    exa_api_key: str = os.getenv("EXA_API_KEY", "").strip()
    openalex_mailto: str = os.getenv("OPENALEX_MAILTO", "").strip()
    db_path: Path = DATA_DIR / "girlbot.db"

    @property
    def has_claude(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_exa(self) -> bool:
        return bool(self.exa_api_key)


settings = Settings()
