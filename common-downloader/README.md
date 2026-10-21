# Common Downloader

主项目中用于通用视频下载的独立实例。页面通过 `APP_MODE=general` 显示通用模式文案，支持小红书、抖音、快手、YouTube 和 X 的链接或分享文案。

## 启动

```bash
cp .env.example .env
# 编辑 .env，至少设置 AUTH_KEY、MEDIA_PATH 和 REDIS_URL
docker compose up -d --build
curl http://127.0.0.1:8001/api/health
```

当前 Compose 使用 host network，并通过独立端口 `8001` 和 Celery 队列 `common-downloads` 与绘本实例隔离。

## 说明

- 下载记录按文件修改时间倒序排列，每页默认显示 12 条。
- 下载完成后会确认文件存在，但暂不做媒体容器级完整性校验。
- 平台解析依赖第三方页面和服务，接口变化可能影响可用性。
- 不要把 `.env`、Cookie、API Key 或下载后的媒体文件提交到 Git。
