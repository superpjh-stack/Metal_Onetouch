"""단가 마스터 서비스"""
import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_master import MaterialPriceMaster, ProcessPriceMaster
from app.schemas.price_master import (
    MaterialPriceRead,
    MaterialPriceUpsert,
    ProcessPriceRead,
    ProcessPriceUpsert,
)


class PriceMasterService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_process_prices(self) -> list[ProcessPriceRead]:
        rows = (await self.db.execute(
            select(ProcessPriceMaster).order_by(
                ProcessPriceMaster.process_type, ProcessPriceMaster.material_grade
            )
        )).scalars().all()
        return [ProcessPriceRead.model_validate(r) for r in rows]

    async def upsert_process_prices(
        self, items: list[ProcessPriceUpsert], updated_by: uuid.UUID
    ) -> list[ProcessPriceRead]:
        for item in items:
            stmt = pg_insert(ProcessPriceMaster).values(
                process_type=item.process_type,
                material_grade=item.material_grade,
                unit_price=item.unit_price,
                price_unit=item.price_unit,
                effective_from=date.today(),
                notes=item.notes,
                updated_by=updated_by,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["process_type"],
                set_={
                    "unit_price": stmt.excluded.unit_price,
                    "price_unit": stmt.excluded.price_unit,
                    "notes": stmt.excluded.notes,
                    "updated_by": stmt.excluded.updated_by,
                    "effective_from": stmt.excluded.effective_from,
                },
            )
            await self.db.execute(stmt)
        await self.db.flush()
        return await self.list_process_prices()

    async def list_material_prices(self) -> list[MaterialPriceRead]:
        rows = (await self.db.execute(
            select(MaterialPriceMaster).order_by(MaterialPriceMaster.material_code)
        )).scalars().all()
        return [MaterialPriceRead.model_validate(r) for r in rows]

    async def upsert_material_prices(
        self, items: list[MaterialPriceUpsert], updated_by: uuid.UUID
    ) -> list[MaterialPriceRead]:
        for item in items:
            stmt = pg_insert(MaterialPriceMaster).values(
                material_code=item.material_code,
                material_name=item.material_name,
                price_per_kg=item.price_per_kg,
                density=item.density,
                notes=item.notes,
                updated_by=updated_by,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["material_code"],
                set_={
                    "material_name": stmt.excluded.material_name,
                    "price_per_kg": stmt.excluded.price_per_kg,
                    "density": stmt.excluded.density,
                    "notes": stmt.excluded.notes,
                    "updated_by": stmt.excluded.updated_by,
                },
            )
            await self.db.execute(stmt)
        await self.db.flush()
        return await self.list_material_prices()

    async def get_process_price(
        self, process_type: str, material_grade: str | None = None
    ) -> ProcessPriceMaster | None:
        """material_grade 우선 조회, 없으면 공통(NULL) 폴백"""
        if material_grade:
            row = (await self.db.execute(
                select(ProcessPriceMaster).where(
                    ProcessPriceMaster.process_type == process_type,
                    ProcessPriceMaster.material_grade == material_grade,
                )
            )).scalar_one_or_none()
            if row:
                return row
        return (await self.db.execute(
            select(ProcessPriceMaster).where(
                ProcessPriceMaster.process_type == process_type,
                ProcessPriceMaster.material_grade.is_(None),
            )
        )).scalar_one_or_none()

    async def get_material_price(self, material_code: str) -> MaterialPriceMaster | None:
        return (await self.db.execute(
            select(MaterialPriceMaster).where(MaterialPriceMaster.material_code == material_code)
        )).scalar_one_or_none()
