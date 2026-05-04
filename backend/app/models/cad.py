"""CAD 도면 분석 모델"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


CAD_ANALYSIS_STATUS_VALUES = ("pending", "analyzing", "completed", "failed")


class CadDrawing(Base, UUIDMixin):
    """CAD 도면 업로드 + GPT-4o Vision 분석 결과"""

    __tablename__ = "cad_drawings"

    drawing_number: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True, index=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("uploaded_files.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    analysis_status: Mapped[str] = mapped_column(
        Enum(*CAD_ANALYSIS_STATUS_VALUES, name="cad_analysis_status_enum"),
        nullable=False,
        default="pending",
        index=True,
    )
    raw_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    parsed_objects: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    dimensions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    material_hint: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 3), nullable=True)
    analyzed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
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

    file = relationship("UploadedFile", lazy="select")
    customer = relationship("Customer", lazy="select")

    def __repr__(self) -> str:
        return f"<CadDrawing {self.drawing_number} [{self.analysis_status}]>"
