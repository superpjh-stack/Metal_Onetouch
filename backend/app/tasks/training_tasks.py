"""YOLOv8 학습 Celery 태스크"""
import asyncio

from app.core.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.training_tasks.train_yolo_model_task",
    queue="train_queue",
    max_retries=0,
    soft_time_limit=82800,
    time_limit=86400,
)
def train_yolo_model_task(self, job_id: str) -> None:
    asyncio.run(_run_training(job_id))


@celery_app.task(
    bind=True,
    name="app.tasks.training_tasks.build_dataset_task",
    queue="cad_queue",
    max_retries=1,
    default_retry_delay=10,
    soft_time_limit=600,
    time_limit=900,
)
def build_dataset_task(self, dataset_id: str) -> None:
    asyncio.run(_run_build_dataset(dataset_id))


async def _run_training(job_id: str) -> None:
    import os, tempfile, shutil, uuid
    from datetime import datetime
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.annotation import AnnotationDataset, AnnotationTask, TrainingJob

    async with AsyncSessionLocal() as db:
        job = (await db.execute(
            select(TrainingJob).where(TrainingJob.id == uuid.UUID(job_id))
        )).scalar_one_or_none()
        if not job:
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        await db.commit()

        tmp_dir = tempfile.mkdtemp(prefix=f"yolo_{job_id}_")
        try:
            from app.core.storage import storage_service
            from app.core.config import settings
            import httpx

            # 데이터셋 다운로드
            dataset = (await db.execute(
                select(AnnotationDataset).where(AnnotationDataset.id == job.dataset_id)
            )).scalar_one_or_none()

            dataset_dir = os.path.join(tmp_dir, "dataset")
            os.makedirs(os.path.join(dataset_dir, "images", "train"), exist_ok=True)
            os.makedirs(os.path.join(dataset_dir, "labels", "train"), exist_ok=True)

            # 완료된 어노테이션 태스크에서 이미지+레이블 생성
            tasks = (await db.execute(
                select(AnnotationTask).where(AnnotationTask.status == "completed")
            )).scalars().all()

            from app.models.file import UploadedFile
            from app.models.cad import CadDrawing
            class_map = {"hole": 0, "bend": 1, "cut": 2, "weld": 3, "slot": 4}

            for i, task in enumerate(tasks):
                drawing = (await db.execute(
                    select(CadDrawing).where(CadDrawing.id == task.drawing_id)
                )).scalar_one_or_none()
                if not drawing:
                    continue
                file_rec = (await db.execute(
                    select(UploadedFile).where(UploadedFile.id == drawing.file_id)
                )).scalar_one_or_none()
                if not file_rec:
                    continue

                try:
                    url = storage_service.get_presigned_download_url(file_rec.bucket, file_rec.object_key)
                    async with httpx.AsyncClient() as http:
                        resp = await http.get(url)
                        resp.raise_for_status()
                    ext = os.path.splitext(file_rec.original_name or ".jpg")[1] or ".jpg"
                    img_path = os.path.join(dataset_dir, "images", "train", f"{i:05d}{ext}")
                    with open(img_path, "wb") as f:
                        f.write(resp.content)

                    # YOLO label 파일 (placeholder — 실제는 bbox 좌표 필요)
                    parsed = task.corrected_parsed or task.original_parsed
                    label_lines = []
                    for obj in (parsed or {}).get("objects", []):
                        cls_id = class_map.get(obj.get("type", "cut"), 2)
                        label_lines.append(f"{cls_id} 0.5 0.5 0.1 0.1")
                    lbl_path = os.path.join(dataset_dir, "labels", "train", f"{i:05d}.txt")
                    with open(lbl_path, "w") as f:
                        f.write("\n".join(label_lines))
                except Exception:
                    continue

            # YOLO data.yaml
            names = ["hole", "bend", "cut", "weld", "slot"]
            yaml_path = os.path.join(dataset_dir, "data.yaml")
            with open(yaml_path, "w") as f:
                f.write(f"train: {os.path.join(dataset_dir, 'images', 'train')}\n")
                f.write(f"val: {os.path.join(dataset_dir, 'images', 'train')}\n")
                f.write(f"nc: {len(names)}\n")
                f.write(f"names: {names}\n")

            # MLflow 설정
            mlflow_run_id = None
            try:
                import mlflow
                mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
                mlflow.set_experiment("cad-yolo")
                with mlflow.start_run() as run:
                    mlflow_run_id = run.info.run_id
                    mlflow.log_params({
                        "model_version": job.model_version,
                        "epochs": job.epochs,
                        "batch_size": job.batch_size,
                        "img_size": job.img_size,
                    })

                    # YOLO 학습
                    from ultralytics import YOLO
                    model = YOLO(f"{job.model_version}.pt")
                    results = model.train(
                        data=yaml_path,
                        epochs=job.epochs,
                        batch=job.batch_size,
                        imgsz=job.img_size,
                        project=tmp_dir,
                        name="train",
                        verbose=False,
                    )

                    train_map50 = float(results.results_dict.get("metrics/mAP50(B)", 0.0))
                    val_map50 = float(results.results_dict.get("metrics/mAP50(B)", 0.0))

                    mlflow.log_metrics({"train_map50": train_map50, "val_map50": val_map50})

                    # best.pt → MinIO 업로드
                    best_pt = os.path.join(tmp_dir, "train", "weights", "best.pt")
                    if os.path.exists(best_pt):
                        s3_path = f"models/yolo/{job_id}/best.pt"
                        storage_service.client.fput_object(
                            settings.MINIO_BUCKET, s3_path, best_pt
                        )
                        job.model_s3_path = s3_path

                    job.train_map50 = train_map50
                    job.val_map50 = val_map50
                    job.mlflow_run_id = mlflow_run_id
                    job.status = "completed"
                    job.completed_at = datetime.utcnow()
            except Exception as exc:
                job.status = "failed"
                job.error_message = str(exc)
                job.mlflow_run_id = mlflow_run_id

            await db.commit()

        except Exception as exc:
            job.status = "failed"
            job.error_message = str(exc)
            await db.commit()
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


async def _run_build_dataset(dataset_id: str) -> None:
    """데이터셋 상태를 ready로 업데이트 (실제 MinIO 업로드는 학습 시점에 수행)"""
    import uuid
    from datetime import datetime
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.models.annotation import AnnotationDataset

    async with AsyncSessionLocal() as db:
        dataset = (await db.execute(
            select(AnnotationDataset).where(AnnotationDataset.id == uuid.UUID(dataset_id))
        )).scalar_one_or_none()
        if dataset:
            dataset.status = "ready"
            dataset.built_at = datetime.utcnow()
            await db.commit()
