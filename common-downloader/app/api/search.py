"""搜索 API - 分享链接解析与平台识别"""
import json
import re
import subprocess
import httpx
from fastapi import APIRouter, Query, Body
from app.platforms import YouTubePlatform, XiaoHongShuPlatform, DouYinPlatform, KuaiShouPlatform, XPlatform
from app.models.video import SearchResult
from backend.config import settings

router = APIRouter(tags=["search"])

youtube = YouTubePlatform()


_KNOWN_PLATFORMS = {
    "xiaohongshu": ["xiaohongshu.com", "xhslink.com", "xhslink.cn"],
    "douyin": ["douyin.com", "iesdouyin.com"],
    "kuaishou": ["kuaishou.com", "gifshow.com"],
    "youtube": ["youtube.com", "youtu.be"],
    "x": ["x.com", "twitter.com"],
}


def detect_platform(url: str) -> str:
    """从 URL 自动识别平台"""
    url_lower = url.lower()
    for platform, domains in _KNOWN_PLATFORMS.items():
        for domain in domains:
            if domain in url_lower:
                return platform
    return "unknown"


KNOWN_STORY_NAMES = (
    "好饿的毛毛虫", "爱吃水果的牛", "爱吃水果的鳄鱼", "鳄鱼怕怕 牙医怕怕",
    "鸭子骑车记", "乘着火车去旅行", "挖红薯巴士", "蜗牛出租车", "骑自行车的鳄鱼",
)


def infer_story_name(title: str = "", raw_text: str = "") -> str:
    """从平台标题或分享文案提取绘本名，避免把整段分享文案当作品名。"""
    source = f"{title} {raw_text}"
    quoted = re.search(r"《([^》]{1,40})》", source)
    if quoted:
        return quoted.group(1).strip()
    for name in KNOWN_STORY_NAMES:
        if name in source:
            return name

    topic = re.search(r"#([^#\[\] ]{2,40})", source)
    if topic:
        return topic.group(1).strip()
    labeled = re.search(r"(?:绘本动画|绘本故事|亲子绘本动画)\s*[｜|:：-]\s*([^，。！？!！\n]{2,30})", source)
    if labeled:
        return labeled.group(1).strip()
    candidate = title.strip()
    candidate = candidate.rsplit("/", 1)[-1]
    candidate = candidate.replace(".mp4", "").replace(".webm", "").replace(".mov", "")
    candidate = candidate.split("|", 1)[0].split("｜", 1)[0].strip()
    for prefix in ("儿童绘本", "绘本故事", "故事动画"):
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix):].lstrip(" -：:")
    if candidate and len(candidate) <= 40 and not candidate.startswith(("分享", "推荐", "这本绘本")):
        return candidate
    return ""


def resolve_generic_metadata(url: str) -> dict:
    """用 yt-dlp 统一兜底解析平台标题。"""
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-single-json", "--no-warnings", "--skip-download", url],
            capture_output=True, text=True, timeout=35,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout)
            return {
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "thumbnail": data.get("thumbnail", ""),
                "duration": data.get("duration", 0),
                "webpage_url": data.get("webpage_url", url),
            }
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        pass
    return {}


async def resolve_with_deepseek(raw_text: str, url: str, title: str, description: str) -> dict:
    """让 DeepSeek 从分享文案和平台元数据中提取平台与绘本名。"""
    if not settings.DEEPSEEK_API_KEY:
        return {}
    prompt = f"""请分析下面的视频分享内容，返回严格 JSON，不要 Markdown：
{{"platform":"xiaohongshu|douyin|kuaishou|youtube|unknown","story_name":"绘本或作品名称","description":"一句话简介"}}

分享原文：{raw_text[:4000]}
链接：{url}
平台标题：{title[:500]}
平台描述：{description[:2000]}

规则：story_name 只填作品名，不要填分享文案、作者、出版社、平台名或话题；如果文本中有《书名》，优先使用书名。"""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                settings.DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions",
                headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"},
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": "你是视频分享信息提取器，只输出合法 JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            platform = data.get("platform", "unknown")
            if platform not in _KNOWN_PLATFORMS:
                platform = "unknown"
            return {
                "platform": platform,
                "story_name": str(data.get("story_name", "")).strip(),
                "description": str(data.get("description", "")).strip(),
            }
    except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return {}


@router.get("/search")
async def search_videos(
    query: str = Query(..., description="绘本名称"),
    max_results: int = Query(10, description="最大结果数"),
):
    """搜索绘本视频 - 仅自动搜索 YouTube，其他平台通过链接提交"""
    youtube_results = []
    try:
        youtube_results = await youtube.search(query, max_results)
    except Exception as e:
        print(f"YouTube 搜索失败: {e}")

    search_results = [
        SearchResult(query=query, platform="youtube", videos=youtube_results),
    ]

    return {"results": search_results}


@router.post("/search/link")
async def search_by_link(
    url: str = Body(..., embed=True),
    platform: str = Body("", embed=True),
    story_name: str = Body("", embed=True),
    raw_text: str = Body("", embed=True),
):
    """通过分享链接解析视频信息（自动识别平台）"""
    if not url:
        return {"error": "请提供视频链接"}

    # 自动识别平台
    detected = detect_platform(url)
    res = {"platform": detected, "url": url, "story_name": story_name, "title": "", "thumbnail": "", "webpage_url": url}

    # 用 yt-dlp 预解析链接获取真实信息
    try:
        if detected == "xiaohongshu":
            meta = await XiaoHongShuPlatform.resolve_url(url)
        elif detected == "douyin":
            meta = await DouYinPlatform.resolve_url(url)
        elif detected == "kuaishou":
            meta = await KuaiShouPlatform.resolve_url(url)
        elif detected == "x":
            meta = await XPlatform.resolve_url(url)
        else:
            meta = None

        if not meta:
            meta = resolve_generic_metadata(url)
        if meta:
            res["title"] = meta.get("title", "")
            res["thumbnail"] = meta.get("thumbnail", "")
            res["webpage_url"] = meta.get("webpage_url", url)
            res["download_url"] = meta.get("download_url", "")
            res["download_headers"] = meta.get("download_headers", {})
            res["duration"] = meta.get("duration", 0)
            res["description"] = meta.get("description", "")
            res["status"] = "resolved"
        else:
            res["status"] = "link_received"
    except Exception as e:
        res["status"] = "link_received"

    ai_info = await resolve_with_deepseek(
        raw_text, url, res["title"], res.get("description", "")
    )
    ai_platform = ai_info.get("platform", "unknown")
    if ai_platform != "unknown":
        res["platform"] = ai_platform
    res["story_name"] = story_name or ai_info.get("story_name") or infer_story_name(
        res["title"], f"{res.get('description', '')} {raw_text}"
    )
    if ai_info.get("description"):
        res["story_description"] = ai_info["description"]

    return res
