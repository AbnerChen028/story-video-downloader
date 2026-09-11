"""视频数据模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class VideoInfo(BaseModel):
    """单个视频信息"""
    id: str
    title: str
    description: str = ""
    url: str
    thumbnail: str = ""
    duration: int = 0  # seconds
    author: str = ""
    platform: str  # youtube, xiaohongshu, douyin, kuaishou
    source_url: str = ""  # 原始页面链接
    published_at: Optional[datetime] = None


class SearchResult(BaseModel):
    """搜索返回结果"""
    query: str
    platform: str
    videos: list[VideoInfo] = []


class DownloadTask(BaseModel):
    """下载任务"""
    task_id: str
    video_title: str
    story_name: str  # 绘本名称（文件夹名）
    platform: str
    url: str
    status: str = "pending"  # pending, downloading, completed, failed
    progress: int = 0  # 0-100
    file_path: str = ""
    error: str = ""
    created_at: datetime = datetime.now()
