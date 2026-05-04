"""수주 엔드포인트"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DBSession, require_roles
from app.schemas.common import PaginatedResponse
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate
from app.services.order_service import OrderService

router = APIRouter(tags=["Orders"])

_require_manager = require_roles("admin", "production_manager")


@router.get("/", response_model=PaginatedResponse[OrderRead])
async def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    order_status: Optional[str] = Query(None, alias="status"),
    customer_id: Optional[uuid.UUID] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: DBSession,
):
    """수주 목록"""
    svc = OrderService(db)
    items, total = await svc.list_orders(
        order_status=order_status,
        customer_id=customer_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )
    return PaginatedResponse(data=items, total=total, page=page, limit=limit)


@router.post("/", response_model=OrderRead, status_code=201)
async def create_order(
    body: OrderCreate,
    db: DBSession,
    user: CurrentUser,
    _: None = _require_manager,
):
    """수주 등록"""
    svc = OrderService(db)
    order = await svc.create_order(body, created_by=user.id)
    await db.commit()
    return order


@router.get("/{order_id}", response_model=OrderRead)
async def get_order(order_id: uuid.UUID, db: DBSession):
    """수주 상세 (items 포함)"""
    return await OrderService(db).get_order(order_id)


@router.patch("/{order_id}/status", response_model=OrderRead)
async def update_order_status(
    order_id: uuid.UUID,
    body: OrderStatusUpdate,
    db: DBSession,
    user: CurrentUser,
    _: None = _require_manager,
):
    """수주 상태 변경"""
    svc = OrderService(db)
    order = await svc.update_status(order_id, body.status)
    await db.commit()
    return order
