"""출하/물류 Service Layer"""
import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lot import Lot
from app.models.shipment import Shipment, ShipmentLot
from app.schemas.shipment import ShipmentCreate, ShipmentLotItem, ShipmentRead


class ShipmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_shipment_number(self) -> str:
        """SH-{YYYYMMDD}-{4자리 SEQ}"""
        today_str = date.today().strftime("%Y%m%d")
        prefix = f"SH-{today_str}-"
        result = await self.db.execute(
            select(func.count(Shipment.id)).where(
                Shipment.shipment_number.like(f"{prefix}%")
            )
        )
        count = result.scalar_one() or 0
        return f"{prefix}{count + 1:04d}"

    async def create_shipment(
        self,
        data: ShipmentCreate,
        created_by: uuid.UUID,
    ) -> Shipment:
        shipment_number = await self.generate_shipment_number()
        shipment = Shipment(
            shipment_number=shipment_number,
            customer_id=data.customer_id,
            planned_date=data.planned_date,
            notes=data.notes,
            created_by=created_by,
        )
        self.db.add(shipment)
        await self.db.flush()

        for lot_item in data.lots:
            await self._add_lot_to_shipment(shipment.id, lot_item)

        await self.db.flush()
        return await self._reload(shipment.id)

    async def _add_lot_to_shipment(
        self, shipment_id: uuid.UUID, item: ShipmentLotItem
    ) -> ShipmentLot:
        sl = ShipmentLot(
            shipment_id=shipment_id,
            lot_id=item.lot_id,
            qty=item.qty,
            unit_price=item.unit_price,
        )
        self.db.add(sl)

        # LOT 상태 completed → shipped 자동 전환
        lot_result = await self.db.execute(
            select(Lot).where(Lot.id == item.lot_id)
        )
        lot = lot_result.scalar_one_or_none()
        if lot and lot.lot_status == "completed":
            lot.lot_status = "shipped"

        return sl

    async def add_lots(
        self,
        shipment_id: uuid.UUID,
        lots: list[ShipmentLotItem],
    ) -> Shipment:
        shipment_result = await self.db.execute(
            select(Shipment).where(Shipment.id == shipment_id)
        )
        shipment = shipment_result.scalar_one_or_none()
        if not shipment:
            raise HTTPException(status_code=404, detail="출하를 찾을 수 없습니다")
        if shipment.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="pending 상태의 출하에만 LOT을 추가할 수 있습니다",
            )

        for item in lots:
            await self._add_lot_to_shipment(shipment_id, item)

        await self.db.flush()
        return await self._reload(shipment_id)

    async def update_status(
        self,
        shipment: Shipment,
        new_status: str,
        notes: str | None = None,
    ) -> Shipment:
        ALLOWED: dict[str, list[str]] = {
            "pending": ["shipped", "cancelled"],
            "shipped": ["delivered", "cancelled"],
            "delivered": [],
            "cancelled": [],
        }
        if new_status not in ALLOWED.get(shipment.status, []):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"'{shipment.status}' → '{new_status}' 전환이 허용되지 않습니다",
            )

        now_utc = datetime.now(timezone.utc)
        if new_status == "shipped":
            shipment.shipped_date = now_utc
        if new_status == "delivered":
            shipment.delivered_date = now_utc
            # 포함 LOT 상태 shipped → delivered
            lots_result = await self.db.execute(
                select(Lot)
                .join(ShipmentLot, ShipmentLot.lot_id == Lot.id)
                .where(ShipmentLot.shipment_id == shipment.id)
            )
            for lot in lots_result.scalars().all():
                if lot.lot_status == "shipped":
                    lot.lot_status = "delivered"

        shipment.status = new_status
        if notes is not None:
            shipment.notes = notes

        await self.db.flush()
        return await self._reload(shipment.id)

    async def _reload(self, shipment_id: uuid.UUID) -> Shipment:
        result = await self.db.execute(
            select(Shipment)
            .options(joinedload(Shipment.lots), joinedload(Shipment.customer))
            .where(Shipment.id == shipment_id)
        )
        return result.scalar_one()
