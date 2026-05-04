import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

WO_STATUSES = ("pending", "in_progress", "completed", "on_hold", "cancelled")

WO_FINAL_STATUSES = frozenset({"completed", "cancelled"})

WO_STATUS_TRANSITIONS: dict[str, list[str]] = {
    "pending":     ["in_progress", "on_hold", "cancelled"],
    "in_progress": ["completed", "on_hold"],
    "on_hold":     ["pending", "in_progress", "cancelled"],
    "completed":   [],
    "cancelled":   [],
}


class WorkOrder(Base, UUIDMixin, TimestampMixin):
    """작업지시 모델"""

    __tablename__ = "work_orders"

    wo_number: Mapped[str] = mapped_column(
        String(30), unique=True, nullable=False, index=True
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    process_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("processes.id", ondelete="RESTRICT"), nullable=False
    )
    equipment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        Enum(*WO_STATUSES, name="wo_status_enum"),
        default="pending",
        nullable=False,
        index=True,
    )
    planned_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    planned_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    input_qty: Mapped[Optional[float]] = mapped_column(Numeric(12, 3), nullable=True)
    output_qty: Mapped[Optional[float]] = mapped_column(Numeric(12, 3), nullable=True)
    defect_qty: Mapped[float] = mapped_column(
        Numeric(12, 3), default=0, nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    lot: Mapped["Lot"] = relationship("Lot")  # noqa: F821
    process: Mapped["ProcessType"] = relationship(  # noqa: F821
        "ProcessType", back_populates="work_orders"
    )
    equipment: Mapped[Optional["Equipment"]] = relationship(  # noqa: F821
        "Equipment", back_populates="work_orders"
    )
    process_results: Mapped[list["ProcessResult"]] = relationship(
        "ProcessResult", back_populates="work_order"
    )

    def can_transition_to(self, new_status: str) -> bool:
        """현재 상태에서 new_status로 전환 가능한지 확인."""
        return new_status in WO_STATUS_TRANSITIONS.get(self.status, [])

    def __repr__(self) -> str:
        return f"<WorkOrder {self.wo_number} [{self.status}]>"


class ProcessResult(Base, UUIDMixin):
    """공정 실적 모델 — 불변 레코드 (updated_at 없음)"""

    __tablename__ = "process_results"

    work_order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("work_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    equipment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("equipment.id", ondelete="SET NULL"), nullable=True
    )
    worker_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    input_qty: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    output_qty: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    defect_qty: Mapped[float] = mapped_column(
        Numeric(12, 3), default=0, nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    condition_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    defect_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    work_order: Mapped["WorkOrder"] = relationship(
        "WorkOrder", back_populates="process_results"
    )

    def __repr__(self) -> str:
        return f"<ProcessResult wo={self.work_order_id} out={self.output_qty}>"
