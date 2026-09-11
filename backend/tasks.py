"""Celery 异步下载任务"""
import asyncio
import subprocess
from pathlib import Path
from celery import Task
from backend.celery_app import celery_app
from backend.config import settings
from app.core.download_manager import DownloadManager
from app.platforms.youtube import YouTubePlatform
from app.platforms.xiaohongshu import XiaoHongShuPlatform
from app.platforms.douyin import DouYinPlatform
from app.platforms.kuaishou import KuaiShouPlatform
from app.platforms.x import XPlatform

download_manager = DownloadManager()

PLATFORM_DOWNLOADERS = {
    "youtube": YouTubePlatform.download,
    "xiaohongshu": XiaoHongShuPlatform.download,
    "douyin": DouYinPlatform.download,
    "kuaishou": KuaiShouPlatform.download,
    "x": XPlatform.download,
}


class DownloadTask(Task):
    def __init__(self):
        super().__init__()

    def update_progress(self, task_id, progress, **kwargs):
        self.update_state(
            state="PROGRESS",
            meta={"progress": progress, **kwargs}
        )


@celery_app.task(bind=True, base=DownloadTask, max_retries=3, default_retry_delay=60)
def download_video_task(self, task_id: str, video_url: str, story_name: str,
                        platform: str, title: str = "", thumbnail: str = ""):
    """异步下载视频任务"""
    try:
        self.update_progress(task_id, 0, video_title=title, status="starting")

        # 1. 确保目录结构存在
        season_dir = download_manager.ensure_dirs()

        # 2. 确保 tvshow.nfo / season.nfo
        download_manager.ensure_tvshow_nfo()
        download_manager.ensure_season_nfo()

        # 3. 计算下一集编号
        episode_num = download_manager.get_next_episode_number()

        # 4. 生成文件名：儿童绘本 - S01E{nn} - {名称}.mp4
        filename = download_manager.generate_filename(story_name, episode_num)

        self.update_progress(task_id, 30, video_title=title, status="downloading")

        # 5. 下载
        downloader = PLATFORM_DOWNLOADERS.get(platform)
        result_path = None
        if downloader:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result_path = loop.run_until_complete(
                    downloader(video_url, season_dir, filename)
                )
            finally:
                loop.close()
        else:
            output_template = season_dir / f"{filename}.%(ext)s"
            download_result = subprocess.run(
                ["yt-dlp", "-f", "best[ext=mp4]/best", "-o", str(output_template),
                 "--no-warnings", video_url],
                capture_output=True, text=True, timeout=600
            )
            if download_result.returncode != 0:
                raise Exception(download_result.stderr[-500:] or "下载命令失败")
            for f in season_dir.iterdir():
                if f.stem == filename and f.suffix in (".mp4", ".mkv", ".webm"):
                    result_path = f
                    break

        if result_path and result_path.exists():
            self.update_progress(task_id, 80, video_title=title, status="saving_metadata")

            # 6. 写出单集 nfo
            display_title = title or story_name
            download_manager.write_episode_nfo(result_path.stem, episode_num, story_name)

            self.update_progress(task_id, 100, video_title=title, status="completed",
                                 file_path=str(result_path))

            return {
                "status": "completed",
                "file_path": str(result_path),
                "story_name": story_name,
                "episode": episode_num,
            }
        else:
            raise Exception("下载文件未找到")

    except Exception as exc:
        self.update_progress(task_id, 0, video_title=title, status="failed",
                             error=str(exc))
        raise self.retry(exc=exc)
