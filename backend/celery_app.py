"""Celery 异步任务队列"""
from celery import Celery
from backend.config import settings

celery_app = Celery(
    "story_video",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["backend.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
