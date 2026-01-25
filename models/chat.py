"""Schemas for chat API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single message in conversation history."""

    role: str = Field(..., description="'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request body for POST /chat."""

    message: str = Field(..., min_length=1, description="User's message to the immigration consultant")
    history: list[ChatMessage] | None = Field(
        default=None,
        description="Optional conversation history for multi-turn chat",
    )


class ChatResponse(BaseModel):
    """Response for POST /chat."""

    reply: str = Field(..., description="Immigration consultant's reply")
