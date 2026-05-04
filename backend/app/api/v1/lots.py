import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import DBSession, CurrentUser, require_any_role, require_production_manager
from app.core.exceptions import (
    LotDeleteForbiddenException,
    LotNotFoundException,
    LotStatusTransitionException,
)
from app.models.lot import Lot, LotHistory
from app.schemas.common import PaginatedResponse
from app.schemas.lot import (
    LotCreate,
    LotHistoryItem,
    LotHistoryResponse,
    LotRead,
    LotStatusUpdate,
    LotTraceabilityReport,
    LotUpdate,
    TraceabilityNode,
)

router = APIRouter(prefix="/lots", tags=["LOT 관리"])


# ------------------------------------------------------------------------------
# POST / — LOT 생성
# ------------------------------------------------------------------------------

@router.post(
    "/",
    response_model=LotRead,
    status_code=status.HTTP_201_CREATED,
    summary="LOT 생성",
    description="신규 LOT을 생성합니다. lot_id는 L{YYYYMMDD}-{SEQ} 형식으로 자동 부여됩니다.",
    dependencies=[require_production_manager],
)
async def create_lot(body: LotCreate, db: DBSession, current_user: CurrentUser):
    lot_id = await Lot.generate_lot_id(db)

    lot = Lot(
        lot_id=lot_id,
        lot_status="created",
        raw_material_id=body.raw_material_id,
        raw_material_name=body.raw_material_name,
        quantity=body.quantity,
        unit=body.unit,
        customer_name=body.customer_name,
        product_code=body.product_code,
        product_name=body.product_name,
        order_number=body.order_number,
        planned_start_date=body.planned_start_date,
        planned_end_date=body.planned_end_date,
        notes=body.notes,
        created_by=current_user.id,
    )
    db.add(lot)
    await db.flush()

    # 생성 이력 기록
    history = LotHistory(
        lot_id_fk=lot.id,
        lot_display_id=lot_id,
        step="LOT 생성",
        from_status=None,
        to_status="created",
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        detail=f"LOT {lot_id} 생성됨",
    )
    db.add(history)
    await db.flush()

    return lot


# ------------------------------------------------------------------------------
# GET / — LOT 목록 (페이지네이션 + 필터)
# ------------------------------------------------------------------------------

@router.get(
    "/",
    response_model=PaginatedResponse[LotRead],
    summary="LOT 목록 조회",
    description=(
        "LOT 목록을 페이지네이션과 필터 조건으로 조회합니다.\n\n"
        "응답 봉투: `{ data: [...], pagination: { total, page, limit, hasMore }, meta: { timestamp, requestId } }`"
    ),
    dependencies=[require_any_role],
)
async def list_lots(
    request: Request,
    db: DBSession,
    page: int = Query(default=1, ge=1, description="페이지 번호"),
    limit: int = Query(default=20, ge=1, le=100, alias="page_size", description="페이지 크기"),
    status_filter: Optional[str] = Query(default=None, alias="status", description="상태 필터"),
    customer_name: Optional[str] = Query(default=None, description="고객사명 검색"),
    product_code: Optional[str] = Query(default=None, description="제품 코드 검색"),
    order_number: Optional[str] = Query(default=None, description="수주번호 검색"),
    lot_id_search: Optional[str] = Query(default=None, alias="lot_id", description="LOT ID 검색"),
):
    query = select(Lot)

    # 필터 적용
    if status_filter:
        query = query.where(Lot.lot_status == status_filter)
    if customer_name:
        query = query.where(Lot.customer_name.ilike(f"%{customer_name}%"))
    if product_code:
        query = query.where(Lot.product_code.ilike(f"%{product_code}%"))
    if order_number:
        query = query.where(Lot.order_number.ilike(f"%{order_number}%"))
    if lot_id_search:
        query = query.where(Lot.lot_id.ilike(f"%{lot_id_search}%"))

    # 전체 카운트
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    # 페이지네이션
    offset = (page - 1) * limit
    query = query.order_by(Lot.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    lots = result.scalars().all()

    trace_id = getattr(request.state, "trace_id", None)
    return PaginatedResponse[LotRead].build(
        items=[LotRead.model_validate(lot) for lot in lots],
        total=total,
        page=page,
        limit=limit,
        request_id=trace_id,
    )


# ------------------------------------------------------------------------------
# GET /{lot_id} — LOT 상세
# ------------------------------------------------------------------------------

@router.get(
    "/{lot_id}",
    response_model=LotRead,
    summary="LOT 상세 조회",
    dependencies=[require_any_role],
)
async def get_lot(lot_id: str, db: DBSession):
    result = await db.execute(select(Lot).where(Lot.lot_id == lot_id))
    lot = result.scalar_one_or_none()
    if lot is None:
        raise LotNotFoundException(f"LOT ID '{lot_id}'를 찾을 수 없습니다")
    return lot


# ------------------------------------------------------------------------------
# PATCH /{lot_id}/status — 상태 변경
# ------------------------------------------------------------------------------

@router.patch(
    "/{lot_id}/status",
    response_model=LotRead,
    summary="LOT 상태 변경",
    description="LOT의 상태를 변경합니다. 허용된 전환 경로만 가능합니다.",
)
async def update_lot_status(
    lot_id: str,
    body: LotStatusUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    result = await db.execute(select(Lot).where(Lot.lot_id == lot_id))
    lot = result.scalar_one_or_none()
    if lot is None:
        raise LotNotFoundException(f"LOT ID '{lot_id}'를 찾을 수 없습니다")

    if not lot.can_transition_to(body.status):
        raise LotStatusTransitionException(
            f"'{lot.lot_status}' 상태에서 '{body.status}'로 전환할 수 없습니다"
        )

    prev_status = lot.lot_status
    lot.lot_status = body.status

    # 실제 시작/종료일 자동 설정
    today = datetime.now(timezone.utc).date()
    if body.status == "in_process" and lot.actual_start_date is None:
        lot.actual_start_date = today
    if body.status in {"completed", "shipped"} and lot.actual_end_date is None:
        lot.actual_end_date = today

    await db.flush()

    # 이력 기록
    history = LotHistory(
        lot_id_fk=lot.id,
        lot_display_id=lot_id,
        step=f"상태 변경: {prev_status} → {body.status}",
        from_status=prev_status,
        to_status=body.status,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        detail=body.detail,
        reason=body.reason,
    )
    db.add(history)

    return lot


# ------------------------------------------------------------------------------
# PATCH /{lot_id} — LOT 정보 수정
# ------------------------------------------------------------------------------

@router.patch(
    "/{lot_id}",
    response_model=LotRead,
    summary="LOT 정보 수정",
    dependencies=[require_production_manager],
)
async def update_lot(
    lot_id: str,
    body: LotUpdate,
    db: DBSession,
    current_user: CurrentUser,
):
    result = await db.execute(select(Lot).where(Lot.lot_id == lot_id))
    lot = result.scalar_one_or_none()
    if lot is None:
        raise LotNotFoundException(f"LOT ID '{lot_id}'를 찾을 수 없습니다")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lot, field, value)

    # 수정 이력
    changed_fields = list(update_data.keys())
    history = LotHistory(
        lot_id_fk=lot.id,
        lot_display_id=lot_id,
        step="LOT 정보 수정",
        from_status=lot.lot_status,
        to_status=lot.lot_status,
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        detail=f"수정 필드: {', '.join(changed_fields)}",
    )
    db.add(history)

    return lot


# ------------------------------------------------------------------------------
# POST /{lot_id}/cancel — LOT 취소 (삭제 대신 상태 전환)
# ------------------------------------------------------------------------------
# 설계 정책: LOT은 물리적으로 삭제되지 않습니다 (no_delete_lots DB rule).
# 취소가 필요할 경우 status를 'cancelled'로 전환합니다.
# 최종 상태(shipped, rejected, cancelled)에서는 취소할 수 없습니다.

@router.post(
    "/{lot_id}/cancel",
    response_model=LotRead,
    status_code=status.HTTP_200_OK,
    summary="LOT 취소",
    description=(
        "LOT의 상태를 `cancelled`로 전환합니다.\n\n"
        "- LOT은 물리적으로 삭제되지 않습니다 (DB no_delete_lots 정책).\n"
        "- 이미 최종 상태(`shipped`, `rejected`, `cancelled`)인 LOT은 취소할 수 없습니다."
    ),
    dependencies=[require_production_manager],
)
async def cancel_lot(lot_id: str, db: DBSession, current_user: CurrentUser):
    from app.models.lot import LOT_FINAL_STATUSES  # noqa: PLC0415

    result = await db.execute(select(Lot).where(Lot.lot_id == lot_id))
    lot = result.scalar_one_or_none()
    if lot is None:
        raise LotNotFoundException(f"LOT ID '{lot_id}'를 찾을 수 없습니다")

    if lot.lot_status in LOT_FINAL_STATUSES:
        raise LotDeleteForbiddenException(
            f"'{lot.lot_status}' 상태의 LOT은 취소할 수 없습니다"
        )

    prev_status = lot.lot_status
    lot.lot_status = "cancelled"
    await db.flush()

    # 취소 이력 기록
    history = LotHistory(
        lot_id_fk=lot.id,
        lot_display_id=lot_id,
        step="LOT 취소",
        from_status=prev_status,
        to_status="cancelled",
        actor_id=current_user.id,
        actor_name=current_user.full_name,
        detail=f"LOT {lot_id} 취소됨 (이전 상태: {prev_status})",
    )
    db.add(history)

    return lot


# ------------------------------------------------------------------------------
# GET /{lot_id}/history — 이력 타임라인
# ------------------------------------------------------------------------------

@router.get(
    "/{lot_id}/history",
    response_model=LotHistoryResponse,
    summary="LOT 이력 타임라인",
    description="LOT의 전체 상태 변경 이력을 시간 순으로 반환합니다.",
    dependencies=[require_any_role],
)
async def get_lot_history(lot_id: str, db: DBSession):
    result = await db.execute(select(Lot).where(Lot.lot_id == lot_id))
    lot = result.scalar_one_or_none()
    if lot is None:
        raise LotNotFoundException(f"LOT ID '{lot_id}'를 찾을 수 없습니다")

    hist_result = await db.execute(
        select(LotHistory)
        .where(LotHistory.lot_display_id == lot_id)
        .order_by(LotHistory.created_at.asc())
    )
    histories = hist_result.scalars().all()

    timeline = [
        LotHistoryItem(
            id=h.id,
            step=h.step,
            from_status=h.from_status,
            to_status=h.to_status,
            actor_id=h.actor_id,
            actor_name=h.actor_name,
            detail=h.detail,
            reason=h.reason,
            timestamp=h.created_at,
        )
        for h in histories
    ]

    return LotHistoryResponse(
        lot_id=lot_id,
        lot_status=lot.lot_status,
        timeline=timeline,
    )


# ------------------------------------------------------------------------------
# GET /{lot_id}/traceability — 완전 역추적
# ------------------------------------------------------------------------------

@router.get(
    "/{lot_id}/traceability",
    response_model=LotTraceabilityReport,
    summary="LOT 역추적 보고서",
    description="원자재부터 출하까지 LOT의 전체 이력 트리를 생성합니다.",
    dependencies=[require_any_role],
)
async def get_lot_traceability(lot_id: str, db: DBSession):
    result = await db.execute(select(Lot).where(Lot.lot_id == lot_id))
    lot = result.scalar_one_or_none()
    if lot is None:
        raise LotNotFoundException(f"LOT ID '{lot_id}'를 찾을 수 없습니다")

    hist_result = await db.execute(
        select(LotHistory)
        .where(LotHistory.lot_display_id == lot_id)
        .order_by(LotHistory.created_at.asc())
    )
    histories = hist_result.scalars().all()

    # 이력 → 트리 구조 변환 (선형 시퀀스를 트리로 표현)
    history_tree: list[TraceabilityNode] = []
    prev_node: Optional[TraceabilityNode] = None

    for h in histories:
        node = TraceabilityNode(
            step=h.step,
            status=h.to_status or h.from_status or "unknown",
            actor=h.actor_name,
            timestamp=h.created_at,
            detail=h.detail or h.reason,
            children=[],
        )
        if prev_node is None:
            history_tree.append(node)
        else:
            prev_node.children.append(node)
        prev_node = node

    return LotTraceabilityReport(
        lot_id=lot_id,
        lot_status=lot.lot_status,
        raw_material_id=lot.raw_material_id,
        raw_material_name=lot.raw_material_name,
        quantity=lot.quantity,
        unit=lot.unit,
        customer_name=lot.customer_name,
        product_name=lot.product_name,
        order_number=lot.order_number,
        planned_start_date=lot.planned_start_date,
        planned_end_date=lot.planned_end_date,
        actual_start_date=lot.actual_start_date,
        actual_end_date=lot.actual_end_date,
        created_at=lot.created_at,
        history_tree=history_tree,
        total_history_count=len(histories),
        generated_at=datetime.utcnow(),
    )
