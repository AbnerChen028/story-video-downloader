# 视频分享下载服务

一个基于 FastAPI、Celery 和 Docker 的 NAS 网页下载器，包含绘本视频服务和通用下载器两个独立实例。

## 功能

- 支持小红书、抖音、快手、YouTube 和 X 分享文案
- 自动提取链接、识别平台、获取标题、简介和封面
- 支持网页预览、下载队列、实时进度、历史分页和删除
- 下载完成后校验 MP4，失败或不完整文件不会进入历史
- `APP_MODE=storybook` 显示绘本模式，`APP_MODE=general` 显示通用模式
- Docker 使用 host 网络，Celery + Redis 执行异步任务

## 目录结构

```text
story-video-search/
├── app/                  # API、平台适配器和下载管理
├── backend/              # FastAPI、Celery 和配置
├── frontend/             # HTML/CSS/JavaScript 页面
├── docker-compose.yml    # 绘本服务
└── common-downloader/    # 通用下载器独立副本
```

## NAS 部署

绘本服务：

```text
项目目录：/volume1/docker/story-video-search
宿主下载目录：/volume3/media/links/电视剧/儿童/儿童绘本
内网端口：8000
```

通用下载器：

```text
项目目录：/volume1/docker/common-downloader
宿主下载目录：/volume3/9kg/common
内网端口：8001
容器名称：common-downloader-web
Celery 队列：common-downloads
```

```bash
cp .env.example .env
# 至少设置 AUTH_KEY；不要把 .env 提交到 Git
docker compose up -d --build
curl http://127.0.0.1:8000/api/health
```

通用下载器的 `docker-compose.yml` 已使用端口 `8001` 和独立 Celery 队列。Lucky 或其他反代只需将域名转发到 `http://NAS_IP:8001`。

## 环境变量

| 变量 | 说明 |
|---|---|
| `AUTH_KEY` | 网页访问密钥，必须通过部署环境设置 |
| `APP_MODE` | `storybook` 或 `general`，控制页面模式和文案 |
| `DOWNLOAD_BASE_PATH` | 容器内下载根目录，通常为 `/data/downloads` |
| `REDIS_URL` | Celery Broker/Backend 地址 |
| `CELERY_QUEUE` | 任务队列名称，多个实例应保持不同 |
| `DEEPSEEK_API_KEY` | 可选，必须使用环境变量注入 |
| `QSY_PARSE_API_URL` | 抖音解析服务地址 |
| `QSY_PARSE_KEY` | 可选的解析服务 Key |
| `QSY_PARSE_TYPE` | 解析模式，默认 `sd` |
| `YOUTUBE_API_KEY` | 可选；不设置时使用 yt-dlp |

## Emby 文件结构

绘本服务默认生成电视节目结构：

```text
儿童绘本/
├── tvshow.nfo
└── Season 1/
    ├── season.nfo
    └── 儿童绘本 - S01E01 - 作品名.mp4
```

## API

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/health` | 健康检查和当前模式 |
| `GET` | `/api/search?query=绘本名` | 搜索结果 |
| `POST` | `/api/search/link` | 解析完整分享文案 |
| `POST` | `/api/download` | 创建异步下载任务 |
| `GET` | `/api/tasks/{task_id}` | 查询进度和错误 |
| `GET` | `/api/download/list?page=1&page_size=12` | 分页读取历史 |
| `GET` | `/api/download/file?filename=...` | 预览 MP4 |
| `DELETE` | `/api/download/file?filename=...` | 删除视频及 NFO |

## 安全与限制

- `.env`、Cookie、API Key 和下载媒体不应提交到 Git。
- 平台解析依赖第三方服务和平台页面结构，接口变化可能影响可用性。
- 请仅下载自己有权保存和使用的内容，并遵守各平台服务条款。
