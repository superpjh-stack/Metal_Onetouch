"""어노테이션 태스크, 데이터셋, YOLOv8 학습 잡 모델"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class AnnotationTask(Base, UUIDMixin):
    """CAD 분석 결과 검토 및 보정 태스크"""

    __tablename__ = "annotation_tasks"

    drawing_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("cad_drawings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    original_parsed: Mapped[dict] = mapped_column(JSONB, nullable=False)
    corrected_parsed: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    annotator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    skip_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )

    drawing = relationship("CadDrawing", lazy="select")
    annotator = relationship("User", lazy="select", foreign_keys=[annotator_id])

    def __repr__(self) -> str:
        return f"<AnnotationTask drawing={self.drawing_id} [{self.status}]>"


class AnnotationDataset(Base, UUIDMixin):
    """YOLO 형식 학습 데이터셋 버전"""

    __tablename__ = "annotation_datasets"

    version: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    image_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    label_counts: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    s3_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="building")
    built_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )

    jobs: Mapped[list["TrainingJob"]] = relationship(back_populates="dataset")

    def __repr__(self) -> str:
        return f"<AnnotationDataset {self.version} [{self.status}]>"


class TrainingJob(Base, UUIDMixin):
    """YOLOv8 모델 학습 잡"""

    __tablename__ = "training_jobs"

    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("annotation_datasets.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    model_version: Mapped[str] = mapped_column(String(20), nullable=False, default="yolov8s")
    epochs: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    batch_size: Mapped[int] = mapped_column(Integer, nullable=False, default=16)
    img_size: Mapped[int] = mapped_column(Integer, nullable=False, default=640)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    train_map50: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    val_map50: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 4), nullable=True)
    model_s3_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mlflow_run_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMPTZ, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    hyperparams: Mapped[dict] = mapped_column(JSONB, nullable=False, default={})
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )

    dataset: Mapped["AnnotationDataset"] = relationship(back_populates="jobs")

    def __repr__(self) -> str:
        return f"<TrainingJob {self.model_version} [{self.status}] map50={self.val_map50}>"


class DxfLayerMapping(Base, UUIDMixin):
    """DXF 레이어 패턴 → 공정 유형 매핑"""

    __tablename__ = "dxf_layer_mappings"

    layer_pattern: Mapped[str] = mapped_column(String(100), nullable=False)
    process_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<DxfLayerMapping '{self.layer_pattern}' → {self.process_type}>"
