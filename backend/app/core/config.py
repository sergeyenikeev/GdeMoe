"""Централизованные настройки backend.

Это основной файл, который стоит открыть, если нужно понять,
откуда берутся пути к медиа, настройки БД и параметры AI.
"""

from typing import List

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Набор runtime-настроек backend-приложения.

    Все настройки загружаются из переменных окружения (.env файла)
    с fallback на значения по умолчанию. Использует Pydantic для валидации
    типов и обязательности полей.

    Настройки разделены на группы:
    - Общие (project_name, api_v1_prefix)
    - База данных PostgreSQL (postgres_*)
    - Кэширование (redis_url)
    - Аутентификация JWT (jwt_*)
    - Медиафайлы (media_*)
    - AI и ML (ai_*)
    - Разработка (debug, cors_origins)

    Для изменения настроек в продакшене используйте переменные окружения
    или .env файл в корне проекта.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_name: str = "GdeMoe API"
    """Название проекта для API-документации."""

    api_v1_prefix: str = "/api/v1"
    """Префикс для всех эндпоинтов API версии 1."""

    postgres_host: str = "db"
    """Хост PostgreSQL сервера."""

    postgres_port: int = 5432
    """Порт PostgreSQL сервера."""

    postgres_db: str = "gdemoe"
    """Имя базы данных PostgreSQL."""

    postgres_user: str = "gdemoe"
    """Пользователь для подключения к PostgreSQL."""

    postgres_password: str = "gdemoe"
    """Пароль для подключения к PostgreSQL."""

    redis_url: str | None = None
    """URL для подключения к Redis (опционально, для кэширования)."""

    jwt_secret_key: str = "change-me"
    """Секретный ключ для подписи JWT-токенов. Должен быть изменён в продакшене."""

    jwt_algorithm: str = "HS256"
    """Алгоритм шифрования для JWT."""

    jwt_access_token_expires_minutes: int = 60 * 24 * 7
    """Время жизни access-токена в минутах (по умолчанию 7 дней)."""

    media_public_path: str = "/data/gdemo/public_media"
    """Путь к директории для публичных медиа-файлов."""

    media_private_path: str = "/data/gdemo/private_media"
    """Путь к директории для приватных медиа-файлов."""

    media_max_photo_size_bytes: int = 10 * 1024 * 1024
    """Максимальный размер фото в байтах (10 MB)."""

    media_max_video_size_bytes: int = 150 * 1024 * 1024
    """Максимальный размер видео в байтах (150 MB)."""

    media_allowed_mimes: List[str] = [
        "image/jpeg",
        "image/png",
        "image/heic",
        "video/mp4",
    ]
    """Список разрешённых MIME-типов для загрузки медиа."""

    video_frame_stride: int = 180
    """Шаг извлечения кадров из видео (каждый 180-й кадр)."""

    video_max_frames: int = 3
    """Максимальное количество кадров для извлечения из видео."""

    ai_service_url: str | None = None
    """URL внешнего AI-сервиса для распознавания (опционально)."""

    ai_yolo_weights_path: str | None = None
    """Путь к весам YOLO для локального AI-пайплайна (опционально)."""

    @computed_field
    @property
    def database_url(self) -> str:
        """Собирает DSN для async SQLAlchemy из env-переменных.

        Формирует строку подключения к базе данных на основе настроек PostgreSQL.
        Используется для создания async engine SQLAlchemy с драйвером asyncpg.

        Returns:
            str: Строка подключения в формате postgresql+asyncpg://user:pass@host:port/db
        """
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
