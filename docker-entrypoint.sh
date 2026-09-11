#!/bin/sh
# 同时启动 FastAPI 和 Celery Worker

# 启动 Celery Worker（后台）
celery -A backend.celery_app worker --loglevel=info --concurrency=2 -n worker@%h &

# 启动 FastAPI
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
