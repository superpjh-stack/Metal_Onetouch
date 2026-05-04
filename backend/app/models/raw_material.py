import uuid
from typing import Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

MATERIAL_CATEGORIES = (
    "steel_sheet",
    "stainless",
    "aluminum",
    "copper",
    "pipe",
    "bar",
    "other",
)


class RawMaterial(Base, UUIDMixin, TimestampMixin):
    """원자재 마스터 모델"""

    __tablename__ = "raw_materials"

    material_code: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    category: Mapped[str] = mapped_column(
        Enum(*MATERIAL_CATEGORIES, name="material_category_enum"),
        default="other",
        nullable=False,
    )
    spec: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="EA")
    supplier_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    stock_qty: Mapped[float] = mapped_column(
        Numeric(12, 3), default=0, nullable=False
    )
    min_stock_qty: Mapped[float] = mapped_column(
        Numeric(12, 3), default=0, nullable=False
    )
    unit_price: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    lead_time_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    supplier: Mapped[Optional["Supplier"]] = relationship(  # noqa: F821
        "Supplier", back_populates="raw_materials"
    )

    def __repr__(self) -> str:
        return f"<RawMaterial {self.material_code} {self.name}>"
