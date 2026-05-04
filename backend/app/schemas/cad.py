"""CAD 도면 분석 스키마"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CadObjectItem(BaseModel):
    type: str
    count: int = 1
    diameter: Optional[float] = None
    width: Optional[float] = None
    length: Optional[float] = None
    angle: Optional[float] = None
    radius: Optional[float] = None
    tolerance: Optional[str] = None


class CadDimensions(BaseModel):
    length: float
    width: float
    thickness: float


class CadParsedResult(BaseModel):
    objects: list[CadObjectItem] = Field(default_factory=list)
    dimensions: Optional[CadDimensions] = None
    material_hint: Optional[str] = None
    confidence: float = 0.0


class CadDrawingCreate(BaseModel):
    file_id: uuid.UUID
    customer_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class CadDrawingRead(BaseModel):
    id: uuid.UUID
    drawing_number: str
    file_id: uuid.UUID
    customer_id: Optional[uuid.UUID]
    analysis_status: str
    parsed_objects: Optional[dict] = None
    dimensions: Optional[dict] = None
    material_hint: Optional[str]
    confidence: Optional[Decimal]
    analyzed_at: Optional[datetime]
    error_message: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class CadStatusResponse(BaseModel):
    id: uuid.UUID
    drawing_number: str
    analysis_status: str
    confidence: Optional[Decimal]
    analyzed_at: Optional[datetime]
    error_message: Optional[str]
    model_config = ConfigDict(from_attributes=True)


class CadUpdateObjects(BaseModel):
    objects: list[CadObjectItem]
    dimensions: CadDimensions
