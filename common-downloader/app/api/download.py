"""下载 API"""
import uuid
from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import FileResponse
from app.core.download_manager import DownloadManager
from backend.celery_app import celery_app

router = APIRouter(tags=["download"])
download_manager = DownloadManager()


@router.post("/download")
async def start_download(
    video_url: str = Body(..., embed=True),
    story_name: str = Body(..., embed=True),
    platform: str = Body(..., embed=True),
    title: str = Body("", embed=True),
    thumbnail: str = Body("", embed=True),
):
    """开始下载视频"""
    if not video_url or not story_name:
        raise HTTPException(status_code=400, detail="video_url 和 story_name 必填")

    task_id = str(uuid.uuid4())

    celery_app.send_task(
        "backend.tasks.download_video_task",
        args=[task_id, video_url, story_name, platform, title, thumbnail],
        task_id=task_id,
    )

    return {"task_id": task_id, "status": "pending", "story_name": story_name}


@router.get("/download/list")
async def get_download_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
):
    """获取已下载的绘本列表"""
    stories = await download_manager.get_story_list()
    total = len(stories)
    start = (page - 1) * page_size
    return {
        "stories": stories[start:start + page_size],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/download/path")
async def get_download_path():
    """获取当前下载路径"""
    path = download_manager.get_download_path()
    return {"download_path": str(path)}


@router.get("/download/file")
async def preview_download(filename: str = Query(...)):
    """返回历史视频供浏览器预览"""
    requested = (download_manager.season_dir / filename).resolve()
    season_dir = download_manager.season_dir.resolve()
    if requested.parent != season_dir or requested.suffix.lower() != ".mp4":
        raise HTTPException(status_code=400, detail="无效的视频文件")
    if not requested.is_file():
        raise HTTPException(status_code=404, detail="视频不存在")
    return FileResponse(requested, media_type="video/mp4")


@router.delete("/download/file")
async def delete_download(filename: str = Query(...)):
    """删除历史视频及其同名 Emby 元数据"""
    requested = (download_manager.season_dir / filename).resolve()
    season_dir = download_manager.season_dir.resolve()
    if requested.parent != season_dir or requested.suffix.lower() != ".mp4":
        raise HTTPException(status_code=400, detail="无效的视频文件")
    if not requested.is_file():
        raise HTTPException(status_code=404, detail="视频不存在")
    requested.unlink()
    for extension in (".nfo", "-thumb.jpg"):
        sidecar = requested.with_suffix(extension) if extension == ".nfo" else requested.with_name(requested.stem + extension)
        if sidecar.exists():
            sidecar.unlink()
    return {"status": "deleted", "filename": filename}
