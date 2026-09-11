# 独立下载实例

- NAS 项目目录：`/volume1/docker/common-downloader`
- 内网访问：`http://192.168.80.208:8001`
- 下载根目录：`/volume3/9kg/common`，挂载到 `/data/downloads`
- 容器：`common-downloader-web`，使用 host 网络
- Celery 队列：`common-downloads`，与原服务的 `celery` 队列隔离
- `.env` 从原运行容器继承密钥和解析配置，不纳入源码或打包文件。
- 本次为现有功能的独立副本，仍保留原服务的作品命名、Season 1 子目录及元数据规则。
- 外网反代由用户自行配置；原服务的端口、数据目录及容器保持不变。

在 NAS 项目目录运行 `docker compose up -d --build` 可更新本实例。
