FROM python:3.11-slim

WORKDIR /app

# 使用清华镜像源加速 apt 下载
RUN sed -i 's/deb.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    sed -i 's/security.debian.org/mirrors.tuna.tsinghua.edu.cn/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || true && \
    apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    procps \
    && rm -rf /var/lib/apt/lists/*

# 安装 yt-dlp
RUN curl -fsSL https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp \
    && chmod a+rx /usr/local/bin/yt-dlp

# 安装 Python 依赖
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制项目代码
COPY backend/ backend/
COPY app/ app/
COPY frontend/ frontend/
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh && mkdir -p /data/downloads

EXPOSE 8000
ENTRYPOINT ["/docker-entrypoint.sh"]
