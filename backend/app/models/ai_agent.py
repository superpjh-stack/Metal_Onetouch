"""AI Agent 대화 이력 모델"""
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class AIConversation(Base, UUIDMixin):
    """AI 대화 세션"""

    __tablename__ = "ai_conversations"

    agent_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now(), onupdate=func.now(), index=True
    )

    user = relationship("User")
    messages: Mapped[list["AIMessage"]] = relationship(
        "AIMessage",
        back_populates="conversation",
        order_by="AIMessage.created_at",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AIConversation {self.id} agent={self.agent_type}>"


class AIMessage(Base, UUIDMixin):
    """AI 메시지 (불변 — updated_at 없음)"""

    __tablename__ = "ai_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ai_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now(), index=True
    )

    conversation: Mapped[AIConversation] = relationship(
        "AIConversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        return f"<AIMessage {self.id} role={self.role}>"
