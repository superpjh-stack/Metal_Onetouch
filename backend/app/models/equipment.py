import uuid
from datetime import date
from typing import Optional

from sqlalchemy import Boolean, Date, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

EQUIPMENT_STATUSES = (
    "running",
    "idle",
    "maintenance",
    "breakdown",
    "decommissioned",
)


class Equipment(Base, UUIDMixin, TimestampMixin):
    """설비 마스터 모델"""

    __tablename__ = "equipment"

    equipment_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    process_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("processes.id", ondelete="SET NULL"), nullable=True, index=True
    )
    manufacturer: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    model_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    serial_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(
        Enum(*EQUIPMENT_STATUSES, name="equipment_status_enum"),
        default="idle",
        nullable=False,
    )
    installed_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_maint_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_maint_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    process: Mapped[Optional["ProcessType"]] = relationship(  # noqa: F821
        "ProcessType", back_populates="equipment_list"
    )
    work_orders: Mapped[list["WorkOrder"]] = relationship(  # noqa: F821
        "WorkOrder", back_populates="equipment"
    )

    def __repr__(self) -> str:
        return f"<Equipment {self.equipment_code} {self.name} [{self.status}]>"
