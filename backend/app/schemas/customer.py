"""고객사 Pydantic 스키마"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CustomerCreate(BaseModel):
    customer_code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=200)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    business_no: Optional[str] = Field(None, max_length=20)
    credit_limit: Optional[float] = None
    is_active: bool = True
    notes: Optional[str] = None


class CustomerRead(CustomerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class CustomerUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, max_length=200)
    contact_person: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = None
    business_no: Optional[str] = Field(None, max_length=20)
    credit_limit: Optional[float] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None
