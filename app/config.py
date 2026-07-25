from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    telegram_bot_token: str
    github_token: str = ""
    github_models_endpoint: str = "https://models.github.ai/inference"
    github_models_api_version: str = "2026-03-10"
    github_chat_models: str = "openai/gpt-4.1-mini,openai/gpt-4o-mini"
    github_vision_models: str = "openai/gpt-4.1-mini,openai/gpt-4o-mini"
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
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

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
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.generated_dir).mkdir(parents=True, exist_ok=True)
        Path(self.uploads_dir).mkdir(parents=True, exist_ok=True)

settings = Settings()
