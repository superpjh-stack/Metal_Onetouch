"""Celery 애플리케이션 설정"""
import os

from celery import Celery

celery_app = Celery(
    "metal_onetouch",
    broker=os.getenv("REDIS_URL", "redis://redis:6379") + "/1",
    backend=os.getenv("REDIS_URL", "redis://redis:6379") + "/2",
    include=["app.tasks.ai_agent", "app.tasks.cad_tasks", "app.tasks.dxf_tasks", "app.tasks.training_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    task_routes={
        "app.tasks.ai_agent.*":       {"queue": "ai_agent_queue"},
        "app.tasks.cad_tasks.*":      {"queue": "cad_queue"},
        "app.tasks.dxf_tasks.*":      {"queue": "cad_queue"},
        "app.tasks.training_tasks.*": {"queue": "train_queue"},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
