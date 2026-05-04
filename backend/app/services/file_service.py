"""파일 업로드 서비스 — MinIO presigned URL 기반"""
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.storage import storage_service
from app.models.file import UploadedFile
from app.schemas.file import (
    ConfirmUploadRequest,
    DownloadUrlResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
    UploadedFileRead,
)


class FileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_presigned_upload(
        self,
        req: PresignedUploadRequest,
        uploaded_by: uuid.UUID,
    ) -> PresignedUploadResponse:
        ext = req.original_name.rsplit(".", 1)[-1].lower() if "." in req.original_name else "bin"
        now = datetime.utcnow()
        object_key = f"{req.folder}/{now:%Y/%m}/{uuid.uuid4()}.{ext}"
        bucket = settings.MINIO_BUCKET

        storage_service.ensure_bucket(bucket)
        presigned_url = storage_service.get_presigned_upload_url(bucket, object_key)

        file_record = UploadedFile(
            bucket=bucket,
            object_key=object_key,
            original_name=req.original_name,
            mime_type=req.mime_type,
            uploaded_by=uploaded_by,
        )
        self.db.add(file_record)
        await self.db.flush()

        return PresignedUploadResponse(
            file_id=file_record.id,
            presigned_url=presigned_url,
            object_key=object_key,
            expires_in=3600,
        )

    async def confirm_upload(self, req: ConfirmUploadRequest) -> UploadedFileRead:
        # 동일 hash 파일이 이미 존재하면 기존 파일 반환
        existing = (await self.db.execute(
            select(UploadedFile).where(
                UploadedFile.file_hash == req.file_hash,
                UploadedFile.id != req.file_id,
            )
        )).scalar_one_or_none()
        if existing:
            return UploadedFileRead.model_validate(existing)

        file_record = (await self.db.execute(
            select(UploadedFile).where(UploadedFile.id == req.file_id)
        )).scalar_one_or_none()
        if not file_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File record not found")

        file_record.file_size = req.file_size
        file_record.file_hash = req.file_hash
        await self.db.flush()
        return UploadedFileRead.model_validate(file_record)

    async def get_download_url(self, file_id: uuid.UUID) -> DownloadUrlResponse:
        file_record = (await self.db.execute(
            select(UploadedFile).where(UploadedFile.id == file_id)
        )).scalar_one_or_none()
        if not file_record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

        url = storage_service.get_presigned_download_url(
            file_record.bucket, file_record.object_key
        )
        return DownloadUrlResponse(download_url=url, expires_in=3600)
