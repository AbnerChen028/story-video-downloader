"""抖音 - 通过分享链接解析与下载"""
import subprocess
import json
import httpx
import urllib.request
from pathlib import Path
from typing import Optional
from app.models.video import VideoInfo
from backend.config import settings


class DouYinPlatform:
    """抖音平台 - 通过分享链接下载"""

    async def search(self, query: str, max_results: int = 10) -> list[VideoInfo]:
        return []

    @staticmethod
    async def resolve_url(url: str) -> Optional[dict]:
        parsed = await DouYinPlatform._resolve_with_qsy(url)
        if parsed:
            return parsed
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
    async def _resolve_with_qsy(url: str) -> Optional[dict]:
        payload = {"url": url, "type": settings.QSY_PARSE_TYPE}
        if settings.QSY_PARSE_KEY:
            payload["key"] = settings.QSY_PARSE_KEY
        try:
            async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
                response = await client.post(
                    settings.QSY_PARSE_API_URL,
                    json=payload,
                    headers={"Accept": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
            if data.get("code") != 0:
                return None
            body = data.get("body") or {}
            urls = data.get("urls") or body.get("urls") or []
            if not urls:
                return None
            return {
                "title": body.get("title", ""),
                "description": body.get("title", ""),
                "thumbnail": body.get("cover_url", ""),
                "duration": 0,
                "ext": "mp4",
                "webpage_url": body.get("url", url),
                "download_url": urls[0],
                "download_headers": {
                    key: data[key]
                    for key in ("Referer", "User-Agent", "Accept")
                    if data.get(key)
                },
            }
        except (httpx.HTTPError, ValueError, TypeError):
            return None

    @staticmethod
    async def download(url: str, output_dir: Path, filename: str) -> Optional[Path]:
        """下载抖音视频"""
        output_template = output_dir / f"{filename}.%(ext)s"
        try:
            parsed = await DouYinPlatform._resolve_with_qsy(url)
            if parsed and parsed.get("download_url"):
                request = urllib.request.Request(
                    parsed["download_url"], headers=parsed.get("download_headers", {})
                )
                with urllib.request.urlopen(request, timeout=300) as response:
                    with (output_dir / f"{filename}.mp4").open("wb") as target:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            target.write(chunk)
                result = output_dir / f"{filename}.mp4"
                if result.exists() and result.stat().st_size > 0:
                    return result
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
