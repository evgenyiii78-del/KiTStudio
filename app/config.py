from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig", override=False)

def _path(name: str, default: str) -> Path:
    value = Path(os.getenv(name, default))
    return value if value.is_absolute() else BASE_DIR / value

@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip('"').strip("'")
    aitunnel_api_key: str = os.getenv("AITUNNEL_API_KEY", "").strip().strip('"').strip("'")
    aitunnel_base_url: str = os.getenv("AITUNNEL_BASE_URL", "https://api.aitunnel.ru/v1").strip().rstrip("/")
    chat_model: str = os.getenv("AITUNNEL_CHAT_MODEL", "openai/gpt-4.1-mini").strip()
    vision_model: str = os.getenv("AITUNNEL_VISION_MODEL", "openai/gpt-4.1-mini").strip()
    image_model: str = os.getenv("AITUNNEL_IMAGE_MODEL", "openai/gpt-image-2").strip()
    image_size: str = os.getenv("IMAGE_SIZE", "1024x1024").strip()
    image_quality: str = os.getenv("IMAGE_QUALITY", "medium").strip()
    database_path: Path = _path("DATABASE_PATH", "data/cakehub_bot.db")
    generated_dir: Path = _path("GENERATED_DIR", "data/generated")
    uploads_dir: Path = _path("UPLOADS_DIR", "data/uploads")
    history_limit: int = int(os.getenv("HISTORY_LIMIT", "20"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    bot_call_names: tuple[str, ...] = tuple(x.strip().lower() for x in os.getenv("BOT_CALL_NAMES", "кейкхаб,cakehub,кэйкхаб").split(",") if x.strip())

    def validate(self) -> None:
        missing = []
        if not self.telegram_bot_token: missing.append("TELEGRAM_BOT_TOKEN")
        if not self.aitunnel_api_key: missing.append("AITUNNEL_API_KEY")
        if missing:
            raise RuntimeError("Не настроены переменные: " + ", ".join(missing))

    def ensure_directories(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

settings = Settings()
