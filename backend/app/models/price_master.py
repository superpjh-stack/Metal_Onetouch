"""단가 마스터 모델 (공정 단가 + 재질 단가)"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class ProcessPriceMaster(Base, UUIDMixin):
    """공정별 단가 마스터 — 재질등급별 단가 오버라이드 지원"""

    __tablename__ = "process_price_master"

    process_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    material_grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    price_unit: Mapped[str] = mapped_column(String(30), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<ProcessPriceMaster {self.process_type}/{self.material_grade or 'common'}>"


class MaterialPriceMaster(Base, UUIDMixin):
    """재질별 kg 단가 마스터 — 재료비 계산 기준"""

    __tablename__ = "material_price_master"

    material_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    material_name: Mapped[str] = mapped_column(String(200), nullable=False)
    price_per_kg: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    density: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=Decimal("7.93"))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<MaterialPriceMaster {self.material_code} {self.price_per_kg}원/kg>"
