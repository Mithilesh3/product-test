from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1, max_length=1200)


class SwarChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1500)
    language_preference: Optional[Literal["auto", "hindi", "english", "hinglish"]] = "auto"
    history: list[ChatHistoryMessage] = Field(default_factory=list)


class SwarChatResponse(BaseModel):
    reply: str
    language: Literal["hindi", "english", "hinglish"]
    safe_guard_applied: bool = False
    warning_count: int = 0
    account_blocked: bool = False
