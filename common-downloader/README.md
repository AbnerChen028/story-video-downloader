# 通用下载器

这是主项目中的独立通用下载器实例，页面通过 `APP_MODE=general` 显示通用下载器文案，不影响绘本实例。

## NAS 参数

```text
项目目录：/volume1/docker/common-downloader
下载目录：/volume3/9kg/common
内网地址：http://NAS_IP:8001
容器名称：common-downloader-web
网络模式：host
Celery 队列：common-downloads
```

```bash
cd /volume1/docker/common-downloader
docker compose up -d --build
curl http://127.0.0.1:8001/api/health
```

外网访问请在 Lucky 或其他反向代理中将域名转发到 `http://NAS_IP:8001`。

## 支持平台

支持小红书、抖音、快手、YouTube 和 X。可以直接粘贴完整分享文案；系统会提取其中的链接并识别平台。X 平台优先使用公开元数据接口获取正文、封面和 MP4 地址。

## 配置

`.env` 由部署环境提供，不应提交到 Git。常用变量包括：

- `AUTH_KEY`：网页访问密钥
- `DEEPSEEK_API_KEY`：可选的大模型标题识别密钥
- `QSY_PARSE_KEY`：可选的第三方解析 Key
- `REDIS_URL`：Celery Broker/Backend

下载记录按文件修改时间倒序排列，每页默认显示 12 条。下载完成后会进行 MP4 完整性校验。
