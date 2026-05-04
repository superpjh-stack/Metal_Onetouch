"""수주 모델"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


ORDER_STATUS_VALUES = (
    "received",       # 수주 접수
    "confirmed",      # 확정
    "in_production",  # 생산 중
    "shipped",        # 출하
    "completed",      # 완료
    "cancelled",      # 취소
)

ORDER_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "received":      ["confirmed", "cancelled"],
    "confirmed":     ["in_production", "cancelled"],
    "in_production": ["shipped", "cancelled"],
    "shipped":       ["completed"],
    "completed":     [],
    "cancelled":     [],
}


class Order(Base, UUIDMixin, TimestampMixin):
    """수주 마스터"""

    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(*ORDER_STATUS_VALUES, name="order_status_enum"),
        nullable=False,
        default="received",
        index=True,
    )
    ordered_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(16, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    customer = relationship("Customer")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in ORDER_STATUS_TRANSITIONS.get(self.status, [])

    def __repr__(self) -> str:
        return f"<Order {self.order_number} [{self.status}]>"


class OrderItem(Base, UUIDMixin):
    """수주 라인"""

    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    material_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="ea")
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("lots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )

    order: Mapped[Order] = relationship("Order", back_populates="items")
    lot = relationship("Lot")

    def __repr__(self) -> str:
        return f"<OrderItem {self.order_id} {self.material_name}>"
