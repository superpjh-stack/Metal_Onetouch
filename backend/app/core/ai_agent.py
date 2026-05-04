"""LangChain Agent 빌더 — GPT-4o + Qdrant RAG"""
import os
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


INBOUND_SYSTEM_PROMPT = """당신은 금속 가공 제조업체의 입고 AI Agent입니다.
과거 입고 이력 데이터를 기반으로 품질 이상 패턴을 감지하고 사용자에게 안내합니다.

규칙:
1. 항상 한국어로 응답하세요.
2. 데이터 기반 근거를 반드시 제시하세요 (환각 금지).
3. 불확실한 경우 "데이터 부족으로 판단 불가"라고 명시하세요.
4. RAG 검색 결과가 없으면 "유사 이력 없음"이라고 명시하세요.
"""

OUTBOUND_SYSTEM_PROMPT = """당신은 금속 가공 제조업체의 출하 AI Agent입니다.
출하 LOT의 품질 리스크를 GREEN/YELLOW/RED로 평가하고 배송 최적화를 제안합니다.

리스크 등급 기준:
- GREEN: 불량률 < 2% AND 클레임 이력 없음
- YELLOW: 불량률 2~5% OR 클레임 이력 1건
- RED: 불량률 > 5% OR 클레임 이력 2건 이상

규칙:
1. 항상 한국어로 응답하세요.
2. 응답 마지막에 반드시 리스크 등급을 명시하세요: 예) 📊 리스크 등급: GREEN
3. 데이터 기반 근거를 반드시 제시하세요.
"""


async def build_agent(agent_type: str, db: AsyncSession) -> Any:
    """LangChain AgentExecutor 빌드"""
    from langchain.agents import AgentExecutor, create_openai_functions_agent
    from langchain.memory import ConversationBufferWindowMemory
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_openai import ChatOpenAI

    from app.core.qdrant_init import get_qdrant_client
    from app.core.ai_tools import build_tools

    system_prompt = INBOUND_SYSTEM_PROMPT if agent_type == "inbound" else OUTBOUND_SYSTEM_PROMPT

    llm = ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    qdrant_client = get_qdrant_client()
    tools = build_tools(db=db, qdrant_client=qdrant_client, agent_type=agent_type)

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad"),
    ])

    agent = create_openai_functions_agent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=False, max_iterations=5)
