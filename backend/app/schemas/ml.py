"""ML 관련 Pydantic 스키마 (어노테이션, 데이터셋, 학습 잡)"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AnnotationTaskRead(BaseModel):
    id: uuid.UUID
    drawing_id: uuid.UUID
    status: str
    original_parsed: dict
    corrected_parsed: Optional[dict] = None
    annotator_id: Optional[uuid.UUID] = None
    assigned_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    skip_reason: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnnotationSubmit(BaseModel):
    corrected_parsed: dict


class AnnotationDatasetRead(BaseModel):
    id: uuid.UUID
    version: str
    image_count: int
    label_counts: dict
    s3_path: Optional[str] = None
    status: str
    built_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetBuildRequest(BaseModel):
    notes: Optional[str] = None


class TrainingJobCreate(BaseModel):
    dataset_id: uuid.UUID
    model_version: str = "yolov8s"
    epochs: int = Field(default=100, ge=10, le=500)
    batch_size: int = Field(default=16, ge=4, le=64)
    img_size: int = Field(default=640, ge=320, le=1280)
    hyperparams: dict = {}


class TrainingJobRead(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    model_version: str
    epochs: int
    batch_size: int
    img_size: int
    status: str
    train_map50: Optional[float] = None
    val_map50: Optional[float] = None
    model_s3_path: Optional[str] = None
    mlflow_run_id: Optional[str] = None
    is_active: bool
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    hyperparams: dict
    created_at: datetime

    model_config = {"from_attributes": True}
