"""BOM(자재소요량) 모델"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class BomHeader(Base, UUIDMixin):
    """BOM 헤더 — 견적서 1:1"""

    __tablename__ = "bom_headers"

    quotation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quotations.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    revision: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=1)
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["BomItem"]] = relationship(
        back_populates="bom",
        cascade="all, delete-orphan",
        order_by="BomItem.sort_order",
    )

    def __repr__(self) -> str:
        return f"<BomHeader quotation={self.quotation_id} rev={self.revision}>"


class BomItem(Base, UUIDMixin):
    """BOM 항목 행"""

    __tablename__ = "bom_items"

    bom_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("bom_headers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_code: Mapped[str] = mapped_column(String(50), nullable=False)
    specification: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False, default=1)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")
    unit_weight_kg: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    total_weight_kg: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False, default=0)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )

    bom: Mapped["BomHeader"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<BomItem {self.material_code} {self.specification}>"
