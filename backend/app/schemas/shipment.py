"""출하/물류 스키마"""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ShipmentLotItem(BaseModel):
    lot_id: UUID
    qty: Decimal
    unit_price: Decimal | None = None


class ShipmentCreate(BaseModel):
    customer_id: UUID
    planned_date: date | None = None
    notes: str | None = None
    lots: list[ShipmentLotItem] = []


class ShipmentUpdate(BaseModel):
    planned_date: date | None = None
    notes: str | None = None


class ShipmentStatusUpdate(BaseModel):
    status: Literal["shipped", "delivered", "cancelled"]
    notes: str | None = None


class ShipmentLotRead(BaseModel):
    id: UUID
    lot_id: UUID
    qty: Decimal
    unit_price: Decimal | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ShipmentRead(BaseModel):
    id: UUID
    shipment_number: str
    customer_id: UUID
    customer_name: str | None = None
    status: str
    planned_date: date | None
    shipped_date: datetime | None
    delivered_date: datetime | None
    notes: str | None
    lots: list[ShipmentLotRead] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
