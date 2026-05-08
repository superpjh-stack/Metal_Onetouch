"""파일 업로드 엔드포인트 — MinIO presigned URL 2단계"""
import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DBSession
from app.schemas.file import (
    ConfirmUploadRequest,
    DownloadUrlResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
    UploadedFileRead,
)
from app.services.file_service import FileService

router = APIRouter(tags=["Files"])


@router.post("/presigned-upload", response_model=PresignedUploadResponse, status_code=201)
async def create_presigned_upload(
    body: PresignedUploadRequest,
    db: DBSession = None,
    user: CurrentUser = None,
):
    """Step 1: presigned PUT URL + file_id 발급"""
    svc = FileService(db)
    result = await svc.create_presigned_upload(body, uploaded_by=user.id)
    await db.commit()
    return result


@router.post("/confirm-upload", response_model=UploadedFileRead)
async def confirm_upload(
    body: ConfirmUploadRequest,
    db: DBSession = None,
    _: CurrentUser = None,
):
    """Step 2: 업로드 완료 확인 + hash 중복 체크"""
    svc = FileService(db)
    result = await svc.confirm_upload(body)
    await db.commit()
    return result


@router.get("/{file_id}/download-url", response_model=DownloadUrlResponse)
async def get_download_url(
    file_id: uuid.UUID,
    db: DBSession = None,
    _: CurrentUser = None,
):
    """다운로드용 presigned URL 발급"""
    return await FileService(db).get_download_url(file_id)
