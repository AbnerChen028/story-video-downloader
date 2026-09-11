"""YouTube 搜索与下载"""
import re
import json
import subprocess
from pathlib import Path
from typing import Optional
import httpx
from app.models.video import VideoInfo
from backend.config import settings


class YouTubePlatform:
    """YouTube 平台搜索与下载"""

    def __init__(self):
        self.api_key = settings.YOUTUBE_API_KEY
        self.base_url = "https://www.googleapis.com/youtube/v3"

    async def search(self, query: str, max_results: int = 10) -> list[VideoInfo]:
        """搜索 YouTube 视频"""
        videos = []

        if self.api_key:
            # 使用官方 API
            async with httpx.AsyncClient() as client:
                params = {
                    "part": "snippet",
                    "q": f"{query} 绘本 儿童",
                    "maxResults": max_results,
                    "type": "video",
                    "key": self.api_key,
                }
                resp = await client.get(f"{self.base_url}/search", params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("items", []):
                        vid = item["id"]["videoId"]
                        snippet = item["snippet"]
                        videos.append(VideoInfo(
                            id=vid,
                            title=snippet["title"],
                            description=snippet["description"][:200],
                            url=f"https://www.youtube.com/watch?v={vid}",
                            thumbnail=snippet["thumbnails"]["high"]["url"],
                            author=snippet["channelTitle"],
                            platform="youtube",
                            source_url=f"https://www.youtube.com/watch?v={vid}",
                            published_at=snippet.get("publishedAt"),
                        ))
        else:
            # 无 API Key 时使用 yt-dlp 搜索
            videos = await self._search_via_ytdlp(query, max_results)

        return videos

    async def _search_via_ytdlp(self, query: str, max_results: int = 10) -> list[VideoInfo]:
        """使用 yt-dlp 搜索（不需要 API Key）"""
        videos = []
        try:
            result = subprocess.run(
                ["yt-dlp", "--dump-json", "--flat-playlist",
                 f"ytsearch{max_results}:{query} 绘本 儿童",
                 "--no-warnings"],
                capture_output=True, text=True, timeout=30
            )
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                data = json.loads(line)
                videos.append(VideoInfo(
                    id=data.get("id", ""),
                    title=data.get("title", ""),
                    description=data.get("description", "")[:200],
                    url=f"https://www.youtube.com/watch?v={data.get('id', '')}",
                    thumbnail=data.get("thumbnail", ""),
                    author=data.get("channel", data.get("uploader", "")),
                    platform="youtube",
                    source_url=f"https://www.youtube.com/watch?v={data.get('id', '')}",
                ))
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            print(f"YouTube yt-dlp search error: {e}")

        return videos

    @staticmethod
    async def download(url: str, output_dir: Path, filename: str) -> Optional[Path]:
        """下载 YouTube 视频到指定目录"""
        output_path = output_dir / f"{filename}.%(ext)s"
        try:
            result = subprocess.run(
                ["yt-dlp",
                 "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                 "-o", str(output_path),
                 "--no-warnings",
                 "--no-playlist",
                 url],
                capture_output=True, text=True, timeout=600
            )
            if result.returncode != 0:
                return None
            for f in output_dir.iterdir():
                if f.stem == filename and f.suffix in (".mp4", ".mkv", ".webm"):
                    # 统一转为 mp4
                    return f
        except subprocess.TimeoutExpired:
            print(f"YouTube download timeout: {url}")
        except FileNotFoundError:
            print("yt-dlp not found")
        return None
