"""YOLOv8 추론 서비스"""
import io
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.annotation import TrainingJob


class YoloService:
    _model_cache: dict[str, object] = {}

    async def get_active_model(self, db: AsyncSession) -> Optional[object]:
        """활성 training_jobs에서 .pt 파일 로드 (캐시)"""
        job = (await db.execute(
            select(TrainingJob).where(TrainingJob.is_active == True)
        )).scalar_one_or_none()
        if not job or not job.model_s3_path:
            return None

        job_id = str(job.id)
        if job_id in self._model_cache:
            return self._model_cache[job_id]

        try:
            from ultralytics import YOLO
            from app.core.storage import storage_service
            import tempfile, os

            # MinIO에서 .pt 다운로드
            bucket, key = self._parse_s3_path(job.model_s3_path)
            url = storage_service.get_presigned_download_url(bucket, key)

            import httpx
            async with httpx.AsyncClient() as http:
                resp = await http.get(url)
                resp.raise_for_status()
                model_bytes = resp.content

            with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as f:
                f.write(model_bytes)
                tmp_path = f.name

            model = YOLO(tmp_path)
            os.unlink(tmp_path)
            self._model_cache[job_id] = model
            return model
        except Exception:
            return None

    def predict(self, model: object, image_bytes: bytes) -> dict:
        """이미지 바이트 → parsed_objects 표준 형식"""
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(image_bytes))
            results = model(img, verbose=False)
            objects = self._results_to_objects(results)
            confidence = self._calc_confidence(results)
            return {
                "objects": objects,
                "confidence": confidence,
                "source": "yolo",
            }
        except Exception as exc:
            return {"objects": [], "confidence": 0.0, "source": "yolo", "error": str(exc)}

    def _results_to_objects(self, results) -> list[dict]:
        objects = []
        names = results[0].names if results else {}
        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls_id = int(box.cls.item())
                label = names.get(cls_id, "cut")
                conf = float(box.conf.item())
                x, y, w, h = box.xywh[0].tolist()
                obj: dict = {"type": label, "count": 1, "confidence": round(conf, 4)}
                if label == "hole":
                    obj["diameter"] = round(min(w, h), 2)
                elif label in ("cut", "weld", "slot"):
                    obj["length"] = round(max(w, h), 2)
                elif label == "bend":
                    obj["angle"] = 90.0
                objects.append(obj)
        return objects

    def _calc_confidence(self, results) -> float:
        confs = []
        for r in results:
            if r.boxes is not None:
                confs.extend(float(b.conf.item()) for b in r.boxes)
        return round(sum(confs) / len(confs), 4) if confs else 0.0

    @staticmethod
    def _parse_s3_path(s3_path: str) -> tuple[str, str]:
        """'bucket/key/path' → (bucket, key/path)"""
        parts = s3_path.lstrip("/").split("/", 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return "onetouch-mes", s3_path
