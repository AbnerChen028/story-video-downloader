"""FastAPI 应用入口"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from app.api.search import router as search_router
from app.api.download import router as download_router
from app.api.tasks import router as tasks_router
from app.auth import auth_router

app = FastAPI(
    title="绘本视频搜索下载服务",
    description="搜索并下载小红书、抖音、快手、YouTube 等平台的绘本视频",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 路由
app.include_router(auth_router)  # 认证（无需前缀）
app.include_router(search_router, prefix="/api")
app.include_router(download_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")

@app.get("/api/health")
async def health_check():
    is_general = settings.APP_MODE == "general"
    return {
        "status": "ok",
        "download_path": str(settings.DOWNLOAD_BASE_PATH),
        "app_mode": settings.APP_MODE,
        "app_title": "通用下载器" if is_general else "绘本视频下载",
        "app_description": "下载各平台视频并整理到本地" if is_general else "下载绘本视频并整理成 Emby 剧集",
    }

FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}

@app.get("/")
async def serve_index():
    return FileResponse(FRONTEND_DIR / "index.html", headers=NO_CACHE_HEADERS)

@app.get("/style.css")
async def serve_css():
    return FileResponse(FRONTEND_DIR / "style.css", headers=NO_CACHE_HEADERS, media_type="text/css")

@app.get("/script.js")
async def serve_js():
    return FileResponse(FRONTEND_DIR / "script.js", headers=NO_CACHE_HEADERS, media_type="application/javascript")
