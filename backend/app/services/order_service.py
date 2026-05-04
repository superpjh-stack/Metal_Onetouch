"""수주 Service Layer"""
import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.order import Order, OrderItem, ORDER_STATUS_TRANSITIONS
from app.schemas.order import OrderCreate, OrderRead, OrderItemRead


class OrderService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_order_number(self) -> str:
        """ORD-{YYYYMMDD}-{4자리 SEQ}"""
        today_str = date.today().strftime("%Y%m%d")
        prefix = f"ORD-{today_str}-"
        result = await self.db.execute(
            select(func.count(Order.id)).where(
                Order.order_number.like(f"{prefix}%")
            )
        )
        count = result.scalar_one() or 0
        return f"{prefix}{count + 1:04d}"

    async def create_order(
        self,
        data: OrderCreate,
        created_by: uuid.UUID,
    ) -> OrderRead:
        customer = (await self.db.execute(
            select(Customer).where(Customer.id == data.customer_id)
        )).scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

        order_number = await self.generate_order_number()
        total = sum(
            (i.quantity * i.unit_price) for i in data.items if i.unit_price is not None
        ) or None

        order = Order(
            order_number=order_number,
            customer_id=data.customer_id,
            ordered_date=data.ordered_date,
            due_date=data.due_date,
            total_amount=total,
            notes=data.notes,
            created_by=created_by,
        )
        self.db.add(order)
        await self.db.flush()

        for item in data.items:
            self.db.add(OrderItem(
                order_id=order.id,
                material_name=item.material_name,
                material_code=item.material_code,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
            ))

        await self.db.flush()
        return await self._reload(order.id, customer_name=customer.name)

    async def update_status(
        self,
        order_id: uuid.UUID,
        new_status: str,
    ) -> OrderRead:
        order = await self._get_or_404(order_id)
        if not order.can_transition_to(new_status):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot transition {order.status} → {new_status}",
            )
        order.status = new_status
        await self.db.flush()
        customer = (await self.db.execute(
            select(Customer).where(Customer.id == order.customer_id)
        )).scalar_one_or_none()
        return await self._reload(order.id, customer_name=customer.name if customer else None)

    async def list_orders(
        self,
        order_status: str | None = None,
        customer_id: uuid.UUID | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[OrderRead], int]:
        q = select(Order).options(joinedload(Order.items), joinedload(Order.customer))
        if order_status:
            q = q.where(Order.status == order_status)
        if customer_id:
            q = q.where(Order.customer_id == customer_id)
        if date_from:
            q = q.where(Order.ordered_date >= date_from)
        if date_to:
            q = q.where(Order.ordered_date <= date_to)

        total = (await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )).scalar_one()

        rows = (await self.db.execute(
            q.order_by(Order.created_at.desc()).offset((page - 1) * limit).limit(limit)
        )).scalars().unique().all()

        items = []
        for o in rows:
            read = OrderRead.model_validate(o)
            items.append(read.model_copy(update={
                "customer_name": o.customer.name if o.customer else None,
            }))
        return items, total

    async def get_order(self, order_id: uuid.UUID) -> OrderRead:
        order = (await self.db.execute(
            select(Order)
            .options(joinedload(Order.items), joinedload(Order.customer))
            .where(Order.id == order_id)
        )).scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        read = OrderRead.model_validate(order)
        return read.model_copy(update={
            "customer_name": order.customer.name if order.customer else None,
        })

    async def _get_or_404(self, order_id: uuid.UUID) -> Order:
        order = (await self.db.execute(
            select(Order).where(Order.id == order_id)
        )).scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        return order

    async def _reload(self, order_id: uuid.UUID, customer_name: str | None = None) -> OrderRead:
        order = (await self.db.execute(
            select(Order)
            .options(joinedload(Order.items))
            .where(Order.id == order_id)
        )).scalar_one()
        read = OrderRead.model_validate(order)
        return read.model_copy(update={"customer_name": customer_name})
