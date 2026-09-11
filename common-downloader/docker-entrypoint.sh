#!/bin/sh
# 同时启动 FastAPI 和 Celery Worker

# 启动 Celery Worker（后台）
celery -A backend.celery_app worker --loglevel=info --concurrency=2 -Q "${CELERY_QUEUE:-common-downloads}" -n common-worker@%h &

# 启动 FastAPI
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8001}"
