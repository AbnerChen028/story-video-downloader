# 儿童绘本视频搜索下载服务

搜索并下载小红书、YouTube、抖音、快手等平台的绘本相关视频，存入 NAS 指定目录供 Emby 媒体库展示。

## 目录结构

```
story-video-search/
├── docker-compose.yml      # Docker 编排
├── Dockerfile              # 容器构建
├── backend/                # Python 后端
│   ├── main.py             # FastAPI 入口
│   ├── config.py           # 配置
│   ├── celery_app.py       # Celery 异步队列
│   ├── tasks.py            # 下载任务
│   └── requirements.txt    # Python 依赖
├── app/                    # 业务逻辑
│   ├── api/                # API 路由
│   │   ├── search.py       # 搜索接口
│   │   ├── download.py     # 下载接口
│   │   └── tasks.py        # 任务状态接口
│   ├── core/               # 核心模块
│   │   └── download_manager.py  # 下载管理器
│   ├── platforms/          # 各平台实现
│   │   ├── youtube.py      # YouTube
│   │   ├── xiaohongshu.py  # 小红书
│   │   ├── douyin.py       # 抖音
│   │   └── kuaishou.py     # 快手
│   └── models/             # 数据模型
├── frontend/               # 前端页面
│   ├── index.html
│   ├── style.css
│   └── script.js
├── config/                 # 持久化配置
└── .env.example            # 环境变量示例
```

## 下载目录结构

下载的视频会按绘本名称自动创建文件夹：

```
/volume3/media/links/电视剧/儿童剧/儿童绘本/
├── 大卫不可以/
│   ├── cover.jpg
│   ├── metadata.json
│   ├── youtube_大卫不可以_xxx.mp4
│   └── xiaohongshu_大卫不可以_xxx.mp4
├── 好饿的毛毛虫/
│   └── ...
└── metadata.json           # 全局索引（供前端展示）
```

## 部署步骤

### 1. 克隆项目到 NAS

```bash
# 在 NAS 上执行
git clone <本项目地址> /path/to/story-video-search
cd /path/to/story-video-search
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 YouTube API Key（可选）
```

### 3. 启动服务

```bash
docker compose up -d
```

### 4. Lucky 反代配置

在 Lucky 后台添加反向代理规则：

- **服务名称**: 绘本搜索
- **目标地址**: `http://localhost:8000`
- **域名**: `story.your-domain.com`
- **WebSocket 支持**: 开启

### 5. Emby 配置

- Emby 中添加媒体库 → 类型选「其他视频」
- 路径：`/volume3/media/links/电视剧/儿童剧/儿童绘本/`
- Emby 会自动识别文件夹和封面

## API 接口

| 接口 | 方法 | 说明 |
|---|---|---|
| `/api/search?query=绘本名` | GET | 搜索各平台视频 |
| `/api/download` | POST | 提交下载任务 |
| `/api/tasks/{task_id}` | GET | 查询下载进度 |
| `/api/download/list` | GET | 已下载绘本列表 |
| `/api/download/path` | GET | 查看下载路径 |
| `/api/health` | GET | 健康检查 |

## 技术栈

- **后端**: Python FastAPI
- **前端**: 原生 HTML + CSS + JS
- **任务队列**: Celery + Redis
- **下载引擎**: yt-dlp + Playwright (小红书)
- **部署**: Docker Compose
- **反代**: Lucky
