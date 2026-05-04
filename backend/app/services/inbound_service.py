"""원자재 입고 Service Layer"""
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inbound import RawMaterialReceipt
from app.models.lot import Lot
from app.models.supplier import Supplier
from app.schemas.inbound import ReceiptCreate, ReceiptRead, SupplierReceiptStats


class InboundService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_receipt_number(self) -> str:
        """REC-{YYYYMMDD}-{4자리 SEQ}"""
        today_str = date.today().strftime("%Y%m%d")
        prefix = f"REC-{today_str}-"
        result = await self.db.execute(
            select(func.count(RawMaterialReceipt.id)).where(
                RawMaterialReceipt.receipt_number.like(f"{prefix}%")
            )
        )
        count = result.scalar_one() or 0
        return f"{prefix}{count + 1:04d}"

    async def create_receipt(
        self,
        data: ReceiptCreate,
        created_by: uuid.UUID,
    ) -> ReceiptRead:
        """입고 등록 + LOT 자동 생성.

        Lot.lot_status = 'received', raw_material_name = data.material_name
        """
        # 공급처 유효성 검증
        supplier = (await self.db.execute(
            select(Supplier).where(Supplier.id == data.supplier_id)
        )).scalar_one_or_none()
        if not supplier:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supplier not found")

        receipt_number = await self.generate_receipt_number()

        # 1. LOT 자동 생성
        lot_id_str = await Lot.generate_lot_id(self.db)
        lot = Lot(
            lot_id=lot_id_str,
            lot_status="received",
            raw_material_name=data.material_name,
            raw_material_id=data.material_code,
            quantity=float(data.quantity),
            unit=data.unit,
            created_by=created_by,
        )
        self.db.add(lot)
        await self.db.flush()

        # 2. 입고 등록
        receipt = RawMaterialReceipt(
            receipt_number=receipt_number,
            supplier_id=data.supplier_id,
            lot_id=lot.id,
            material_name=data.material_name,
            material_code=data.material_code,
            quantity=data.quantity,
            unit=data.unit,
            unit_price=data.unit_price,
            received_date=data.received_date,
            notes=data.notes,
            created_by=created_by,
        )
        self.db.add(receipt)
        await self.db.flush()
        await self.db.refresh(receipt)

        read = ReceiptRead.model_validate(receipt)
        read = read.model_copy(update={
            "supplier_name": supplier.name,
            "lot_display_id": lot_id_str,
        })
        return read

    async def list_receipts(
        self,
        supplier_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[ReceiptRead], int]:
        q = select(RawMaterialReceipt).options(
            joinedload(RawMaterialReceipt.supplier),
            joinedload(RawMaterialReceipt.lot),
        )
        if supplier_id:
            q = q.where(RawMaterialReceipt.supplier_id == supplier_id)
        if date_from:
            q = q.where(RawMaterialReceipt.received_date >= date_from)
        if date_to:
            q = q.where(RawMaterialReceipt.received_date <= date_to)

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        rows = (await self.db.execute(
            q.order_by(RawMaterialReceipt.received_date.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )).scalars().unique().all()

        items = []
        for r in rows:
            read = ReceiptRead.model_validate(r)
            read = read.model_copy(update={
                "supplier_name": r.supplier.name if r.supplier else None,
                "lot_display_id": r.lot.lot_id if r.lot else None,
            })
            items.append(read)
        return items, total

    async def get_receipt(self, receipt_id: uuid.UUID) -> ReceiptRead:
        row = (await self.db.execute(
            select(RawMaterialReceipt)
            .options(
                joinedload(RawMaterialReceipt.supplier),
                joinedload(RawMaterialReceipt.lot),
            )
            .where(RawMaterialReceipt.id == receipt_id)
        )).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receipt not found")
        read = ReceiptRead.model_validate(row)
        return read.model_copy(update={
            "supplier_name": row.supplier.name if row.supplier else None,
            "lot_display_id": row.lot.lot_id if row.lot else None,
        })

    async def get_supplier_stats(
        self, period_days: int = 30
    ) -> list[SupplierReceiptStats]:
        since = datetime.now(timezone.utc).date()
        from datetime import timedelta
        since = since - timedelta(days=period_days)

        rows = (await self.db.execute(
            select(
                RawMaterialReceipt.supplier_id,
                Supplier.name.label("supplier_name"),
                func.count(RawMaterialReceipt.id).label("total_receipts"),
                func.coalesce(func.sum(RawMaterialReceipt.quantity), 0).label("total_quantity"),
                func.avg(RawMaterialReceipt.unit_price).label("avg_unit_price"),
                func.max(RawMaterialReceipt.received_date).label("last_received_date"),
            )
            .join(Supplier, Supplier.id == RawMaterialReceipt.supplier_id)
            .where(RawMaterialReceipt.received_date >= since)
            .group_by(RawMaterialReceipt.supplier_id, Supplier.name)
            .order_by(func.count(RawMaterialReceipt.id).desc())
        )).all()

        return [
            SupplierReceiptStats(
                supplier_id=r.supplier_id,
                supplier_name=r.supplier_name,
                total_receipts=r.total_receipts,
                total_quantity=float(r.total_quantity),
                avg_unit_price=float(r.avg_unit_price) if r.avg_unit_price else None,
                last_received_date=r.last_received_date,
            )
            for r in rows
        ]
