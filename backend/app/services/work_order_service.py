"""작업지시 Service Layer"""
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.work_order import WO_STATUS_TRANSITIONS, WorkOrder
from app.schemas.work_order import WorkOrderRead


class WorkOrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_wo_number(self) -> str:
        """WO-{YYYYMMDD}-{4자리 SEQ} 형식의 작업지시 번호 생성"""
        today_str = date.today().strftime("%Y%m%d")
        prefix = f"WO-{today_str}-"
        result = await self.db.execute(
            select(func.count(WorkOrder.id)).where(
                WorkOrder.wo_number.like(f"{prefix}%")
            )
        )
        count = result.scalar_one() or 0
        return f"{prefix}{count + 1:04d}"

    async def validate_status_transition(
        self, wo: WorkOrder, new_status: str
    ) -> None:
        if not wo.can_transition_to(new_status):
            allowed = WO_STATUS_TRANSITIONS.get(wo.status, [])
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"'{wo.status}' → '{new_status}' 전환이 허용되지 않습니다. 허용: {allowed}",
            )

    async def apply_status_transition(
        self,
        wo: WorkOrder,
        new_status: str,
        notes: str | None = None,
    ) -> WorkOrder:
        await self.validate_status_transition(wo, new_status)

        now_utc = datetime.now(timezone.utc)
        if new_status == "in_progress" and wo.actual_start is None:
            wo.actual_start = now_utc
        if new_status in ("completed", "cancelled") and wo.actual_end is None:
            wo.actual_end = now_utc

        wo.status = new_status
        if notes is not None:
            wo.notes = notes

        await self.db.flush()

        result = await self.db.execute(
            select(WorkOrder)
            .options(joinedload(WorkOrder.process_results))
            .where(WorkOrder.id == wo.id)
        )
        return WorkOrderRead.model_validate(result.scalar_one())
