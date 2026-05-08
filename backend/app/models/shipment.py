"""출하/물류 모델"""
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


SHIPMENT_STATUS_VALUES = ("pending", "shipped", "delivered", "cancelled")


class Shipment(Base, UUIDMixin):
    """출하 마스터"""

    __tablename__ = "shipments"

    shipment_number: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    planned_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    shipped_date: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    delivered_date: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    customer = relationship("Customer")
    lots: Mapped[list["ShipmentLot"]] = relationship(
        "ShipmentLot",
        back_populates="shipment",
        cascade="all, delete-orphan",
    )

    @property
    def customer_name(self) -> str | None:
        return self.customer.name if self.customer else None

    def __repr__(self) -> str:
        return f"<Shipment {self.shipment_number} [{self.status}]>"


class ShipmentLot(Base, UUIDMixin):
    """출하 LOT 묶음"""

    __tablename__ = "shipment_lots"
    __table_args__ = (
        UniqueConstraint("shipment_id", "lot_id", name="uq_shipment_lot"),
    )

    shipment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    lot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    qty: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[float | None] = mapped_column(Numeric(15, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )

    shipment: Mapped[Shipment] = relationship("Shipment", back_populates="lots")
    lot = relationship("Lot")

    def __repr__(self) -> str:
        return f"<ShipmentLot shipment={self.shipment_id} lot={self.lot_id}>"
