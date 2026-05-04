"""원자재 입고 모델"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class RawMaterialReceipt(Base, UUIDMixin):
    """원자재 입고 이력 — 생성 시 LOT 자동 생성"""

    __tablename__ = "raw_material_receipts"

    receipt_number: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True, index=True
    )
    supplier_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("suppliers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    lot_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("lots.id", ondelete="SET NULL"), nullable=True, index=True
    )
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    material_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="kg")
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    received_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )

    supplier = relationship("Supplier")
    lot = relationship("Lot")

    def __repr__(self) -> str:
        return f"<RawMaterialReceipt {self.receipt_number} [{self.material_name}]>"
