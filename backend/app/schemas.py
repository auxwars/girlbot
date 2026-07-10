"""Request/response models for the API."""
from typing import Optional

from pydantic import BaseModel, Field


class AnalyzeIn(BaseModel):
    message: str = Field(..., min_length=1)
    context: str = ""


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1)
    # Optional per-message overrides; fall back to the account's saved defaults.
    reliance: Optional[int] = Field(None, ge=0, le=100)
    use_research: Optional[bool] = None


class SettingsIn(BaseModel):
    anthropic_key: Optional[str] = None
    exa_key: Optional[str] = None
    openalex_mailto: Optional[str] = None
    model: Optional[str] = None
    training_enabled: Optional[bool] = None
    reliance: Optional[int] = Field(None, ge=0, le=100)
    use_research: Optional[bool] = None
