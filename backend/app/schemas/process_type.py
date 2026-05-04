"""공정 Pydantic 스키마"""
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

ProcessTypeEnum = Literal[
    "cutting", "forming", "welding", "painting", "inspection", "assembly", "other"
]


class ProcessTypeCreate(BaseModel):
    process_code: str = Field(..., max_length=20)
    name: str = Field(..., max_length=200)
    process_type: ProcessTypeEnum
    std_time_min: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    is_active: bool = True


class ProcessTypeRead(ProcessTypeCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ProcessTypeUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(None, max_length=200)
    process_type: Optional[ProcessTypeEnum] = None
    std_time_min: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None
    is_active: Optional[bool] = None
