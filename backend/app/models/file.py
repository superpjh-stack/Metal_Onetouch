"""업로드 파일 메타데이터 모델"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import TIMESTAMPTZ
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDMixin


class UploadedFile(Base, UUIDMixin):
    """MinIO 업로드 파일 메타데이터"""

    __tablename__ = "uploaded_files"

    bucket: Mapped[str] = mapped_column(String(100), nullable=False, default="metal-onetouch")
    object_key: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    original_name: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<UploadedFile {self.original_name} [{self.object_key}]>"
