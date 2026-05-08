"""견적서 엔드포인트"""
import uuid
from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession, require_roles
from app.schemas.common import PaginatedResponse
from app.schemas.quotation import (
    QuotationCreate,
    QuotationItemUpdate,
    QuotationLinkOrder,
    QuotationRead,
    QuotationSummary,
)
from app.schemas.bom import BomRead
from app.services.bom_service import BomService
from app.services.quotation_service import QuotationService

router = APIRouter(tags=["Quotations"])

_require_sales = require_roles("admin", "sales", "production_manager")


@router.post("/", response_model=QuotationRead, status_code=201)
async def create_quotation(
    body: QuotationCreate,
    db: DBSession = None,
    user: CurrentUser = None,
    _: None = _require_sales,
):
    """CAD 도면 기반 자동 견적 생성"""
    svc = QuotationService(db)
    quotation = await svc.calculate_from_drawing(body, created_by=user.id)
    await db.commit()
    return quotation


@router.get("/", response_model=PaginatedResponse[QuotationSummary])
async def list_quotations(
    db: DBSession = None,
    _: CurrentUser = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    customer_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
):
    """견적 목록"""
    svc = QuotationService(db)
    items, total = await svc.list_quotations(
        customer_id=customer_id,
        status=status,
        page=page,
        limit=limit,
    )
    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.get("/{quotation_id}", response_model=QuotationRead)
async def get_quotation(quotation_id: uuid.UUID, db: DBSession = None, _: CurrentUser = None):
    """견적 상세 (항목 포함)"""
    return await QuotationService(db).get_quotation(quotation_id)


@router.patch("/{quotation_id}/items", response_model=QuotationRead)
async def update_items(
    quotation_id: uuid.UUID,
    body: list[QuotationItemUpdate],
    db: DBSession = None,
    user: CurrentUser = None,
    _: None = _require_sales,
):
    """견적 항목 단가/수량 수정 (draft 상태만)"""
    svc = QuotationService(db)
    result = await svc.update_items(quotation_id, body)
    await db.commit()
    return result


@router.post("/{quotation_id}/submit", response_model=QuotationRead)
async def submit_quotation(
    quotation_id: uuid.UUID,
    db: DBSession = None,
    user: CurrentUser = None,
    _: None = _require_sales,
):
    """견적 제출 (draft → submitted)"""
    svc = QuotationService(db)
    result = await svc.transition_status(quotation_id, "submitted")
    await db.commit()
    return result


@router.patch("/{quotation_id}/link-order", response_model=QuotationRead)
async def link_order(
    quotation_id: uuid.UUID,
    body: QuotationLinkOrder,
    db: DBSession = None,
    user: CurrentUser = None,
    _: None = _require_sales,
):
    """수주 연결"""
    svc = QuotationService(db)
    result = await svc.link_order(quotation_id, body)
    await db.commit()
    return result


@router.get("/{quotation_id}/similar", response_model=list[QuotationSummary])
async def similar_quotations(
    quotation_id: uuid.UUID,
    db: DBSession = None,
    _: CurrentUser = None,
    top_k: int = Query(5, ge=1, le=20),
):
    """유사 견적 검색 (Qdrant 벡터 / DB 폴백)"""
    return await QuotationService(db).find_similar_quotations(quotation_id, top_k=top_k)


@router.post("/{quotation_id}/bom", response_model=BomRead, status_code=201)
async def generate_bom(
    quotation_id: uuid.UUID,
    db: DBSession = None,
    user: CurrentUser = None,
):
    """확정 견적에서 BOM 자동생성"""
    result = await BomService(db).generate_from_quotation(quotation_id, created_by=user.id)
    await db.commit()
    return result


@router.get("/{quotation_id}/bom", response_model=Optional[BomRead])
async def get_bom(quotation_id: uuid.UUID, db: DBSession = None, _: CurrentUser = None):
    """견적서 BOM 조회"""
    return await BomService(db).get_bom(quotation_id)

