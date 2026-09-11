"""X 平台：通过公开的 FxTwitter 元数据接口解析视频。"""
import asyncio
import json
import logging
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

import httpx

from app.models.video import VideoInfo
from app.platforms.douyin import DouYinPlatform

logger = logging.getLogger(__name__)


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
    async def download(url: str, output_dir: Path, filename: str, progress_callback=None) -> Optional[Path]:
        try:
            return await asyncio.wait_for(
                XPlatform._download(url, output_dir, filename, progress_callback), timeout=900
            )
        except asyncio.TimeoutError as exc:
            raise RuntimeError("X 视频下载超过 15 分钟，请稍后重试") from exc

    @staticmethod
    async def _download(url: str, output_dir: Path, filename: str, progress_callback) -> Path:
        if progress_callback:
            progress_callback(0, 0, "resolving")
        parsed = await XPlatform.resolve_url(url)
        if not parsed or not parsed.get("download_url"):
            raise RuntimeError("X 视频解析失败，未取得可下载的视频地址")
        target = output_dir / f"{filename}.mp4"
        downloaded = 0
        total = 0
        try:
            with tempfile.TemporaryDirectory(prefix=".x-download-", dir=output_dir) as temp_dir:
                partial = Path(temp_dir) / "video.part"
                headers = {**parsed.get("download_headers", {}), "Accept-Encoding": "identity"}
                if progress_callback:
                    progress_callback(0, 0, "connecting")
                async with httpx.AsyncClient(timeout=httpx.Timeout(30, connect=15), follow_redirects=True) as client:
                    async with client.stream("GET", parsed["download_url"], headers=headers) as response:
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "").lower()
                        if "text/" in content_type or "json" in content_type or "image/" in content_type:
                            raise RuntimeError("X 返回的内容不是视频，未保存到下载历史")
                        total = int(response.headers.get("content-length", "0"))
                        last_update = 0
                        with partial.open("wb") as output:
                            async for chunk in response.aiter_raw():
                                output.write(chunk)
                                downloaded += len(chunk)
                                now = time.monotonic()
                                if progress_callback and now - last_update >= 1:
                                    progress_callback(downloaded, total, "downloading")
                                    last_update = now
                if not downloaded or (total and total != downloaded):
                    raise RuntimeError(f"X 视频传输不完整：收到 {downloaded} 字节，预期 {total} 字节")
                if progress_callback:
                    progress_callback(downloaded, total, "verifying")
                probe = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type:format=duration,format_name",
                     "-of", "json", str(partial)], capture_output=True, text=True, timeout=30,
                )
                if probe.returncode != 0:
                    raise RuntimeError("X 视频校验失败，未保存到下载历史")
                metadata = json.loads(probe.stdout)
                actual_duration = float(metadata.get("format", {}).get("duration", 0))
                if not any(stream.get("codec_type") == "video" for stream in metadata.get("streams", [])) or actual_duration <= 0:
                    raise RuntimeError("X 下载内容没有有效视频轨道")
                if "mp4" not in metadata.get("format", {}).get("format_name", ""):
                    raise RuntimeError("X 下载内容不是 MP4 格式")
                expected_duration = float(parsed.get("duration") or 0)
                if expected_duration and actual_duration + max(2, expected_duration * 0.02) < expected_duration:
                    raise RuntimeError("X 视频时长不完整，未保存到下载历史")
                os.link(partial, target)
            logger.info("X download completed: bytes=%s duration=%.1fs", downloaded, actual_duration)
            return target
        except httpx.TimeoutException as exc:
            logger.warning("X download timed out after %s bytes", downloaded)
            raise RuntimeError(f"X 视频连接或传输超时（已接收 {downloaded // 1024} KB），将自动重试") from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"X 视频服务器返回 HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError("X 视频传输失败，请检查网络连接") from exc
