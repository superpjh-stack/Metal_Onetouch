"""MinIO 파일 스토리지 클라이언트"""
from datetime import timedelta

from minio import Minio

from app.core.config import settings


class StorageService:
    def __init__(self) -> None:
        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    def ensure_bucket(self, bucket: str) -> None:
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

    def get_presigned_upload_url(
        self, bucket: str, object_key: str, expires_seconds: int = 3600
    ) -> str:
        return self._client.presigned_put_object(
            bucket, object_key, expires=timedelta(seconds=expires_seconds)
        )

    def get_presigned_download_url(
        self, bucket: str, object_key: str, expires_seconds: int = 3600
    ) -> str:
        return self._client.presigned_get_object(
            bucket, object_key, expires=timedelta(seconds=expires_seconds)
        )

    def delete_object(self, bucket: str, object_key: str) -> None:
        self._client.remove_object(bucket, object_key)

    def object_exists(self, bucket: str, object_key: str) -> bool:
        try:
            self._client.stat_object(bucket, object_key)
            return True
        except Exception:
            return False


storage_service = StorageService()
