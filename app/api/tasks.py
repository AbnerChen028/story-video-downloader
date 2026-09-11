"""任务查询 API"""
from fastapi import APIRouter
from backend.celery_app import celery_app

router = APIRouter(tags=["tasks"])


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """查询下载任务状态"""
    result = celery_app.AsyncResult(task_id)
    task_meta = {}
    if result.info and isinstance(result.info, dict):
        task_meta = result.info

    response = {
        "task_id": task_id,
        "status": result.status,
        "progress": task_meta.get("progress", 0),
        "error": task_meta.get("error", ""),
        "file_path": task_meta.get("file_path", ""),
        "video_title": task_meta.get("video_title", ""),
    }

    if result.successful():
        response["result"] = result.result

    return response
