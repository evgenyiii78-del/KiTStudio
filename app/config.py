from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, default)
    return value.strip() if isinstance(value, str) else default


def _clean_token(value: str) -> str:
    token = (value or "").strip().strip('"').strip("'").strip()
    if token.lower().startswith("bot") and ":" in token:
        token = token[3:].strip()
    return token


def telegram_token_candidates() -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for source in ("BOT_TOKEN", "TELEGRAM_BOT_TOKEN"):
        token = _clean_token(_env(source))
        if token and token not in seen:
            result.append((source, token))
            seen.add(token)
    return result


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = _clean_token(_env("BOT_TOKEN")) or _clean_token(_env("TELEGRAM_BOT_TOKEN"))
    aitunnel_api_key: str = _env("AITUNNEL_API_KEY")
    aitunnel_base_url: str = _env("AITUNNEL_BASE_URL", "https://api.aitunnel.ru/v1").rstrip("/")

    image_model: str = "gpt-image-2"
    image_size: str = _env("AITUNNEL_IMAGE_SIZE", "1024x1024")
    image_quality: str = _env("AITUNNEL_IMAGE_QUALITY", "auto")
    image_output_format: str = _env("AITUNNEL_IMAGE_FORMAT", "png")

    database_path: str = _env("DATABASE_PATH", "/app/data/kitstudio.sqlite3")
    ai_timeout_seconds: int = _env_int("AI_TIMEOUT_SECONDS", 180)
    log_level: str = _env("LOG_LEVEL", "INFO")

    def validate(self) -> None:
        missing: list[str] = []
        if not telegram_token_candidates():
            missing.append("BOT_TOKEN/TELEGRAM_BOT_TOKEN")
        if not self.aitunnel_api_key:
            missing.append("AITUNNEL_API_KEY")
        if missing:
            raise RuntimeError("Не заданы обязательные переменные: " + ", ".join(missing))

    def ensure_directories(self) -> None:
        Path(self.database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
