from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    telegram_bot_token: str
    
    aitunnel_api_key: str = ""
    aitunnel_base_url: str = "https://api.aitunnel.ru/v1"
    aitunnel_image_model: str = "gpt-image-1-mini"
    image_size: str = "1024x1024"
    image_quality: str = "medium"
    database_path: str = "data/cakehub_bot.db"
    generated_dir: str = "data/generated"
    uploads_dir: str = "data/uploads"
    history_limit: int = 20
    max_queue_size: int = 20
    workers: int = 2
    log_level: str = "INFO"
    bot_names: str = "кейкхаб,cakehub,кейк хаб"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    @property
    def chat_models(self) -> list[str]:
        return [x.strip() for x in self.github_chat_models.split(",") if x.strip()]

    @property
    def vision_models(self) -> list[str]:
        return [x.strip() for x in self.github_vision_models.split(",") if x.strip()]

    @property
    def call_names(self) -> list[str]:
        return [x.strip().lower() for x in self.bot_names.split(",") if x.strip()]

    def ensure_dirs(self) -> None:
        def resolve_path(value: str) -> Path:
            path = Path(value)
            return path if path.is_absolute() else PROJECT_ROOT / path

        self.database_path = str(resolve_path(self.database_path))
        self.generated_dir = str(resolve_path(self.generated_dir))
        self.uploads_dir = str(resolve_path(self.uploads_dir))
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.generated_dir).mkdir(parents=True, exist_ok=True)
        Path(self.uploads_dir).mkdir(parents=True, exist_ok=True)

settings = Settings()
