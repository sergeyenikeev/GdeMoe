"""Healthcheck-эндпоинты для сервиса и окружения."""

from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck() -> dict:
    """Быстрый liveness-check без доступа к зависимостям.

    Выполняет простую проверку доступности сервиса без подключения к внешним ресурсам.
    Возвращает фиксированный ответ "ok", что указывает на то, что приложение запущено
    и способно обрабатывать HTTP-запросы. Используется оркестраторами (Kubernetes, Docker)
    для проверки живости контейнера.

    Returns:
        dict: Словарь с ключом "status" и значением "ok".

    Raises:
        Нет исключений - функция всегда возвращает успешный ответ.
    """
    return {"status": "ok"}


@router.get("/health/full")
async def healthcheck_full(db: AsyncSession = Depends(get_db)) -> dict:
    """Проверяет БД, пути к медиа и наличие весов YOLO.

    Выполняет комплексную диагностику здоровья сервиса, проверяя:
    - Подключение к базе данных (выполняет простой SELECT 1)
    - Существование директорий для хранения медиафайлов (public и private)
    - Наличие файла весов YOLO для AI-функциональности

    Используется для мониторинга и отладки развертывания. Если какая-либо проверка
    fails, общий статус становится "degraded", но сервис продолжает работать.

    Args:
        db (AsyncSession): Асинхронная сессия базы данных для проверки подключения.

    Returns:
        dict: Словарь с общим статусом ("ok" или "degraded") и детальными результатами
              проверок в ключе "checks". Каждый check содержит "ok": bool и дополнительные
              поля с информацией или ошибкой.

    Raises:
        Нет исключений - все ошибки перехватываются и возвращаются в ответе.
    """
    checks: dict[str, dict] = {}

    # Проверка, что приложение вообще может открыть соединение с БД.
    try:
        await db.execute(text("select 1"))
        checks["db"] = {"ok": True}
    except Exception as exc:  # noqa: BLE001
        checks["db"] = {"ok": False, "error": str(exc)}

    # Проверка директорий, в которые backend должен сохранять файлы и превью.
    public_path = Path(settings.media_public_path)
    private_path = Path(settings.media_private_path)
    checks["media_paths"] = {
        "ok": public_path.exists() and private_path.exists(),
        "public_exists": public_path.exists(),
        "private_exists": private_path.exists(),
    }

    # Проверяем только наличие файла весов, не загружая модель в память.
    if settings.ai_yolo_weights_path:
        yolo_weights = Path(settings.ai_yolo_weights_path)
        if not yolo_weights.is_absolute():
            yolo_weights = Path.cwd() / yolo_weights
        source = "AI_YOLO_WEIGHTS_PATH"
    else:
        yolo_weights = Path.home() / ".cache" / "ultralytics" / "assets" / "yolov8n.pt"
        source = "default"
    checks["ai_weights"] = {"ok": yolo_weights.exists(), "path": str(yolo_weights), "source": source}

    overall = "ok" if all(c.get("ok") for c in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
    checks: dict[str, dict] = {}

    # Проверка, что приложение вообще может открыть соединение с БД.
    try:
        await db.execute(text("select 1"))
        checks["db"] = {"ok": True}
    except Exception as exc:  # noqa: BLE001
        checks["db"] = {"ok": False, "error": str(exc)}

    # Проверка директорий, в которые backend должен сохранять файлы и превью.
    public_path = Path(settings.media_public_path)
    private_path = Path(settings.media_private_path)
    checks["media_paths"] = {
        "ok": public_path.exists() and private_path.exists(),
        "public_exists": public_path.exists(),
        "private_exists": private_path.exists(),
    }

    # Проверяем только наличие файла весов, не загружая модель в память.
    if settings.ai_yolo_weights_path:
        yolo_weights = Path(settings.ai_yolo_weights_path)
        if not yolo_weights.is_absolute():
            yolo_weights = Path.cwd() / yolo_weights
        source = "AI_YOLO_WEIGHTS_PATH"
    else:
        yolo_weights = Path.home() / ".cache" / "ultralytics" / "assets" / "yolov8n.pt"
        source = "default"
    checks["ai_weights"] = {"ok": yolo_weights.exists(), "path": str(yolo_weights), "source": source}

    overall = "ok" if all(c.get("ok") for c in checks.values()) else "degraded"
    return {"status": overall, "checks": checks}
