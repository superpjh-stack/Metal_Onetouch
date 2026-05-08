"""원자재 입고 엔드포인트"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession, require_roles
from app.schemas.common import PaginatedResponse
from app.schemas.inbound import ReceiptCreate, ReceiptRead, SupplierReceiptStats
from app.services.inbound_service import InboundService

router = APIRouter(tags=["Inbound"])

_require_manager = require_roles("admin", "production_manager")


@router.post("/", response_model=ReceiptRead, status_code=201)
async def create_receipt(
    body: ReceiptCreate,
    db: DBSession = None,
    user: CurrentUser = None,
    _: None = _require_manager,
):
    """입고 등록 + LOT 자동 생성"""
    svc = InboundService(db)
    receipt = await svc.create_receipt(body, created_by=user.id)
    await db.commit()
    return receipt


@router.get("/stats/supplier", response_model=list[SupplierReceiptStats])
async def get_supplier_stats(
    period_days: int = Query(30, ge=1, le=365),
    db: DBSession = None,
):
    """공급처별 입고 통계 — 반드시 GET / 보다 먼저 등록"""
    svc = InboundService(db)
    return await svc.get_supplier_stats(period_days=period_days)


@router.get("/", response_model=PaginatedResponse[ReceiptRead])
async def list_receipts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    supplier_id: Optional[uuid.UUID] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: DBSession = None,
):
    """입고 목록 조회"""
    svc = InboundService(db)
    items, total = await svc.list_receipts(
        supplier_id=supplier_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )
    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.get("/{receipt_id}", response_model=ReceiptRead)
async def get_receipt(receipt_id: uuid.UUID, db: DBSession = None):
    """입고 상세"""
    svc = InboundService(db)
    return await svc.get_receipt(receipt_id)

