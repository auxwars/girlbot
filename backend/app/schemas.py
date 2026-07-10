"""Request/response models for the API."""
from typing import Optional

from pydantic import BaseModel, Field


class ExampleIn(BaseModel):
    her_message: str = Field(..., min_length=1)
    context: str = ""
    true_meaning: str = Field(..., min_length=1)
    intent: str = Field(..., min_length=1)


class EventIn(BaseModel):
    text: str = Field(..., min_length=1)


class AnalyzeIn(BaseModel):
    message: str = Field(..., min_length=1)
    context: str = ""


class ChatTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class AdviceIn(BaseModel):
    question: str = Field(..., min_length=1)
    # 0 = lean entirely on outside research, 100 = lean entirely on her data.
    reliance: int = Field(60, ge=0, le=100)
    use_research: bool = True
    history: list[ChatTurn] = []
