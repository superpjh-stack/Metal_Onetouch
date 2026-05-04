"""AI Agent 스키마"""
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AgentQueryRequest(BaseModel):
    query: str
    conversation_id: UUID | None = None


class AgentQueryResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    content: str
    risk_level: Literal["GREEN", "YELLOW", "RED"] | None = None
    sources: list[dict] = []
    latency_ms: int
    tokens_used: int


class ConversationRead(BaseModel):
    id: UUID
    agent_type: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class MessageRead(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    metadata: dict | None
    tokens_used: int | None
    latency_ms: int | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
