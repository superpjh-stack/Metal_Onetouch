from typing import Optional

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

PROCESS_TYPES = (
    "cutting",
    "forming",
    "welding",
    "painting",
    "inspection",
    "assembly",
    "other",
)


class ProcessType(Base, UUIDMixin, TimestampMixin):
    """공정 마스터 모델 (테이블명: processes)"""

    __tablename__ = "processes"

    process_code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    process_type: Mapped[str] = mapped_column(
        Enum(*PROCESS_TYPES, name="process_type_enum"),
        nullable=False,
    )
    std_time_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    equipment_list: Mapped[list["Equipment"]] = relationship(  # noqa: F821
        "Equipment", back_populates="process"
    )
    work_orders: Mapped[list["WorkOrder"]] = relationship(  # noqa: F821
        "WorkOrder", back_populates="process"
    )

    def __repr__(self) -> str:
        return f"<ProcessType {self.process_code} {self.name}>"
