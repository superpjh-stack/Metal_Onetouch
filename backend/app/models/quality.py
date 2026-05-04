"""품질 검사 모델"""
import uuid
from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class QualityInspection(Base, UUIDMixin):
    """품질 검사 이력 (불변 — updated_at 없음)"""

    __tablename__ = "quality_inspections"

    lot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    inspector_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    inspection_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    defect_rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    inspection_date: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now(), index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )

    lot = relationship("Lot", back_populates="quality_inspections")
    inspector = relationship("User")
    defects: Mapped[list["DefectDetail"]] = relationship(
        "DefectDetail",
        back_populates="inspection",
        cascade="all, delete-orphan",
        order_by="DefectDetail.created_at",
    )

    def __repr__(self) -> str:
        return f"<QualityInspection {self.id} lot={self.lot_id} result={self.result}>"


class DefectDetail(Base, UUIDMixin):
    """불량 상세 (불변)"""

    __tablename__ = "defect_details"

    inspection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quality_inspections.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    defect_code: Mapped[str] = mapped_column(String(30), nullable=False)
    defect_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    qty: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False, default=1)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )

    inspection: Mapped[QualityInspection] = relationship(
        "QualityInspection", back_populates="defects"
    )

    def __repr__(self) -> str:
        return f"<DefectDetail {self.defect_code} type={self.defect_type}>"
