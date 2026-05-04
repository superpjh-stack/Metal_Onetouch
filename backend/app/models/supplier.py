import uuid
from typing import Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Supplier(Base, UUIDMixin, TimestampMixin):
    """공급업체 마스터 모델"""

    __tablename__ = "suppliers"

    supplier_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    grade: Mapped[str] = mapped_column(
        Enum("A", "B", "C", "D", name="supplier_grade_enum"),
        default="C",
        nullable=False,
    )
    business_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    raw_materials: Mapped[list["RawMaterial"]] = relationship(  # noqa: F821
        "RawMaterial", back_populates="supplier"
    )

    def __repr__(self) -> str:
        return f"<Supplier {self.supplier_code} {self.name} [{self.grade}]>"
