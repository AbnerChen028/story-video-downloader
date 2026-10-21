# Story Video Search

面向 NAS 和 Emby 用户的自托管视频下载与整理工具。粘贴分享文案或链接后，服务会识别平台、获取视频元数据、创建异步下载任务，并把完成的视频整理成 Emby 可识别的剧集目录。

A self-hosted video downloader for NAS and Emby users. It extracts links from share text, queues downloads, and writes Emby-compatible metadata.

> 项目阶段：早期版本。目前主要在个人 NAS 环境中使用，平台解析依赖第三方页面和服务，接口变化可能导致暂时失效。

## 功能

- 从小红书、抖音、快手、YouTube 和 X 的分享文案中提取链接
- 识别平台，获取标题、简介和封面
- 使用 Celery 和 Redis 异步下载，显示任务进度
- 下载历史分页、视频预览和本地删除
- 生成 Emby 使用的 `tvshow.nfo`、`season.nfo` 和单集 NFO
- 通过 `APP_MODE` 提供 `storybook` 和 `general` 两种页面模式

## 快速开始

运行环境需要 Docker、Docker Compose、可访问的 Redis，以及一个可写的媒体目录。当前 Compose 配置使用 Linux/NAS 的 host network。

```bash
cp .env.example .env
# 编辑 .env，至少设置 AUTH_KEY、MEDIA_PATH 和 REDIS_URL
docker compose up -d --build
curl http://127.0.0.1:8000/api/health
```

访问 `http://NAS_IP:8000`，使用 `.env` 中的 `AUTH_KEY` 登录。

## 配置

| 变量 | 说明 |
|---|---|
| `AUTH_KEY` | 网页访问密钥，必须设置为随机值 |
| `MEDIA_PATH` | 宿主机媒体目录，Compose 会挂载到容器内 |
| `DOWNLOAD_BASE_PATH` | 容器内下载根目录，默认 `/data/downloads` |
| `REDIS_URL` | Celery Broker/Backend 地址 |
| `APP_MODE` | `storybook` 或 `general` |
| `YOUTUBE_API_KEY` | 可选；未设置时使用 yt-dlp 搜索 |
| `DEEPSEEK_API_KEY` | 可选；用于从分享文案提取作品名 |
| `QSY_PARSE_API_URL` | 可选；抖音解析服务地址 |
| `QSY_PARSE_KEY` | 可选；解析服务密钥 |

不要把 `.env`、Cookie、API Key 或下载后的媒体文件提交到 Git。

## Emby 目录

绘本模式默认生成以下结构：

```text
儿童绘本/
├── tvshow.nfo
└── Season 1/
    ├── season.nfo
    ├── 儿童绘本 - S01E01 - 作品名.mp4
    └── 儿童绘本 - S01E01 - 作品名.nfo
```

## 主要接口

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/health` | 健康检查和当前模式 |
| `POST` | `/api/search/link` | 解析分享链接或分享文案 |
| `POST` | `/api/download` | 创建下载任务 |
| `GET` | `/api/tasks/{task_id}` | 查询任务进度 |
| `GET` | `/api/download/list` | 分页读取下载历史 |
| `GET` | `/api/download/file?filename=...` | 预览视频 |

## 已知限制

- 平台页面、短链接和解析服务变化后，相关适配器可能需要更新。
- 下载完成检查目前只确认文件存在，尚未做媒体容器级完整性校验。
- 当前还没有覆盖平台适配器和任务失败分支的自动化测试。
- 建议部署在可信内网或带身份验证的反向代理后，不要直接暴露到公网。

## License

[MIT](LICENSE)
