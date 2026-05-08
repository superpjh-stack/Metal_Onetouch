"""KPI 집계 Service Layer"""
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kpi import KpiTarget
from app.models.order import Order
from app.models.quality import QualityInspection
from app.models.shipment import Shipment
from app.models.work_order import ProcessResult, WorkOrder
from app.schemas.kpi import (
    KpiDeliveryData,
    KpiProductionData,
    KpiQualityData,
    KpiShipmentData,
    KpiSummary,
    KpiTargetUpsert,
    KpiTrendItem,
)


def _month_range() -> tuple[date, date]:
    today = date.today()
    start = today.replace(day=1)
    return start, today


def _d(col):
    """SQLite/PG 공통 date 추출"""
    return func.date(col)


def _fmt(day_val) -> str:
    """'YYYY-MM-DD' 또는 date → 'MM/DD'"""
    s = str(day_val)[:10]
    return s[5:].replace("-", "/")


class KpiService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_summary(self) -> KpiSummary:
        targets = await self._load_targets()
        production_rate = await self._calc_production_rate()
        defect_rate     = await self._calc_defect_rate()
        delivery_rate   = await self._calc_delivery_rate()
        shipment_count  = await self._calc_shipment_count()
        return KpiSummary(
            production_rate=production_rate,
            defect_rate=defect_rate,
            delivery_rate=delivery_rate,
            shipment_count=shipment_count,
            targets=targets,
        )

    async def get_production(self, days: int = 30) -> KpiProductionData:
        targets = await self._load_targets()
        rate = await self._calc_production_rate()
        trend = await self._production_trend(days)
        return KpiProductionData(
            production_rate=rate,
            target=targets.get("production_rate"),
            trend=trend,
        )

    async def get_quality(self, days: int = 30) -> KpiQualityData:
        targets = await self._load_targets()
        rate = await self._calc_defect_rate()
        trend = await self._quality_trend(days)
        return KpiQualityData(
            defect_rate=rate,
            target=targets.get("defect_rate"),
            trend=trend,
        )

    async def get_delivery(self) -> KpiDeliveryData:
        targets = await self._load_targets()
        rate, total, on_time = await self._calc_delivery_detail()
        return KpiDeliveryData(
            delivery_rate=rate,
            target=targets.get("delivery_rate"),
            total_orders=total,
            on_time_orders=on_time,
        )

    async def get_shipment(self) -> KpiShipmentData:
        month_start, today = _month_range()
        rows = (await self.db.execute(
            select(Shipment.status, func.count(Shipment.id).label("cnt"))
            .where(_d(Shipment.created_at) >= str(month_start))
            .group_by(Shipment.status)
        )).all()
        counts = {r.status: r.cnt for r in rows}
        shipped   = counts.get("shipped", 0)
        delivered = counts.get("delivered", 0)
        pending   = counts.get("pending", 0)
        return KpiShipmentData(
            shipment_count=shipped + delivered,
            pending_count=pending,
            delivered_count=delivered,
        )

    async def upsert_targets(
        self,
        updates: list[KpiTargetUpsert],
        updated_by: uuid.UUID,
    ) -> list[KpiTarget]:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        for u in updates:
            stmt = (
                sqlite_insert(KpiTarget)
                .values(
                    metric_key=u.metric_key,
                    target_value=u.target_value,
                    unit=u.unit,
                    period=u.period,
                    updated_by=str(updated_by),
                )
                .on_conflict_do_update(
                    index_elements=["metric_key"],
                    set_={
                        "target_value": u.target_value,
                        "unit": u.unit,
                        "period": u.period,
                        "updated_by": str(updated_by),
                        "updated_at": func.now(),
                    },
                )
            )
            await self.db.execute(stmt)
        await self.db.flush()
        rows = (await self.db.execute(select(KpiTarget))).scalars().all()
        return list(rows)

    # ── private helpers ──────────────────────────────────────────────────────

    async def _load_targets(self) -> dict[str, float]:
        rows = (await self.db.execute(select(KpiTarget))).scalars().all()
        return {r.metric_key: float(r.target_value) for r in rows}

    async def _calc_production_rate(self) -> float:
        """당월 WorkOrder 계획 대비 ProcessResult 실적 달성률"""
        month_start, _ = _month_range()
        ms = str(month_start)
        planned_row = (await self.db.execute(
            select(func.coalesce(func.sum(WorkOrder.input_qty), 0))
            .where(_d(WorkOrder.planned_start) >= ms)
        )).scalar_one()
        actual_row = (await self.db.execute(
            select(func.coalesce(func.sum(ProcessResult.output_qty), 0))
            .where(_d(ProcessResult.created_at) >= ms)
        )).scalar_one()
        planned = float(planned_row)
        actual  = float(actual_row)
        return round((actual / planned * 100) if planned > 0 else 0.0, 1)

    async def _calc_defect_rate(self) -> float:
        """당월 품질검사 평균 불량률"""
        month_start, _ = _month_range()
        row = (await self.db.execute(
            select(func.coalesce(func.avg(QualityInspection.defect_rate), 0))
            .where(_d(QualityInspection.inspection_date) >= str(month_start))
        )).scalar_one()
        return round(float(row), 2)

    async def _calc_delivery_rate(self) -> float:
        rate, _, _ = await self._calc_delivery_detail()
        return rate

    async def _calc_delivery_detail(self) -> tuple[float, int, int]:
        """납기 준수율: due_date 이내 completed Orders / 전체 completed (당월)"""
        month_start, today = _month_range()
        rows = (await self.db.execute(
            select(Order.due_date, Order.updated_at)
            .where(
                Order.status == "completed",
                _d(Order.updated_at) >= str(month_start),
            )
        )).all()
        total = len(rows)
        on_time = 0
        for r in rows:
            if r.due_date is None:
                on_time += 1
                continue
            upd = r.updated_at
            if hasattr(upd, "date"):
                upd_date = upd.date()
            else:
                upd_date = date.fromisoformat(str(upd)[:10])
            due = r.due_date if isinstance(r.due_date, date) else date.fromisoformat(str(r.due_date)[:10])
            if upd_date <= due:
                on_time += 1
        rate = round((on_time / total * 100) if total > 0 else 0.0, 1)
        return rate, total, on_time

    async def _calc_shipment_count(self) -> int:
        month_start, _ = _month_range()
        row = (await self.db.execute(
            select(func.count(Shipment.id))
            .where(
                Shipment.status.in_(["shipped", "delivered"]),
                _d(Shipment.created_at) >= str(month_start),
            )
        )).scalar_one()
        return int(row)

    async def _production_trend(self, days: int) -> list[KpiTrendItem]:
        since = str(date.today() - timedelta(days=days - 1))
        rows = (await self.db.execute(
            select(
                _d(ProcessResult.created_at).label("day"),
                func.coalesce(func.sum(ProcessResult.output_qty), 0).label("qty"),
            )
            .where(_d(ProcessResult.created_at) >= since)
            .group_by(_d(ProcessResult.created_at))
            .order_by(_d(ProcessResult.created_at))
        )).all()
        return [KpiTrendItem(date=_fmt(r.day), value=float(r.qty)) for r in rows]

    async def _quality_trend(self, days: int) -> list[KpiTrendItem]:
        since = str(date.today() - timedelta(days=days - 1))
        rows = (await self.db.execute(
            select(
                _d(QualityInspection.inspection_date).label("day"),
                func.coalesce(func.avg(QualityInspection.defect_rate), 0).label("rate"),
            )
            .where(_d(QualityInspection.inspection_date) >= since)
            .group_by(_d(QualityInspection.inspection_date))
            .order_by(_d(QualityInspection.inspection_date))
        )).all()
        return [KpiTrendItem(date=_fmt(r.day), value=round(float(r.rate), 2)) for r in rows]
