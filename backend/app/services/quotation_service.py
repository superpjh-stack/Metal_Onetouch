"""견적서 서비스 — 규칙 기반 원가 계산 + Qdrant 유사 견적 검색"""
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cad import CadDrawing
from app.models.quotation import QUOTATION_STATUS_TRANSITIONS, Quotation, QuotationItem
from app.schemas.quotation import (
    QuotationCreate,
    QuotationItemCreate,
    QuotationItemUpdate,
    QuotationLinkOrder,
    QuotationRead,
    QuotationSummary,
)
from app.services.price_master_service import PriceMasterService


class QuotationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _generate_quotation_number(self) -> str:
        from datetime import date as _date
        today_str = _date.today().strftime("%Y%m%d")
        prefix = f"QUO-{today_str}-"
        count = (await self.db.execute(
            select(func.count(Quotation.id)).where(Quotation.quotation_number.like(f"{prefix}%"))
        )).scalar_one() or 0
        return f"{prefix}{count + 1:04d}"

    async def calculate_from_drawing(
        self,
        data: QuotationCreate,
        created_by: uuid.UUID,
    ) -> QuotationRead:
        price_svc = PriceMasterService(self.db)

        material_cost = Decimal("0")
        process_cost = Decimal("0")
        items: list[QuotationItem] = []
        sort = 0

        if data.drawing_id:
            drawing = (await self.db.execute(
                select(CadDrawing).where(CadDrawing.id == data.drawing_id)
            )).scalar_one_or_none()
            if not drawing:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drawing not found")
            if drawing.analysis_status != "completed":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Drawing analysis not completed (status: {drawing.analysis_status})",
                )

            material_code = data.material_code or drawing.material_hint or "SPCC"
            mat_cost, mat_item = await self._calc_material_cost(
                drawing.dimensions or {}, material_code, price_svc
            )
            material_cost = mat_cost
            items.append(QuotationItem(**mat_item.model_dump(), sort_order=sort))
            sort += 1

            proc_items = await self._calc_process_items(
                (drawing.parsed_objects or {}).get("objects", []),
                material_code,
                price_svc,
                sort,
            )
            for pi in proc_items:
                process_cost += pi.amount
                items.append(QuotationItem(**pi.model_dump(exclude={"sort_order"}), sort_order=sort))
                sort += 1

        total_amount = material_cost + process_cost
        margin = Decimal(str(data.margin_rate))
        final_amount = (total_amount * (1 + margin)).quantize(Decimal("0.01"))

        quotation = Quotation(
            quotation_number=await self._generate_quotation_number(),
            customer_id=data.customer_id,
            drawing_id=data.drawing_id,
            status="draft",
            material_cost=material_cost,
            process_cost=process_cost,
            total_amount=total_amount,
            margin_rate=margin,
            final_amount=final_amount,
            valid_until=date.today() + timedelta(days=30),
            notes=data.notes,
            created_by=created_by,
        )
        self.db.add(quotation)
        await self.db.flush()

        for item in items:
            item.quotation_id = quotation.id
            self.db.add(item)

        await self.db.flush()
        await self.db.refresh(quotation)
        return await self._to_read(quotation)

    async def _calc_material_cost(
        self,
        dimensions: dict,
        material_code: str,
        price_svc: PriceMasterService,
    ) -> tuple[Decimal, QuotationItemCreate]:
        mat = await price_svc.get_material_price(material_code)
        length = Decimal(str(dimensions.get("length") or 0))
        width = Decimal(str(dimensions.get("width") or 0))
        thickness = Decimal(str(dimensions.get("thickness") or 0))

        density = Decimal(str(mat.density)) if mat else Decimal("7.93")
        price_per_kg = Decimal(str(mat.price_per_kg)) if mat else Decimal("2000")

        volume_cm3 = (length * width * thickness) / Decimal("1000")
        weight_kg = volume_cm3 * density / Decimal("1000")
        cost = (weight_kg * price_per_kg).quantize(Decimal("0.01"))

        return cost, QuotationItemCreate(
            item_type="material",
            description=f"{material_code} — {length}×{width}×{thickness}mm ({weight_kg:.3f}kg)",
            quantity=weight_kg,
            unit="kg",
            unit_price=price_per_kg,
            amount=cost,
            sort_order=0,
        )

    async def _calc_process_items(
        self,
        objects: list[dict],
        material_grade: str,
        price_svc: PriceMasterService,
        base_sort: int,
    ) -> list[QuotationItemCreate]:
        import math

        TYPE_MAP = {
            "hole": "drilling",
            "slot": "cutting",
            "bend": "bending",
            "cut":  "cutting",
            "weld": "welding",
        }
        items: list[QuotationItemCreate] = []
        sort = base_sort
        for obj in objects:
            obj_type = obj.get("type", "")
            process_type = TYPE_MAP.get(obj_type, "cutting")
            count = Decimal(str(obj.get("count") or 1))
            price_row = await price_svc.get_process_price(process_type, material_grade)
            base_price = Decimal(str(price_row.unit_price)) if price_row else Decimal("500")

            # Correction factors per design section 3.4
            correction = Decimal("1.0")
            if obj_type == "hole":
                diam = obj.get("diameter")
                if diam and float(diam) > 0:
                    correction = Decimal(str(round(math.sqrt(float(diam) / 10.0), 4)))
            elif obj_type == "bend":
                angle = obj.get("angle")
                if angle and float(angle) > 0:
                    correction = Decimal(str(round(float(angle) / 90.0, 4)))
            elif obj_type in ("cut", "slot", "weld"):
                length = obj.get("length")
                if length and float(length) > 0:
                    # per_mm pricing: length × 0.1 (convert mm to cm factor)
                    correction = Decimal(str(round(float(length) * 0.1, 4)))

            effective_price = (base_price * correction).quantize(Decimal("0.0001"))
            amount = (count * effective_price).quantize(Decimal("0.01"))

            items.append(QuotationItemCreate(
                item_type=process_type,
                description=f"{obj_type} ×{int(count)}",
                quantity=count,
                unit="ea",
                unit_price=effective_price,
                amount=amount,
                sort_order=sort,
            ))
            sort += 1
        return items

    async def get_quotation(self, quotation_id: uuid.UUID) -> QuotationRead:
        q = await self._get_or_404(quotation_id)
        return await self._to_read(q)

    async def list_quotations(
        self,
        customer_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[QuotationSummary], int]:
        q = select(Quotation)
        if customer_id:
            q = q.where(Quotation.customer_id == customer_id)
        if status:
            q = q.where(Quotation.status == status)

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        rows = (await self.db.execute(
            q.options(selectinload(Quotation.customer))
            .order_by(Quotation.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )).scalars().all()

        summaries: list[QuotationSummary] = []
        for row in rows:
            customer_name = row.customer.name if row.customer else None
            summaries.append(QuotationSummary(
                id=row.id,
                quotation_number=row.quotation_number,
                customer_name=customer_name,
                final_amount=row.final_amount,
                total_amount=row.total_amount,
                status=row.status,
                created_at=row.created_at,
            ))
        return summaries, total

    async def update_items(
        self, quotation_id: uuid.UUID, updates: list[QuotationItemUpdate]
    ) -> QuotationRead:
        quotation = await self._get_or_404(quotation_id)
        if quotation.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Only draft quotations can be edited",
            )
        update_map = {u.id: u for u in updates}
        for item in quotation.items:
            if item.id in update_map:
                u = update_map[item.id]
                qty = u.quantity if u.quantity is not None else item.quantity
                item.unit_price = u.unit_price
                if u.quantity is not None:
                    item.quantity = u.quantity
                if u.description is not None:
                    item.description = u.description
                item.amount = (qty * u.unit_price).quantize(Decimal("0.01"))

        self._recalculate_totals(quotation)
        await self.db.flush()
        await self.db.refresh(quotation)
        return await self._to_read(quotation)

    def _recalculate_totals(self, quotation: Quotation) -> None:
        mat = sum(
            i.amount for i in quotation.items if i.item_type == "material"
        )
        proc = sum(
            i.amount for i in quotation.items if i.item_type != "material"
        )
        quotation.material_cost = mat
        quotation.process_cost = proc
        quotation.total_amount = mat + proc
        quotation.final_amount = (
            quotation.total_amount * (1 + quotation.margin_rate)
        ).quantize(Decimal("0.01"))

    async def transition_status(self, quotation_id: uuid.UUID, new_status: str) -> QuotationRead:
        quotation = await self._get_or_404(quotation_id)
        if not quotation.can_transition_to(new_status):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Cannot transition from '{quotation.status}' to '{new_status}'",
            )
        quotation.status = new_status
        await self.db.flush()
        await self.db.refresh(quotation)
        return await self._to_read(quotation)

    async def link_order(self, quotation_id: uuid.UUID, data: QuotationLinkOrder) -> QuotationRead:
        quotation = await self._get_or_404(quotation_id)
        quotation.order_id = data.order_id
        if quotation.can_transition_to("accepted"):
            quotation.status = "accepted"
        await self.db.flush()
        await self.db.refresh(quotation)
        return await self._to_read(quotation)

    async def find_similar_quotations(
        self, quotation_id: uuid.UUID, top_k: int = 5
    ) -> list[QuotationSummary]:
        """Qdrant 벡터 유사도 검색 (미설치 시 DB amount 기반 폴백)"""
        source = await self._get_or_404(quotation_id)
        try:
            from qdrant_client import QdrantClient
            from app.core.config import settings
            client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
            results = client.search(
                collection_name=settings.QDRANT_COLLECTION,
                query_vector=[float(source.total_amount)] + [0.0] * 127,
                limit=top_k + 1,
            )
            ids = [
                uuid.UUID(str(r.payload["quotation_id"]))
                for r in results
                if str(r.payload.get("quotation_id")) != str(quotation_id)
            ][:top_k]
            rows = (await self.db.execute(
                select(Quotation).options(selectinload(Quotation.customer))
                .where(Quotation.id.in_(ids))
            )).scalars().all()
        except Exception:
            rows = (await self.db.execute(
                select(Quotation).options(selectinload(Quotation.customer))
                .where(Quotation.id != quotation_id)
                .order_by(
                    func.abs(Quotation.total_amount - source.total_amount)
                )
                .limit(top_k)
            )).scalars().all()

        summaries: list[QuotationSummary] = []
        for row in rows:
            customer_name = row.customer.name if row.customer else None
            summaries.append(QuotationSummary(
                id=row.id,
                quotation_number=row.quotation_number,
                customer_name=customer_name,
                final_amount=row.final_amount,
                total_amount=row.total_amount,
                status=row.status,
                created_at=row.created_at,
            ))
        return summaries

    async def _get_or_404(self, quotation_id: uuid.UUID) -> Quotation:
        row = (await self.db.execute(
            select(Quotation).where(Quotation.id == quotation_id)
        )).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quotation not found")
        return row

    async def _to_read(self, quotation: Quotation) -> QuotationRead:
        await self.db.refresh(quotation, ["items", "customer"])
        customer_name = quotation.customer.name if quotation.customer else None
        data = QuotationRead.model_validate(quotation)
        data.customer_name = customer_name
        return data
