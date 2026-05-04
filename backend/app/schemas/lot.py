import uuid
from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ------------------------------------------------------------------------------
# LOT CRUD 스키마
# ------------------------------------------------------------------------------

class LotCreate(BaseModel):
    """LOT 생성 요청 스키마"""
    raw_material_id: Optional[str] = Field(None, description="원자재 ID")
    raw_material_name: Optional[str] = Field(None, max_length=200, description="원자재명")
    quantity: Optional[float] = Field(None, gt=0, description="수량")
    unit: Optional[str] = Field(None, max_length=20, description="단위 (kg, ea, m ...)")

    customer_name: Optional[str] = Field(None, max_length=200, description="고객사명")
    product_code: Optional[str] = Field(None, max_length=50, description="제품 코드")
    product_name: Optional[str] = Field(None, max_length=200, description="제품명")
    order_number: Optional[str] = Field(None, max_length=50, description="수주 번호")

    planned_start_date: Optional[date] = Field(None, description="계획 시작일")
    planned_end_date: Optional[date] = Field(None, description="계획 종료일")

    notes: Optional[str] = Field(None, description="비고")

    model_config = {
        "json_schema_extra": {
            "example": {
                "raw_material_id": "RM-2024-001",
                "raw_material_name": "SUS304 판재",
                "quantity": 500.0,
                "unit": "kg",
                "customer_name": "삼성전자",
                "product_code": "PROD-001",
                "product_name": "프레스 판금 부품 A",
                "order_number": "ORD-20260430-001",
                "planned_start_date": "2026-05-01",
                "planned_end_date": "2026-05-10",
            }
        }
    }


class LotUpdate(BaseModel):
    """LOT 수정 요청 스키마 (부분 수정)"""
    raw_material_id: Optional[str] = None
    raw_material_name: Optional[str] = None
    quantity: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = None
    customer_name: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    order_number: Optional[str] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    notes: Optional[str] = None


class LotRead(BaseModel):
    """LOT 조회 응답 스키마"""
    id: uuid.UUID
    lot_id: str
    lot_status: str
    raw_material_id: Optional[str] = None
    raw_material_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    customer_name: Optional[str] = None
    product_code: Optional[str] = None
    product_name: Optional[str] = None
    order_number: Optional[str] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    notes: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# LotListResponse is now an alias of PaginatedResponse[LotRead].
# Import kept here for backwards compatibility within this module.
# Use app.schemas.common.PaginatedResponse for the response envelope.


# ------------------------------------------------------------------------------
# LOT 상태 변경
# ------------------------------------------------------------------------------

class LotStatusUpdate(BaseModel):
    """LOT 상태 변경 요청 스키마"""
    status: str = Field(..., description="변경할 상태값")
    reason: Optional[str] = Field(None, description="상태 변경 사유")
    detail: Optional[str] = Field(None, description="추가 세부 정보")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "in_process",
                "reason": "원자재 입고 완료 후 가공 공정 시작",
                "detail": "CNC 선반 작업 지시서 #2024-0501",
            }
        }
    }


# ------------------------------------------------------------------------------
# LOT 이력
# ------------------------------------------------------------------------------

class LotHistoryItem(BaseModel):
    """LOT 이력 단일 항목 스키마"""
    id: uuid.UUID
    step: str = Field(..., description="이력 단계명")
    from_status: Optional[str] = Field(None, description="이전 상태")
    to_status: Optional[str] = Field(None, description="변경 후 상태")
    actor_id: Optional[uuid.UUID] = Field(None, description="처리자 ID")
    actor_name: Optional[str] = Field(None, description="처리자명")
    detail: Optional[str] = Field(None, description="세부 내용")
    reason: Optional[str] = Field(None, description="변경 사유")
    timestamp: datetime = Field(..., description="발생 시각")

    model_config = {"from_attributes": True}


class LotHistoryResponse(BaseModel):
    """LOT 이력 타임라인 응답 스키마"""
    lot_id: str
    lot_status: str
    timeline: List[LotHistoryItem]


# ------------------------------------------------------------------------------
# LOT 역추적 (Traceability)
# ------------------------------------------------------------------------------

class TraceabilityNode(BaseModel):
    """역추적 트리 노드"""
    step: str
    status: str
    actor: Optional[str] = None
    timestamp: Optional[datetime] = None
    detail: Optional[str] = None
    children: List["TraceabilityNode"] = []


TraceabilityNode.model_rebuild()


class LotTraceabilityReport(BaseModel):
    """LOT 완전 역추적 보고서"""
    lot_id: str
    lot_status: str
    raw_material_id: Optional[str] = None
    raw_material_name: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    customer_name: Optional[str] = None
    product_name: Optional[str] = None
    order_number: Optional[str] = None
    planned_start_date: Optional[date] = None
    planned_end_date: Optional[date] = None
    actual_start_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    created_at: datetime
    history_tree: List[TraceabilityNode]
    total_history_count: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)
