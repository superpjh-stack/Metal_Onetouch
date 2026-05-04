"""LangChain Tools for AI Agent"""
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def build_tools(db: AsyncSession, qdrant_client: Any, agent_type: str) -> list:
    """에이전트 타입에 따른 LangChain Tool 목록 반환"""
    from langchain.tools import tool

    collection = "inbound_history" if agent_type == "inbound" else "outbound_history"

    @tool
    async def rag_search_tool(query: str) -> str:
        """과거 입고/출하 이력에서 유사 케이스를 검색합니다."""
        try:
            from fastembed import TextEmbedding

            embedder = TextEmbedding(model_name="BAAI/bge-m3")
            embedding = list(embedder.embed([query]))[0].tolist()

            results = qdrant_client.search(
                collection_name=collection,
                query_vector=embedding,
                limit=5,
                score_threshold=0.70,
            )

            if not results:
                return "유사한 이력을 찾을 수 없습니다."

            items = []
            for r in results:
                items.append(
                    f"- 유사도 {r.score:.2f}: {json.dumps(r.payload, ensure_ascii=False)}"
                )
            return "\n".join(items)
        except Exception as e:
            return f"RAG 검색 실패: {str(e)}"

    @tool
    async def lot_lookup_tool(filters: str) -> str:
        """LOT 정보를 조회합니다. filters: JSON 문자열 예) {\"lot_status\": \"received\"}"""
        try:
            from app.models.lot import Lot

            params = json.loads(filters)
            query = select(Lot).limit(10)

            status_val = params.get("lot_status") or params.get("status")
            if status_val:
                query = query.where(Lot.lot_status == status_val)

            lot_id_val = params.get("lot_id")
            if lot_id_val:
                query = query.where(Lot.lot_id.ilike(f"%{lot_id_val}%"))

            result = await db.execute(query)
            lots = result.scalars().all()

            if not lots:
                return "조건에 맞는 LOT을 찾을 수 없습니다."

            return "\n".join(
                f"- {l.lot_id} [{l.lot_status}] {l.product_name or l.raw_material_name or ''}"
                for l in lots
            )
        except Exception as e:
            return f"LOT 조회 실패: {str(e)}"

    @tool
    async def quality_stats_tool(period_days: int = 30) -> str:
        """최근 불량률 통계를 조회합니다."""
        try:
            from app.services.quality_service import QualityService

            svc = QualityService(db)
            stats = await svc.get_defect_stats(group_by="lot", period_days=period_days)

            if not stats.items:
                return f"최근 {period_days}일간 품질 검사 데이터가 없습니다."

            lines = [f"최근 {period_days}일 불량률 현황:"]
            for item in stats.items[:5]:
                lines.append(
                    f"- {item.group_label}: 검사 {item.total_inspections}건, "
                    f"불합격 {item.fail_count}건, 평균 불량률 {item.avg_defect_rate}%"
                )
            return "\n".join(lines)
        except Exception as e:
            return f"품질 통계 조회 실패: {str(e)}"

    return [rag_search_tool, lot_lookup_tool, quality_stats_tool]
