"""견적서 모델"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


QUOTATION_STATUS_VALUES = ("draft", "submitted", "accepted", "rejected", "expired")
QUOTATION_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "draft":     ["submitted", "accepted", "expired"],
    "submitted": ["accepted", "rejected", "expired"],
    "accepted":  [],
    "rejected":  ["draft"],
    "expired":   [],
}


class Quotation(Base, UUIDMixin):
    """견적서 — draft/submitted/accepted/rejected/expired 상태 머신"""

    __tablename__ = "quotations"

    quotation_number: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    drawing_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("cad_drawings.id", ondelete="SET NULL"), nullable=True, index=True
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(*QUOTATION_STATUS_VALUES, name="quotation_status_enum"),
        nullable=False,
        default="draft",
        index=True,
    )
    material_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=Decimal("0"))
    process_cost: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=Decimal("0"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=Decimal("0"))
    margin_rate: Mapped[Decimal] = mapped_column(Numeric(5, 3), nullable=False, default=Decimal("0.15"))
    final_amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=Decimal("0"))
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    customer = relationship("Customer", lazy="select")
    drawing = relationship("CadDrawing", lazy="select")
    items: Mapped[list["QuotationItem"]] = relationship(
        "QuotationItem",
        cascade="all, delete-orphan",
        order_by="QuotationItem.sort_order",
        lazy="select",
    )

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in QUOTATION_STATUS_TRANSITIONS.get(self.status, [])

    def __repr__(self) -> str:
        return f"<Quotation {self.quotation_number} [{self.status}]>"


class QuotationItem(Base, UUIDMixin):
    """견적 항목 — 공정별 금액 breakdown"""

    __tablename__ = "quotation_items"

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("1"))
    unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False, default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2), nullable=False, default=Decimal("0"))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<QuotationItem {self.item_type} {self.amount}>"
