"""
공통 Pydantic 스키마

API 응답 봉투(envelope) 표준화:
  - PaginatedResponse: { "data": [...], "pagination": {...}, "meta": {...} }
  - ErrorResponse:     { "error": { "code": "...", "message": "...", "traceId": "..." } }

설계 문서: docs/02-design/api/api-spec.md
"""
from datetime import datetime
from typing import Generic, List, Optional, TypeVar
import uuid

from pydantic import BaseModel, Field

T = TypeVar("T")


# ------------------------------------------------------------------------------
# Pagination envelope
# ------------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    """페이지네이션 메타 정보"""
    total: int = Field(..., description="전체 레코드 수")
    page: int = Field(..., description="현재 페이지 번호 (1-based)")
    limit: int = Field(..., description="페이지 당 항목 수")
    has_more: bool = Field(..., alias="hasMore", description="다음 페이지 존재 여부")

    model_config = {"populate_by_name": True}


class ResponseMeta(BaseModel):
    """응답 공통 메타 정보"""
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="응답 생성 시각 (UTC)"
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        alias="requestId",
        description="요청 추적 ID",
    )

    model_config = {"populate_by_name": True}


class PaginatedResponse(BaseModel, Generic[T]):
    """
    페이지네이션 목록 응답 봉투 (설계 표준)

    Shape:
    {
        "data": [...],
        "pagination": { "total", "page", "limit", "hasMore" },
        "meta": { "timestamp", "requestId" }
    }
    """
    data: List[T]
    pagination: PaginationMeta
    meta: ResponseMeta = Field(default_factory=ResponseMeta)

    @classmethod
    def build(
        cls,
        items: List[T],
        total: int,
        page: int,
        limit: int,
        request_id: Optional[str] = None,
    ) -> "PaginatedResponse[T]":
        """편의 생성자: 항목 목록과 페이지네이션 파라미터로 봉투를 생성합니다."""
        has_more = (page * limit) < total
        meta = ResponseMeta(
            requestId=request_id or str(uuid.uuid4()),
        )
        return cls(
            data=items,
            pagination=PaginationMeta(
                total=total,
                page=page,
                limit=limit,
                hasMore=has_more,
            ),
            meta=meta,
        )


# ------------------------------------------------------------------------------
# Error envelope
# ------------------------------------------------------------------------------

class ErrorDetail(BaseModel):
    """에러 상세 정보"""
    code: str = Field(..., description="에러 코드 (예: LOT_NOT_FOUND)")
    message: str = Field(..., description="사람이 읽을 수 있는 에러 메시지")
    trace_id: str = Field(..., alias="traceId", description="요청 추적 ID")

    model_config = {"populate_by_name": True}


class ErrorResponse(BaseModel):
    """
    에러 응답 봉투 (설계 표준)

    Shape:
    {
        "error": { "code": "...", "message": "...", "traceId": "..." }
    }
    """
    error: ErrorDetail
