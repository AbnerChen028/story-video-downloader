"""小红书 - 通过分享链接解析与下载"""
import re
import subprocess
import json
from pathlib import Path
from typing import Optional

from app.models.video import VideoInfo


class XiaoHongShuPlatform:
    """小红书平台 - 通过分享链接下载"""

    async def search(self, query: str, max_results: int = 10) -> list[VideoInfo]:
        return []

    @staticmethod
    async def resolve_url(url: str) -> Optional[dict]:
        """解析小红书分享链接，返回视频元信息"""
        try:
            result = subprocess.run(
                ["yt-dlp", "--dump-json", "--no-warnings", url],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip())
                return {
                    "title": data.get("title", ""),
                    "description": data.get("description", ""),
                    "thumbnail": data.get("thumbnail", ""),
                    "duration": data.get("duration", 0),
                    "ext": data.get("ext", "mp4"),
                    "webpage_url": data.get("webpage_url", url),
                }
        except:
            pass
        return None

    @staticmethod
    async def download(url: str, output_dir: Path, filename: str) -> Optional[Path]:
        """下载小红书视频"""
        output_template = output_dir / f"{filename}.%(ext)s"
        try:
            result = subprocess.run(
                ["yt-dlp", "-f", "best", "-o", str(output_template),
                 "--no-warnings", "--restrict-filenames", url],
                capture_output=True, text=True, timeout=300
            )

            if result.returncode != 0:
                return None
            mp4_path = output_dir / f"{filename}.mp4"
            if mp4_path.exists():
                return mp4_path

            for f in output_dir.glob(f"{filename}.*"):
                if f.suffix in (".mkv", ".webm"):
                    target = output_dir / f"{filename}.mp4"
                    converted = subprocess.run(["ffmpeg", "-y", "-i", str(f), "-c", "copy", str(target)],
                                               capture_output=True, timeout=120)
                    if converted.returncode == 0 and target.exists():
                        f.unlink()
                        return target
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None
