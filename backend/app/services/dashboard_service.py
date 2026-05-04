"""대시보드 집계 Service Layer"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import cast, Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.equipment import Equipment
from app.models.lot import Lot
from app.models.work_order import ProcessResult, WorkOrder
from app.schemas.dashboard import (
    DashboardSummary,
    DayOverDayDelta,
    LotStatusItem,
    ProductionTrendItem,
)


def _day_range(target: date) -> tuple[datetime, datetime]:
    start = datetime.combine(target, datetime.min.time()).replace(tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


class DashboardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_today_production(self) -> float:
        s, e = _day_range(date.today())
        row = (await self.db.execute(
            select(func.coalesce(func.sum(ProcessResult.output_qty), 0))
            .where(ProcessResult.created_at >= s, ProcessResult.created_at < e)
        )).scalar_one()
        return float(row)

    async def get_defect_rate(self, target: date | None = None) -> float:
        """quality_inspections 기반 실집계. 데이터 없을 시 process_results 폴백."""
        from app.models.quality import QualityInspection
        d = target or date.today()
        s, e = _day_range(d)

        row = (await self.db.execute(
            select(func.coalesce(func.avg(QualityInspection.defect_rate), 0))
            .where(
                QualityInspection.inspection_date >= s,
                QualityInspection.inspection_date < e,
            )
        )).scalar_one()
        qi_rate = float(row)

        if qi_rate > 0:
            return round(qi_rate, 2)

        # 폴백: process_results 기반 (품질검사 데이터 없는 날)
        pr = (await self.db.execute(
            select(
                func.coalesce(func.sum(ProcessResult.output_qty), 0).label("output"),
                func.coalesce(func.sum(ProcessResult.defect_qty), 0).label("defect"),
            ).where(ProcessResult.created_at >= s, ProcessResult.created_at < e)
        )).one()
        out, defect = float(pr.output), float(pr.defect)
        return round((defect / out * 100) if out > 0 else 0.0, 2)

    async def get_equipment_utilization(self) -> float:
        eq_result = (await self.db.execute(
            select(Equipment.status, func.count(Equipment.id).label("cnt"))
            .where(Equipment.is_active == True)  # noqa: E712
            .group_by(Equipment.status)
        )).all()
        counts = {row.status: row.cnt for row in eq_result}
        total = sum(counts.values())
        running = counts.get("running", 0)
        return round((running / total * 100) if total > 0 else 0.0, 1)

    async def get_pending_shipments(self) -> int:
        """shipments 테이블 기반 실집계"""
        from app.models.shipment import Shipment
        result = await self.db.execute(
            select(func.count(Shipment.id)).where(Shipment.status == "pending")
        )
        return result.scalar_one()

    async def get_dashboard_summary(self) -> DashboardSummary:
        today = date.today()
        yesterday = today - timedelta(days=1)

        async def _prod_stats(d: date) -> tuple[float, float]:
            s, e = _day_range(d)
            row = (await self.db.execute(
                select(
                    func.coalesce(func.sum(ProcessResult.output_qty), 0).label("output"),
                    func.coalesce(func.sum(ProcessResult.defect_qty), 0).label("defect"),
                ).where(ProcessResult.created_at >= s, ProcessResult.created_at < e)
            )).one()
            return float(row.output), float(row.defect)

        today_out, today_defect = await _prod_stats(today)
        prev_out, prev_defect = await _prod_stats(yesterday)

        today_rate = round((today_defect / today_out * 100) if today_out > 0 else 0.0, 2)
        prev_rate = round((prev_defect / prev_out * 100) if prev_out > 0 else 0.0, 2)

        utilization = await self.get_equipment_utilization()
        pending = await self.get_pending_shipments()

        return DashboardSummary(
            today_production=today_out,
            defect_rate=today_rate,
            equipment_utilization=utilization,
            pending_shipments=pending,
            compared_to_prev_day=DayOverDayDelta(
                production=round(today_out - prev_out, 1),
                defect_rate=round(today_rate - prev_rate, 2),
                equipment_utilization=0.0,
                pending_shipments=0.0,
            ),
        )

    async def get_production_trend(self, days: int = 7) -> list[ProductionTrendItem]:
        since = datetime.combine(
            date.today() - timedelta(days=days - 1), datetime.min.time()
        ).replace(tzinfo=timezone.utc)

        actual_rows = (await self.db.execute(
            select(
                cast(ProcessResult.created_at, Date).label("day"),
                func.coalesce(func.sum(ProcessResult.output_qty), 0).label("actual"),
                func.coalesce(func.sum(ProcessResult.defect_qty), 0).label("defects"),
            )
            .where(ProcessResult.created_at >= since)
            .group_by(cast(ProcessResult.created_at, Date))
            .order_by(cast(ProcessResult.created_at, Date))
        )).all()

        planned_rows = (await self.db.execute(
            select(
                cast(WorkOrder.planned_start, Date).label("day"),
                func.coalesce(func.sum(WorkOrder.input_qty), 0).label("planned"),
            )
            .where(WorkOrder.planned_start >= since)
            .group_by(cast(WorkOrder.planned_start, Date))
        )).all()
        planned_map: dict[date, float] = {r.day: float(r.planned) for r in planned_rows}

        return [
            ProductionTrendItem(
                date=row.day.strftime("%m/%d"),
                planned=planned_map.get(row.day, 0.0),
                actual=float(row.actual),
                defects=float(row.defects),
            )
            for row in actual_rows
        ]

    async def get_lot_status_summary(self, limit: int = 5) -> list[LotStatusItem]:
        lots = (await self.db.execute(
            select(Lot).order_by(Lot.created_at.desc()).limit(limit)
        )).scalars().all()

        STATUS_LABELS = {
            "created": "생성됨", "in_receipt": "입고 처리 중", "received": "입고 완료",
            "in_process": "공정 중", "in_inspection": "품질 검사",
            "completed": "완료", "shipped": "출하됨", "delivered": "인수 완료",
            "on_hold": "보류", "rejected": "불합격", "cancelled": "취소",
        }

        return [
            LotStatusItem(
                lot_id=lot.lot_id,
                item=lot.product_name or lot.raw_material_name or "-",
                status=STATUS_LABELS.get(lot.lot_status, lot.lot_status),
                process="-",
                operator="-",
            )
            for lot in lots
        ]
