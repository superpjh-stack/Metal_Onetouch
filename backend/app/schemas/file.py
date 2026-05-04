"""파일 업로드 스키마"""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PresignedUploadRequest(BaseModel):
    original_name: str
    mime_type: str = "application/octet-stream"
    folder: str = "cad-drawings"


class PresignedUploadResponse(BaseModel):
    file_id: uuid.UUID
    presigned_url: str
    object_key: str
    expires_in: int = 3600


class ConfirmUploadRequest(BaseModel):
    file_id: uuid.UUID
    file_size: int
    file_hash: str


class UploadedFileRead(BaseModel):
    id: uuid.UUID
    bucket: str
    object_key: str
    original_name: str
    mime_type: Optional[str]
    file_size: Optional[int]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class DownloadUrlResponse(BaseModel):
    download_url: str
    expires_in: int = 3600
