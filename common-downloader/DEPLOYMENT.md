# 部署说明

通用下载器可以使用独立目录、端口和 Celery 队列与绘本实例并行运行。

## 建议配置

- 项目目录：`/path/to/common-downloader`
- 宿主机媒体目录：设置为 `.env` 中的 `MEDIA_PATH`
- 内网端口：`8001`
- 容器名称：`common-downloader-web`
- Celery 队列：`common-downloads`
- Redis：通过 `REDIS_URL` 指向可访问的 Redis 实例

```bash
cp .env.example .env
# 设置 AUTH_KEY、MEDIA_PATH、REDIS_URL
docker compose up -d --build
```

如果需要外网访问，请通过带身份验证的反向代理转发，并保留应用自身的 `AUTH_KEY`。
