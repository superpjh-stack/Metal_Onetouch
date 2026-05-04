"""AI Agent 엔드포인트"""
import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession
from app.schemas.ai_agent import (
    AgentQueryRequest,
    AgentQueryResponse,
    ConversationRead,
    MessageRead,
)
from app.services.ai_agent_service import AIAgentService

router = APIRouter(tags=["AI Agent"])


@router.post("/inbound", response_model=AgentQueryResponse)
async def query_inbound_agent(
    body: AgentQueryRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """입고 AI Agent 질의 — LangChain + Qdrant RAG (inbound_history)"""
    return await AIAgentService(db).query(
        agent_type="inbound",
        query_text=body.query,
        conversation_id=body.conversation_id,
        user_id=current_user.id,
    )


@router.post("/outbound", response_model=AgentQueryResponse)
async def query_outbound_agent(
    body: AgentQueryRequest,
    db: DBSession,
    current_user: CurrentUser,
):
    """출하 AI Agent 질의 + 리스크 등급 (GREEN/YELLOW/RED) 반환"""
    return await AIAgentService(db).query(
        agent_type="outbound",
        query_text=body.query,
        conversation_id=body.conversation_id,
        user_id=current_user.id,
    )


@router.get("/conversations", response_model=list[ConversationRead])
async def list_conversations(
    agent_type: Optional[str] = Query(None, pattern="^(inbound|outbound|integrated)$"),
    limit: int = Query(20, ge=1, le=50),
    db: DBSession,
    current_user: CurrentUser,
):
    """현재 사용자 대화 목록"""
    conversations = await AIAgentService(db).list_conversations(
        user_id=current_user.id,
        agent_type=agent_type,
        limit=limit,
    )
    return [ConversationRead.model_validate(c) for c in conversations]


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageRead],
)
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
):
    """특정 대화의 메시지 목록"""
    messages = await AIAgentService(db).get_messages(
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    return [MessageRead.model_validate(m) for m in messages]
