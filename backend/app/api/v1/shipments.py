"""출하/물류 엔드포인트"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DBSession, require_roles
from app.models.shipment import Shipment, ShipmentLot
from app.schemas.common import PaginatedResponse
from app.schemas.shipment import (
    ShipmentCreate,
    ShipmentLotItem,
    ShipmentRead,
    ShipmentStatusUpdate,
    ShipmentUpdate,
)
from app.services.shipment_service import ShipmentService

router = APIRouter(tags=["Shipments"])

_require_manager = require_roles("admin", "production_manager")


@router.get("/pending", response_model=list[ShipmentRead])
async def get_pending_shipments(db: DBSession):
    """출하 대기 목록 (대시보드 연동용)"""
    result = await db.execute(
        select(Shipment)
        .options(joinedload(Shipment.lots))
        .where(Shipment.status == "pending")
        .order_by(Shipment.planned_date.asc())
    )
    return [ShipmentRead.model_validate(s) for s in result.scalars().unique().all()]


@router.get("/", response_model=PaginatedResponse[ShipmentRead])
async def list_shipments(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    ship_status: Optional[str] = Query(None, alias="status"),
    customer_id: Optional[uuid.UUID] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: DBSession,
):
    """출하 목록 조회"""
    filters = []
    if ship_status:
        filters.append(Shipment.status == ship_status)
    if customer_id:
        filters.append(Shipment.customer_id == customer_id)
    if date_from:
        filters.append(Shipment.planned_date >= date_from)
    if date_to:
        filters.append(Shipment.planned_date <= date_to)

    total = (await db.execute(
        select(func.count(Shipment.id)).where(*filters)
    )).scalar_one()

    items_result = await db.execute(
        select(Shipment)
        .options(joinedload(Shipment.lots))
        .where(*filters)
        .order_by(Shipment.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items = [
        ShipmentRead.model_validate(s)
        for s in items_result.scalars().unique().all()
    ]
    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.post(
    "/",
    response_model=ShipmentRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_manager],
)
async def create_shipment(
    body: ShipmentCreate,
    db: DBSession,
    current_user: CurrentUser,
):
    """출하 등록 + LOT 묶음 + shipment_number 자동 생성"""
    shipment = await ShipmentService(db).create_shipment(
        data=body, created_by=current_user.id
    )
    return ShipmentRead.model_validate(shipment)


@router.get("/{shipment_id}", response_model=ShipmentRead)
async def get_shipment(shipment_id: uuid.UUID, db: DBSession):
    """출하 상세 + 포함 LOT 목록"""
    result = await db.execute(
        select(Shipment)
        .options(joinedload(Shipment.lots))
        .where(Shipment.id == shipment_id)
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="출하를 찾을 수 없습니다")
    return ShipmentRead.model_validate(shipment)


@router.patch(
    "/{shipment_id}/status",
    response_model=ShipmentRead,
    dependencies=[_require_manager],
)
async def update_shipment_status(
    shipment_id: uuid.UUID,
    body: ShipmentStatusUpdate,
    db: DBSession,
):
    """출하 상태 전환 (shipped/delivered/cancelled)"""
    result = await db.execute(
        select(Shipment).where(Shipment.id == shipment_id)
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="출하를 찾을 수 없습니다")

    shipment = await ShipmentService(db).update_status(
        shipment=shipment, new_status=body.status, notes=body.notes
    )
    return ShipmentRead.model_validate(shipment)


@router.post(
    "/{shipment_id}/lots",
    response_model=ShipmentRead,
    dependencies=[_require_manager],
)
async def add_lots_to_shipment(
    shipment_id: uuid.UUID,
    body: list[ShipmentLotItem],
    db: DBSession,
):
    """출하에 LOT 추가 (pending 상태일 때만)"""
    shipment = await ShipmentService(db).add_lots(
        shipment_id=shipment_id, lots=body
    )
    return ShipmentRead.model_validate(shipment)
