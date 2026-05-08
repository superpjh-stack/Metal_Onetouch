"""AI Agent Service Layer — LangChain + Qdrant RAG"""
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_agent import AIConversation, AIMessage
from app.schemas.ai_agent import AgentQueryResponse


def _extract_risk_level(content: str) -> str | None:
    """응답 텍스트에서 리스크 등급 추출"""
    for level in ("RED", "YELLOW", "GREEN"):
        if level in content.upper():
            return level
    return None


class AIAgentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def query(
        self,
        agent_type: str,
        query_text: str,
        conversation_id: uuid.UUID | None,
        user_id: uuid.UUID,
    ) -> AgentQueryResponse:
        conversation = await self._get_or_create_conversation(
            agent_type=agent_type,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        start_ms = int(time.time() * 1000)

        try:
            from app.core.ai_agent import build_agent
            agent = await build_agent(agent_type=agent_type, db=self.db)
            response = await agent.ainvoke({"input": query_text})
            content: str = response.get("output", "응답을 생성할 수 없습니다")
            sources: list[dict] = response.get("sources", [])
        except ImportError:
            # LangChain/Qdrant 미설치 환경 폴백
            content = (
                f"[AI Agent — {agent_type}]\n"
                f"질의: {query_text}\n\n"
                "⚠️ AI Agent 패키지(langchain, qdrant-client)가 설치되지 않았습니다. "
                "requirements.txt에 langchain, langchain-openai, qdrant-client, fastembed를 추가 후 재설치하세요."
            )
            sources = []
        except Exception as e:
            content = f"AI Agent 처리 중 오류가 발생했습니다: {str(e)}"
            sources = []

        latency_ms = int(time.time() * 1000) - start_ms
        tokens_used = len(content.split()) * 2  # 근사치

        message = await self._save_messages(
            conversation=conversation,
            user_query=query_text,
            assistant_response=content,
            metadata={"sources": sources, "agent_type": agent_type},
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )

        risk_level = _extract_risk_level(content) if agent_type == "outbound" else None

        return AgentQueryResponse(
            conversation_id=conversation.id,
            message_id=message.id,
            content=content,
            risk_level=risk_level,
            sources=sources,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )

    async def _get_or_create_conversation(
        self,
        agent_type: str,
        user_id: uuid.UUID,
        conversation_id: uuid.UUID | None,
    ) -> AIConversation:
        if conversation_id:
            result = await self.db.execute(
                select(AIConversation).where(
                    AIConversation.id == conversation_id,
                    AIConversation.user_id == user_id,
                )
            )
            conv = result.scalar_one_or_none()
            if conv:
                return conv

        conv = AIConversation(
            agent_type=agent_type,
            user_id=user_id,
        )
        self.db.add(conv)
        await self.db.flush()
        return conv

    async def _save_messages(
        self,
        conversation: AIConversation,
        user_query: str,
        assistant_response: str,
        metadata: dict[str, Any],
        latency_ms: int,
        tokens_used: int,
    ) -> AIMessage:
        user_msg = AIMessage(
            conversation_id=conversation.id,
            role="user",
            content=user_query,
        )
        self.db.add(user_msg)

        assistant_msg = AIMessage(
            conversation_id=conversation.id,
            role="assistant",
            content=assistant_response,
            msg_metadata=metadata,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
        )
        self.db.add(assistant_msg)

        # 대화 제목: 첫 메시지 앞 50자
        if not conversation.title:
            conversation.title = user_query[:50]
        conversation.updated_at = datetime.now(timezone.utc)

        await self.db.flush()
        await self.db.refresh(assistant_msg)
        return assistant_msg

    async def list_conversations(
        self, user_id: uuid.UUID, agent_type: str | None = None, limit: int = 20
    ) -> list[AIConversation]:
        filters = [AIConversation.user_id == user_id]
        if agent_type:
            filters.append(AIConversation.agent_type == agent_type)

        result = await self.db.execute(
            select(AIConversation)
            .where(*filters)
            .order_by(AIConversation.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_messages(
        self, conversation_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[AIMessage]:
        conv_result = await self.db.execute(
            select(AIConversation).where(
                AIConversation.id == conversation_id,
                AIConversation.user_id == user_id,
            )
        )
        if not conv_result.scalar_one_or_none():
            return []

        result = await self.db.execute(
            select(AIMessage)
            .where(AIMessage.conversation_id == conversation_id)
            .order_by(AIMessage.created_at)
        )
        return list(result.scalars().all())
