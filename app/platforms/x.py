"""X 平台：通过公开的 FxTwitter 元数据接口解析视频。"""
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import httpx

from app.models.video import VideoInfo
from app.platforms.douyin import DouYinPlatform


class XPlatform:
    @staticmethod
    def _status_id(url: str) -> str:
        match = re.search(r"/(?:status|statuses)/(\d+)", url)
        return match.group(1) if match else ""

    async def search(self, query: str, max_results: int = 10) -> list[VideoInfo]:
        return []

    @staticmethod
    async def resolve_url(url: str) -> Optional[dict]:
        status_id = XPlatform._status_id(url)
        if status_id:
            try:
                async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                    response = await client.get(f"https://api.fxtwitter.com/status/{status_id}")
                    response.raise_for_status()
                    tweet = response.json().get("tweet", {})
                media = tweet.get("media", {}).get("all", [])
                videos = [item for item in media if item.get("type") == "video"]
                if videos:
                    video = max(videos, key=lambda item: item.get("duration", 0))
                    formats = [item for item in video.get("formats", []) if item.get("container") == "mp4"]
                    download_url = max(formats, key=lambda item: item.get("bitrate", 0)).get("url") if formats else video.get("url", "")
                    if download_url:
                        return {
                            "title": tweet.get("text", "") or tweet.get("author", {}).get("name", "X"),
                            "description": tweet.get("text", ""),
                            "thumbnail": video.get("thumbnail_url", ""),
                            "duration": video.get("duration", 0),
                            "ext": "mp4",
                            "webpage_url": tweet.get("url", url),
                            "download_url": download_url,
                            "download_headers": {"Referer": "https://x.com/", "User-Agent": "Mozilla/5.0"},
                        }
            except (httpx.HTTPError, ValueError, TypeError, KeyError):
                pass
        return await DouYinPlatform._resolve_with_qsy(url)

    @staticmethod
    async def download(url: str, output_dir: Path, filename: str) -> Optional[Path]:
        parsed = await XPlatform.resolve_url(url)
        if not parsed or not parsed.get("download_url"):
            return None
        target = output_dir / f"{filename}.mp4"
        try:
            request = urllib.request.Request(parsed["download_url"], headers=parsed.get("download_headers", {}))
            with urllib.request.urlopen(request, timeout=300) as response, target.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            return target if target.exists() and target.stat().st_size > 0 else None
        except (OSError, urllib.error.URLError):
            if target.exists():
                target.unlink()
            return None
