"""应用配置"""

import os
from pathlib import Path


class Settings:
    DOWNLOAD_BASE_PATH: Path = Path(os.getenv("DOWNLOAD_BASE_PATH", "/data/downloads"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "")
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    QSY_PARSE_API_URL: str = os.getenv("QSY_PARSE_API_URL", "https://a.jiejing.fun/parse")
    QSY_PARSE_KEY: str = os.getenv("QSY_PARSE_KEY", "")
    QSY_PARSE_TYPE: str = os.getenv("QSY_PARSE_TYPE", "sd")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MAX_CONCURRENT_DOWNLOADS: int = 3
    PREFERRED_FORMAT: str = "mp4"

    # 访问密钥
    AUTH_KEY: str = os.getenv("AUTH_KEY", "123456")
    APP_MODE: str = os.getenv("APP_MODE", "storybook")


settings = Settings()
