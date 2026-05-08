"""작업지시 엔드포인트"""
import uuid
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.api.deps import CurrentUser, DBSession, require_roles
from app.models.work_order import ProcessResult, WorkOrder
from app.schemas.common import PaginatedResponse
from app.schemas.work_order import (
    ProcessResultCreate,
    ProcessResultRead,
    WorkOrderCreate,
    WorkOrderRead,
    WorkOrderStatusUpdate,
    WorkOrderUpdate,
)
from app.services.work_order_service import WorkOrderService

router = APIRouter(tags=["Work Orders"])

_require_wo_write = require_roles("admin", "production_manager", "process_engineer")
_require_result_write = require_roles(
    "admin", "production_manager", "process_engineer", "quality_inspector"
)


async def _get_wo_or_404(wo_id: uuid.UUID, db) -> WorkOrder:
    result = await db.execute(
        select(WorkOrder)
        .options(joinedload(WorkOrder.process_results))
        .where(WorkOrder.id == wo_id)
    )
    wo = result.scalar_one_or_none()
    if not wo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="작업지시를 찾을 수 없습니다"
        )
    return wo


@router.get("/", response_model=PaginatedResponse[WorkOrderRead])
async def list_work_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    wo_status: Optional[str] = Query(None, alias="status"),
    lot_id: Optional[uuid.UUID] = Query(None),
    assigned_to: Optional[uuid.UUID] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: DBSession = None,
):
    """작업지시 목록 조회"""
    filters = []
    if wo_status is not None:
        filters.append(WorkOrder.status == wo_status)
    if lot_id is not None:
        filters.append(WorkOrder.lot_id == lot_id)
    if assigned_to is not None:
        filters.append(WorkOrder.assigned_to == assigned_to)
    if date_from is not None:
        from_dt = datetime(date_from.year, date_from.month, date_from.day, tzinfo=timezone.utc)
        filters.append(WorkOrder.planned_start >= from_dt)
    if date_to is not None:
        to_dt = datetime(date_to.year, date_to.month, date_to.day, 23, 59, 59, tzinfo=timezone.utc)
        filters.append(WorkOrder.planned_end <= to_dt)

    total_result = await db.execute(
        select(func.count(WorkOrder.id)).where(*filters)
    )
    total = total_result.scalar_one()

    q = (
        select(WorkOrder)
        .options(joinedload(WorkOrder.process_results))
        .where(*filters)
        .order_by(WorkOrder.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    )
    items_result = await db.execute(q)
    items = [
        WorkOrderRead.model_validate(row)
        for row in items_result.scalars().unique().all()
    ]

    return PaginatedResponse.build(items=items, total=total, page=page, limit=limit)


@router.post(
    "/",
    response_model=WorkOrderRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_wo_write],
)
async def create_work_order(
    body: WorkOrderCreate,
    db: DBSession = None,
    current_user: CurrentUser = None,
):
    """작업지시 생성"""
    wo_number = await WorkOrderService(db).generate_wo_number()
    wo = WorkOrder(
        **body.model_dump(),
        wo_number=wo_number,
        created_by=current_user.id,
    )
    db.add(wo)
    await db.flush()

    result = await db.execute(
        select(WorkOrder)
        .options(joinedload(WorkOrder.process_results))
        .where(WorkOrder.id == wo.id)
    )
    return WorkOrderRead.model_validate(result.scalar_one())


@router.get("/{wo_id}", response_model=WorkOrderRead)
async def get_work_order(wo_id: uuid.UUID, db: DBSession = None):
    """작업지시 단건 조회 (공정 실적 포함)"""
    wo = await _get_wo_or_404(wo_id, db)
    return WorkOrderRead.model_validate(wo)


@router.patch(
    "/{wo_id}",
    response_model=WorkOrderRead,
    dependencies=[_require_wo_write],
)
async def update_work_order(
    wo_id: uuid.UUID,
    body: WorkOrderUpdate,
    db: DBSession = None,
):
    """작업지시 수정"""
    result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == wo_id)
    )
    wo = result.scalar_one_or_none()
    if not wo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="작업지시를 찾을 수 없습니다"
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(wo, field, value)

    await db.flush()
    result = await db.execute(
        select(WorkOrder)
        .options(joinedload(WorkOrder.process_results))
        .where(WorkOrder.id == wo_id)
    )
    return WorkOrderRead.model_validate(result.scalar_one())


@router.patch(
    "/{wo_id}/status",
    response_model=WorkOrderRead,
    dependencies=[_require_wo_write],
)
async def update_work_order_status(
    wo_id: uuid.UUID,
    body: WorkOrderStatusUpdate,
    db: DBSession = None,
):
    """작업지시 상태 전환 (상태 머신 검증 포함)"""
    result = await db.execute(
        select(WorkOrder).where(WorkOrder.id == wo_id)
    )
    wo = result.scalar_one_or_none()
    if not wo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="작업지시를 찾을 수 없습니다"
        )

    return await WorkOrderService(db).apply_status_transition(
        wo, body.status, body.notes
    )


@router.post(
    "/{wo_id}/results",
    response_model=ProcessResultRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[_require_result_write],
)
async def add_process_result(
    wo_id: uuid.UUID,
    body: ProcessResultCreate,
    db: DBSession = None,
):
    """공정 실적 등록 (불변 레코드)"""
    result = await db.execute(select(WorkOrder).where(WorkOrder.id == wo_id))
    wo = result.scalar_one_or_none()
    if not wo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="작업지시를 찾을 수 없습니다"
        )

    pr = ProcessResult(
        **body.model_dump(),
        work_order_id=wo_id,
        lot_id=wo.lot_id,
    )
    db.add(pr)
    await db.flush()
    await db.refresh(pr)
    return ProcessResultRead.model_validate(pr)


@router.get("/{wo_id}/results", response_model=list[ProcessResultRead])
async def list_process_results(wo_id: uuid.UUID, db: DBSession = None):
    """작업지시의 공정 실적 목록"""
    wo_result = await db.execute(select(WorkOrder.id).where(WorkOrder.id == wo_id))
    if not wo_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="작업지시를 찾을 수 없습니다"
        )

    result = await db.execute(
        select(ProcessResult)
        .where(ProcessResult.work_order_id == wo_id)
        .order_by(ProcessResult.created_at)
    )
    return [ProcessResultRead.model_validate(row) for row in result.scalars().all()]
