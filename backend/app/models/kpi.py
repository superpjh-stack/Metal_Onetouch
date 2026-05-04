"""KPI 목표값 모델"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin


class KpiTarget(Base, UUIDMixin):
    """KPI 목표값 설정 — metric_key 당 1건"""

    __tablename__ = "kpi_targets"

    metric_key: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    target_value: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="%")
    period: Mapped[str] = mapped_column(String(10), nullable=False, default="daily")
    updated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<KpiTarget {self.metric_key}={self.target_value}{self.unit}>"
