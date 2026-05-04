"""품질 검사 Service Layer"""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lot import Lot
from app.models.quality import DefectDetail, QualityInspection
from app.schemas.quality import (
    DefectStatsItem,
    DefectStatsResponse,
    QualityInspectionCreate,
)


class QualityService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_inspection(
        self,
        data: QualityInspectionCreate,
        inspector_id: uuid.UUID,
    ) -> QualityInspection:
        inspection_date = data.inspection_date or datetime.now(timezone.utc)

        inspection = QualityInspection(
            lot_id=data.lot_id,
            inspector_id=inspector_id,
            inspection_type=data.inspection_type,
            result=data.result,
            defect_rate=data.defect_rate,
            inspection_date=inspection_date,
            notes=data.notes,
        )
        self.db.add(inspection)
        await self.db.flush()

        for d in data.defects:
            self.db.add(DefectDetail(
                inspection_id=inspection.id,
                defect_code=d.defect_code,
                defect_type=d.defect_type,
                qty=d.qty,
                description=d.description,
                root_cause=d.root_cause,
            ))

        # 불량 판정 시 LOT 상태 자동 전환 (in_process → rejected)
        if data.result == "fail":
            lot_result = await self.db.execute(
                select(Lot).where(Lot.id == data.lot_id)
            )
            lot = lot_result.scalar_one_or_none()
            if lot and lot.lot_status == "in_process":
                lot.lot_status = "rejected"

        await self.db.flush()
        await self.db.refresh(inspection)

        result = await self.db.execute(
            select(QualityInspection)
            .options(joinedload(QualityInspection.defects))
            .where(QualityInspection.id == inspection.id)
        )
        return result.scalar_one()

    async def get_lot_inspections(
        self, lot_id: uuid.UUID
    ) -> list[QualityInspection]:
        result = await self.db.execute(
            select(QualityInspection)
            .options(joinedload(QualityInspection.defects))
            .where(QualityInspection.lot_id == lot_id)
            .order_by(QualityInspection.inspection_date)
        )
        return list(result.scalars().unique().all())

    @staticmethod
    def _lot_alias():
        from app.models.lot import Lot
        from sqlalchemy.orm import aliased
        return aliased(Lot)

    async def get_defect_stats(
        self,
        group_by: str = "supplier",
        period_days: int = 30,
    ) -> DefectStatsResponse:
        since = datetime.now(timezone.utc) - timedelta(days=period_days)

        if group_by == "lot":
            rows = (await self.db.execute(
                select(
                    QualityInspection.lot_id.label("group_key"),
                    func.count(QualityInspection.id).label("total"),
                    func.sum(
                        (QualityInspection.result == "fail").cast("integer")
                    ).label("fails"),
                    func.avg(QualityInspection.defect_rate).label("avg_rate"),
                )
                .where(QualityInspection.inspection_date >= since)
                .group_by(QualityInspection.lot_id)
                .order_by(func.avg(QualityInspection.defect_rate).desc())
                .limit(50)
            )).all()

            items = [
                DefectStatsItem(
                    group_key=str(r.group_key),
                    group_label=str(r.group_key),
                    total_inspections=int(r.total),
                    fail_count=int(r.fails or 0),
                    avg_defect_rate=round(float(r.avg_rate or 0), 2),
                )
                for r in rows
            ]

        elif group_by == "supplier":
            # raw_material_receipts JOIN: QualityInspection → Lot → RawMaterialReceipt → Supplier
            from app.models.inbound import RawMaterialReceipt
            from app.models.supplier import Supplier as SupplierModel
            rows = (await self.db.execute(
                select(
                    SupplierModel.id.label("group_key"),
                    SupplierModel.name.label("group_label"),
                    func.count(QualityInspection.id).label("total"),
                    func.sum(
                        (QualityInspection.result == "fail").cast("integer")
                    ).label("fails"),
                    func.avg(QualityInspection.defect_rate).label("avg_rate"),
                )
                .join(self._lot_alias(), QualityInspection.lot_id == self._lot_alias().id)
                .join(RawMaterialReceipt, RawMaterialReceipt.lot_id == self._lot_alias().id)
                .join(SupplierModel, SupplierModel.id == RawMaterialReceipt.supplier_id)
                .where(QualityInspection.inspection_date >= since)
                .group_by(SupplierModel.id, SupplierModel.name)
                .order_by(func.avg(QualityInspection.defect_rate).desc())
                .limit(20)
            )).all()

            items = [
                DefectStatsItem(
                    group_key=str(r.group_key),
                    group_label=r.group_label,
                    total_inspections=int(r.total),
                    fail_count=int(r.fails or 0),
                    avg_defect_rate=round(float(r.avg_rate or 0), 2),
                )
                for r in rows
            ]

        else:  # process_type — inspection_type 기반 집계
            rows = (await self.db.execute(
                select(
                    QualityInspection.inspection_type.label("group_key"),
                    func.count(QualityInspection.id).label("total"),
                    func.sum(
                        (QualityInspection.result == "fail").cast("integer")
                    ).label("fails"),
                    func.avg(QualityInspection.defect_rate).label("avg_rate"),
                )
                .where(QualityInspection.inspection_date >= since)
                .group_by(QualityInspection.inspection_type)
                .order_by(func.avg(QualityInspection.defect_rate).desc())
            )).all()

            TYPE_LABELS = {
                "incoming": "입고 검사", "in_process": "공정 검사",
                "final": "최종 검사", "shipment": "출하 검사",
            }
            items = [
                DefectStatsItem(
                    group_key=r.group_key,
                    group_label=TYPE_LABELS.get(r.group_key, r.group_key),
                    total_inspections=int(r.total),
                    fail_count=int(r.fails or 0),
                    avg_defect_rate=round(float(r.avg_rate or 0), 2),
                )
                for r in rows
            ]

        return DefectStatsResponse(
            group_by=group_by,
            period_days=period_days,
            items=items,
        )
