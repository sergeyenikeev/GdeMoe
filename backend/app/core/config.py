from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "ГдеМоё API"
    api_v1_prefix: str = "/api/v1"

    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str = "gdemoe"
    postgres_user: str = "gdemoe"
    postgres_password: str = "gdemoe"

    redis_url: str | None = None

    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expires_minutes: int = 60 * 24 * 7

    media_public_path: str = "/data/gdemo/public_media"
    media_private_path: str = "/data/gdemo/private_media"

    ai_service_url: str | None = None  # URL внешнего AI-сервиса (опционально)

    @computed_field
    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


settings = Settings()
