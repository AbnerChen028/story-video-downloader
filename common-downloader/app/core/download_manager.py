"""下载管理器 - Emby TV Series 格式（儿童绘本/Season 1/S01E01-名称.mp4 + nfo）"""
import json
from pathlib import Path
from datetime import datetime
from typing import Optional
from app.models.video import VideoInfo
from backend.config import settings


class DownloadManager:
    def __init__(self):
        self.base_path = settings.DOWNLOAD_BASE_PATH  # 儿童绘本/
        self.season_dir = self.base_path / "Season 1"

    def ensure_dirs(self) -> Path:
        """确保 Season 1/ 目录存在"""
        self.season_dir.mkdir(parents=True, exist_ok=True)
        return self.season_dir

    def get_safe_filename(self, name: str) -> str:
        """生成安全的文件名字段"""
        safe = "".join(c for c in name if c.isalnum() or c in " _-（）()").strip()
        return safe or "未分类"

    def get_next_episode_number(self) -> int:
        """读取 Season 1/ 目录，计算下一个集号"""
        if not self.season_dir.exists():
            return 1
        max_ep = 0
        for f in self.season_dir.iterdir():
            if f.suffix == ".mp4":
                # 匹配 S01E{NUM}
                import re
                m = re.search(r'S01E(\d+)', f.stem)
                if m:
                    ep = int(m.group(1))
                    if ep > max_ep:
                        max_ep = ep
        return max_ep + 1

    def generate_filename(self, story_name: str, episode_num: int) -> str:
        """生成 Emby 风格文件名：儿童绘本 - S01E{nn} - {名称}"""
        safe_name = self.get_safe_filename(story_name)
        return f"儿童绘本 - S01E{episode_num:02d} - {safe_name}"

    def write_episode_nfo(self, file_stem: str, episode_num: int, title: str, plot: str = ""):
        """写入单集 nfo"""
        nfo_path = self.season_dir / f"{file_stem}.nfo"
        plot_escaped = plot.replace("]]>", "]]]]><![CDATA[")
        content = f"""<?xml version="1.0" encoding="utf-8"?>
<episodedetails>
  <title>{title}</title>
  <plot><![CDATA[{plot_escaped}]]></plot>
  <outline><![CDATA[{plot_escaped}]]></outline>
  <season>1</season>
  <episode>{episode_num}</episode>
  <rating>0</rating>
</episodedetails>
"""
        nfo_path.write_text(content, encoding="utf-8")

    def ensure_tvshow_nfo(self):
        """确保根目录 tvshow.nfo 存在"""
        nfo_path = self.base_path / "tvshow.nfo"
        if not nfo_path.exists():
            content = """<?xml version="1.0" encoding="utf-8"?>
<tvshow>
  <title>儿童绘本</title>
  <originaltitle>儿童绘本</originaltitle>
  <plot><![CDATA[儿童绘本故事视频合集，涵盖国内外经典绘本故事。]]></plot>
  <outline><![CDATA[儿童绘本故事视频合集]]></outline>
  <genre>儿童</genre>
  <genre>动画</genre>
  <premiered>2024-01-01</premiered>
  <year>2024</year>
  <rating>0</rating>
  <season>-1</season>
  <episode>-1</episode>
</tvshow>
"""
            nfo_path.write_text(content, encoding="utf-8")

    def ensure_season_nfo(self):
        """确保 Season 1/season.nfo 存在"""
        nfo_path = self.season_dir / "season.nfo"
        if not nfo_path.exists():
            content = """<?xml version="1.0" encoding="utf-8"?>
<season>
  <title>第 1 季</title>
  <plot><![CDATA[儿童绘本故事视频]]></plot>
  <outline><![CDATA[儿童绘本故事视频]]></outline>
  <premiered>2024-01-01</premiered>
  <year>2024</year>
  <seasonnumber>1</seasonnumber>
</season>
"""
            nfo_path.write_text(content, encoding="utf-8")

    async def save_metadata(self, story_name: str, video: VideoInfo, file_path: str):
        """保存元数据（用于前端展示）"""
        metadata_file = self.base_path / "metadata.json"
        metadata = {}
        if metadata_file.exists():
            try:
                metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        if story_name not in metadata:
            metadata[story_name] = {
                "name": story_name,
                "cover": "",
                "videos": [],
                "updated_at": datetime.now().isoformat(),
            }

        metadata[story_name]["videos"].append({
            "title": video.title,
            "platform": video.platform,
            "url": video.url,
            "file": file_path,
            "downloaded_at": datetime.now().isoformat(),
        })

        if not metadata[story_name]["cover"] and video.thumbnail:
            metadata[story_name]["cover"] = video.thumbnail

        metadata[story_name]["updated_at"] = datetime.now().isoformat()
        metadata_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    async def get_story_list(self) -> list[dict]:
        """获取已下载列表"""
        stories = []
        if not self.season_dir.exists():
            return stories

        files = sorted(
            (f for f in self.season_dir.iterdir() if f.suffix == ".mp4"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for f in files:
            # 解析名称
            import re
            m = re.search(r'S01E(\d+)\s*-\s*(.+)', f.stem)
            ep_num = int(m.group(1)) if m else 0
            name = m.group(2).strip() if m else f.stem

            # 查找对应的 nfo 获取更多信息
            nfo_path = self.season_dir / f"{f.stem}.nfo"
            cover = ""
            if nfo_path.exists():
                import xml.etree.ElementTree as ET
                try:
                    tree = ET.parse(str(nfo_path))
                    root = tree.getroot()
                    title_el = root.find("title")
                    if title_el is not None and title_el.text:
                        name = title_el.text
                except Exception:
                    pass

            stories.append({
                "name": name,
                "cover": cover,
                "video_count": 1,
                "episode": ep_num,
                "filename": f.name,
                "file": str(f),
                "updated_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })

        return stories

    def get_download_path(self) -> Path:
        return self.season_dir
