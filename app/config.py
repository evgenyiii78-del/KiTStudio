from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = _env("TELEGRAM_BOT_TOKEN") or _env("BOT_TOKEN")
    aitunnel_api_key: str = _env("AITUNNEL_API_KEY")
    aitunnel_base_url: str = _env("AITUNNEL_BASE_URL", "https://api.aitunnel.ru/v1").rstrip("/")

    chat_model: str = _env("AITUNNEL_CHAT_MODEL", "auto")
    vision_model: str = _env("AITUNNEL_VISION_MODEL", "auto")
    image_model: str = _env("AITUNNEL_IMAGE_MODEL", "gpt-image-1")
    image_size: str = _env("AITUNNEL_IMAGE_SIZE", "1024x1024")
    image_quality: str = _env("AITUNNEL_IMAGE_QUALITY", "auto")
    image_output_format: str = _env("AITUNNEL_IMAGE_FORMAT", "png")

    database_path: str = _env("DATABASE_PATH", "data/cakehub.sqlite3")
    history_limit: int = _env_int("HISTORY_LIMIT", 16)
    max_output_tokens: int = _env_int("MAX_OUTPUT_TOKENS", 2500)
    ai_timeout_seconds: int = _env_int("AI_TIMEOUT_SECONDS", 180)
    log_level: str = _env("LOG_LEVEL", "INFO")
    group_trigger_name: str = _env("GROUP_TRIGGER_NAME", "кейкхаб").lower()

    def validate(self) -> None:
        missing: list[str] = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.aitunnel_api_key:
            missing.append("AITUNNEL_API_KEY")
        if missing:
            raise RuntimeError("Не заданы обязательные переменные: " + ", ".join(missing))
        if self.history_limit < 2:
            raise RuntimeError("HISTORY_LIMIT должен быть >= 2")

    def ensure_directories(self) -> None:
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
