"""Маршруты для загрузки и выдачи медиа.

Этот файл отвечает не только за upload, но и за побочные задачи вокруг него:
нормализацию путей, генерацию превью, запуск анализа и запись истории загрузки.
"""

import hashlib
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, Literal

import aiofiles
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.core.config import settings
from app.models.ai import AIDetection, AIDetectionObject, AIDetectionStatus
from app.models.enums import MediaType, UploadStatus
from app.models.media import ItemMedia, Media, MediaUploadHistory
from app.schemas.media import MediaUploadHistoryOut
from app.services.ai.pipeline import analyze_media
from app.services.ai.video import analyze_video

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/media", tags=["media"])

SANITIZE_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_segment(segment: str, fallback: str) -> str:
    """Очищает сегмент пути от опасных символов для безопасного хранения файлов.

    Удаляет или заменяет символы, которые могут создать проблемы с файловой системой,
    такие как слеши, точки в начале (для скрытых файлов) и другие небезопасные символы.
    Если после очистки строка пустая, возвращает fallback.

    Args:
        segment (str): Исходный сегмент пути для очистки.
        fallback (str): Значение по умолчанию, если после очистки ничего не осталось.

    Returns:
        str: Очищенный сегмент пути, безопасный для использования в файловой системе.

    Raises:
        Нет исключений, всегда возвращает строку.
    """
    cleaned = SANITIZE_RE.sub("_", segment.strip())
    cleaned = cleaned.lstrip(".").strip("_")
    return cleaned or fallback


def _ensure_extension(filename: str, mime: str | None, media_type: str) -> str:
    """Добавляет расширение к имени файла, если оно отсутствует.

    Если имя файла уже содержит точку (расширение), возвращает как есть.
    Для изображений добавляет .jpg, если MIME-тип содержит 'jpeg'.
    Для других типов использует media_type для определения расширения.

    Args:
        filename (str): Исходное имя файла.
        mime (str | None): MIME-тип файла, если известен.
        media_type (str): Тип медиа (например, 'photo', 'video').

    Returns:
        str: Имя файла с расширением.

    Raises:
        Нет исключений, всегда возвращает строку.
    """
    name = os.path.basename(filename)
    if "." in name:
        return name
    if mime and "jpeg" in mime:
        return name + ".jpg"
    if mime and "png" in mime:
        return name + ".png"
    if mime and "heic" in mime:
        return name + ".heic"
    if media_type == "video":
        return name + ".mp4"
    return name + ".bin"


async def _write_file(target_path: Path, file: UploadFile, max_bytes: int) -> tuple[int, str]:
    """Пишет файл на диск потоково и параллельно считает SHA-256 хеш.

    Читает файл по частям, записывает на диск и обновляет хеш.
    Если размер превышает max_bytes, удаляет частично записанный файл и выбрасывает исключение.

    Args:
        target_path (Path): Путь, куда сохранить файл.
        file (UploadFile): Загруженный файл для записи.
        max_bytes (int): Максимальный разрешенный размер файла в байтах.

    Returns:
        tuple[int, str]: Кортеж из размера файла в байтах и SHA-256 хеша в hex-формате.

    Raises:
        HTTPException: Если размер файла превышает max_bytes.
    """
    sha = hashlib.sha256()
    total = 0
    async with aiofiles.open(target_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > max_bytes:
                await out.close()
                target_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File is too large")
            sha.update(chunk)
            await out.write(chunk)
    return total, sha.hexdigest()


def _make_image_thumb(src: Path, dest: Path) -> None:
    """Генерирует JPEG-превью для фото с максимальным размером 512×512.

    Создает миниатюру изображения, сохраняя пропорции, и сохраняет как JPEG.
    Директория назначения создается автоматически.

    Args:
        src (Path): Путь к исходному изображению.
        dest (Path): Путь для сохранения превью.

    Returns:
        None

    Raises:
        Нет исключений, ошибки игнорируются (превью не критично).
    """
    from PIL import Image

    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        img.thumbnail((512, 512))
        img.save(dest, format="JPEG")


def _make_video_thumb(src: Path, dest: Path) -> None:
    """Сохраняет первый кадр видео как миниатюру (требуется OpenCV).

    Извлекает первый кадр из видео и сохраняет как изображение.
    Если OpenCV недоступен или кадр не удалось прочитать, логирует предупреждение и пропускает.

    Args:
        src (Path): Путь к видеофайлу.
        dest (Path): Путь для сохранения превью.

    Returns:
        None

    Raises:
        Нет исключений, ошибки логируются и игнорируются.
    """
    try:
        import cv2  # noqa: WPS433
    except ImportError:
        logger.warning("cv2 not available; skip video thumb for %s", src)
        return
    cap = cv2.VideoCapture(str(src))
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        logger.warning("Cannot read first frame for thumb %s", src)
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(dest), frame)


async def _latest_detection(db: AsyncSession, media_id: int) -> tuple[AIDetection | None, list[AIDetectionObject]]:
    """Возвращает последнюю детекцию по медиа вместе с объектами и кандидатами.

    Выполняет запрос к базе данных для получения самой свежей AI-детекции для данного медиафайла,
    а также всех связанных объектов детекции с их кандидатами.

    Args:
        db (AsyncSession): Асинхронная сессия базы данных.
        media_id (int): ID медиафайла.

    Returns:
        tuple[AIDetection | None, list[AIDetectionObject]]: Кортеж из последней детекции (или None) и списка объектов.

    Raises:
        Нет исключений, возвращает None если детекция не найдена.
    """
    det_stmt = (
        select(AIDetection)
        .where(AIDetection.media_id == media_id)
        .order_by(AIDetection.id.desc())
        .limit(1)
    )
    det = (await db.execute(det_stmt)).scalar_one_or_none()
    objects: list[AIDetectionObject] = []
    if det:
        obj_stmt = (
            select(AIDetectionObject)
            .options(selectinload(AIDetectionObject.candidates))
            .where(AIDetectionObject.detection_id == det.id)
        )
        objects = (await db.execute(obj_stmt)).scalars().all()
    return det, list(objects)


def _serialize_detection(det: AIDetection | None, objects: Iterable[AIDetectionObject]) -> dict | None:
    """Формирует структуру анализа медиа для отдачи клиенту.

    Создает словарь с информацией о детекции, включая статус, подсказки и список объектов.
    Если детекция отсутствует, возвращает None.

    Args:
        det (AIDetection | None): Объект детекции или None.
        objects (Iterable[AIDetectionObject]): Итерируемый объект с объектами детекции.

    Returns:
        dict | None: Словарь с данными анализа или None если детекция не найдена.

    Raises:
        Нет исключений.
    """
    if not det:
        return None
    hint_items = None
    raw = getattr(det, "raw", None)
    if isinstance(raw, dict):
        hint_items = raw.get("hint_item_ids")
    return {
        "id": det.id,
        "status": det.status,
        "hint_item_ids": hint_items,
        "objects": [
            _serialize_detection_object(obj)
            for obj in objects
        ],
    }


def _serialize_media(m: Media, det: AIDetection | None, objects: Iterable[AIDetectionObject]) -> dict:
    """Собирает словарь метаданных медиа с привязкой к последней детекции.

    Формирует полный словарь с информацией о медиафайле, включая пути к файлу и превью,
    а также результаты AI-анализа.

    Args:
        m (Media): Объект медиа из базы данных.
        det (AIDetection | None): Последняя детекция или None.
        objects (Iterable[AIDetectionObject]): Объекты детекции.

    Returns:
        dict: Словарь с метаданными медиа и анализом.

    Raises:
        Нет исключений.
    """
    scope_prefix = "private/" if m.path.startswith("private/") else ""
    return {
        "id": m.id,
        "path": m.path,
        "mime_type": m.mime_type,
        "size_bytes": m.size_bytes,
        "file_hash": m.file_hash,
        "thumb_path": m.thumb_path,
        "file_url": f"/api/v1/media/file/{m.id}",
        "thumb_url": f"/api/v1/media/file/{m.id}?thumb=1" if m.thumb_path else None,
        "analysis": _serialize_detection(det, objects),
    }


def _serialize_detection_object(obj: AIDetectionObject) -> dict:
    """Составляет подробную информацию по объекту детекции с кандидатами.

    Формирует словарь с данными об обнаруженном объекте, включая bounding box,
    уверенность, решения и список кандидатов для сопоставления.

    Args:
        obj (AIDetectionObject): Объект детекции из базы данных.

    Returns:
        dict: Словарь с детальной информацией об объекте.

    Raises:
        Нет исключений.
    """
    return {
        "id": obj.id,
        "label": obj.label,
        "confidence": float(obj.confidence),
        "bbox": obj.bbox,
        "suggested_location_id": obj.suggested_location_id,
        "decision": obj.decision,
        "linked_item_id": obj.linked_item_id,
        "linked_location_id": obj.linked_location_id,
        "candidates": [
            {"item_id": c.item_id, "score": float(c.score)}
            for c in getattr(obj, "candidates", [])
        ],
    }


async def _create_upload_log(
    db: AsyncSession,
    workspace_id: int,
    owner_user_id: int,
    media_type: MediaType,
    source: str | None,
    location_id: int | None,
) -> MediaUploadHistory:
    """Создаёт запись истории сразу в статусе `in_progress`.

    Добавляет новую запись в таблицу истории загрузок с начальным статусом IN_PROGRESS,
    что позволяет отслеживать процесс загрузки и анализа.

    Args:
        db (AsyncSession): Асинхронная сессия базы данных.
        workspace_id (int): ID рабочего пространства.
        owner_user_id (int): ID пользователя-владельца.
        media_type (MediaType): Тип медиа (фото/видео).
        source (str | None): Источник загрузки (например, "upload").
        location_id (int | None): ID локации, если указана.

    Returns:
        MediaUploadHistory: Созданная запись истории загрузки.

    Raises:
        Нет исключений, но может возникнуть IntegrityError при дубликатах.
    """
    entry = MediaUploadHistory(
        workspace_id=workspace_id,
        owner_user_id=owner_user_id,
        location_id=location_id,
        media_type=media_type,
        status=UploadStatus.IN_PROGRESS,
        source=source or "upload",
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def _mark_upload_failed(db: AsyncSession, entry: MediaUploadHistory | None, error: str) -> None:
    """Отмечает загрузку как неудачную с указанием ошибки.

    Выполняет rollback транзакции и обновляет статус записи истории на FAILED,
    добавляя информацию об ошибке в ai_summary.

    Args:
        db (AsyncSession): Асинхронная сессия базы данных.
        entry (MediaUploadHistory | None): Запись истории загрузки или None.
        error (str): Описание ошибки.

    Returns:
        None

    Raises:
        Нет исключений, ошибки логируются.
    """
    if entry is None:
        return
    try:
        await db.rollback()
    except Exception:
        pass
    entry.status = UploadStatus.FAILED
    entry.ai_status = "failed"
    entry.ai_summary = {"error": error}
    db.add(entry)
    await db.commit()


def _validate_mime(mime: str | None, media_type: MediaType) -> str:
    """Проверяет mime и мягко исправляет частый кейс mobile capture.

    Валидирует MIME-тип на соответствие разрешенным, автоматически исправляет
    конфликты между media_type и MIME (например, фото с video MIME становится видео).
    Используется для обработки загрузок с мобильных устройств.

    Args:
        mime (str | None): MIME-тип файла.
        media_type (MediaType): Заявленный тип медиа.

    Returns:
        str: Нормализованный MIME-тип в нижнем регистре.

    Raises:
        HTTPException: Если MIME-тип не разрешен или конфликтует с media_type.
    """
    mime_lower = (mime or "").lower()
    if mime_lower and mime_lower not in [m.lower() for m in settings.media_allowed_mimes]:
        raise HTTPException(status_code=400, detail=f"Unsupported mime type: {mime_lower}")
    if mime_lower and media_type == MediaType.PHOTO and mime_lower.startswith("video/"):
        media_type = MediaType.VIDEO  # auto-correct to avoid conflicts from mobile capture
    if mime_lower and media_type == MediaType.VIDEO and not mime_lower.startswith("video/"):
        raise HTTPException(status_code=400, detail="media_type=video conflicts with mime_type")
    return mime_lower


def _parse_hint_item_ids(value: str | None) -> list[int]:
    """Разбирает список `hint_item_ids` из form-data в список чисел.

    Парсит строку с ID предметов, разделенных запятыми или точками с запятой,
    игнорируя некорректные значения.

    Args:
        value (str | None): Строка с ID через запятую или точку с запятой.

    Returns:
        list[int]: Список целых чисел ID предметов.

    Raises:
        Нет исключений, некорректные значения пропускаются.
    """
    if not value:
        return []
    parts = [p.strip() for p in value.replace(";", ",").split(",")]
    result: list[int] = []
    for part in parts:
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            continue
    return result


def _validate_video_params(frame_stride: int | None, max_frames: int | None) -> tuple[int | None, int | None]:
    """Проверяет параметры выборки кадров для видео-анализа.

    Валидирует параметры frame_stride и max_frames, обеспечивая что они положительные.

    Args:
        frame_stride (int | None): Шаг выборки кадров (каждый N-й кадр).
        max_frames (int | None): Максимальное количество кадров для анализа.

    Returns:
        tuple[int | None, int | None]: Кортеж валидированных параметров.

    Raises:
        HTTPException: Если параметры не положительные числа.
    """
    if frame_stride is not None and frame_stride <= 0:
        raise HTTPException(status_code=400, detail="video_frame_stride must be positive")
    if max_frames is not None and max_frames <= 0:
        raise HTTPException(status_code=400, detail="video_max_frames must be positive")
    return frame_stride, max_frames


@router.post("/upload")
async def upload_media(
    file: UploadFile = File(...),
    workspace_id: int = Form(2),
    owner_user_id: int = Form(1),
    media_type: str = Form("photo"),
    mime_type: str | None = Form(None),
    subdir: str = Form("inbox"),
    scope: Literal["public", "private"] = Form("public"),
    item_id: int | None = Form(None),
    location_id: int | None = Form(None),
    analyze: bool = Form(True),
    source: str | None = Form("upload"),
    client_created_at: str | None = Form(None),
    hint_item_ids: str | None = Form(None),
    video_frame_stride: int | None = Form(None),
    video_max_frames: int | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Основной upload-эндпоинт для загрузки медиафайлов.

    Выполняет полную последовательность загрузки: создание записи истории, валидацию,
    сохранение файла на диск, генерацию превью, создание записи Media в БД,
    привязку к предметам и опциональный запуск AI-анализа.

    Последовательность действий:
    1. Создание записи истории загрузки в статусе IN_PROGRESS
    2. Валидация MIME-типа и параметров
    3. Подготовка безопасного пути хранения файла
    4. Сохранение файла на диск с вычислением SHA-256 хеша
    5. Генерация превью (для фото/видео)
    6. Создание записи Media в базе данных
    7. Привязка к предмету (если указан item_id)
    8. Запуск AI-анализа (если analyze=True)
    9. Обновление истории загрузки с финальным статусом

    Args:
        file (UploadFile): Загружаемый файл.
        workspace_id (int): ID рабочего пространства (по умолчанию 2).
        owner_user_id (int): ID пользователя-владельца (по умолчанию 1).
        media_type (str): Тип медиа: "photo", "video", "document" (по умолчанию "photo").
        mime_type (str | None): MIME-тип файла, если известен.
        subdir (str): Поддиректория для хранения (по умолчанию "inbox").
        scope (Literal["public", "private"]): Область видимости файла (по умолчанию "public").
        item_id (int | None): ID предмета для привязки файла.
        location_id (int | None): ID локации для привязки файла.
        analyze (bool): Запускать ли AI-анализ после загрузки (по умолчанию True).
        source (str | None): Источник загрузки (по умолчанию "upload").
        client_created_at (str | None): Время создания на клиенте (не используется).
        hint_item_ids (str | None): Список ID предметов-подсказок для AI через запятую.
        video_frame_stride (int | None): Шаг выборки кадров для видео-анализа.
        video_max_frames (int | None): Максимальное количество кадров для видео.
        db (AsyncSession): Сессия базы данных.

    Returns:
        dict: Информация о загруженном медиафайле с ID, путем, размером, хешем и статусом анализа.

    Raises:
        HTTPException: При ошибках валидации (неподдерживаемый MIME, слишком большой файл и т.д.).
        Exception: При неожиданных ошибках (записываются в лог и историю).
    """
    try:
        media_type_enum = MediaType(media_type)
    except Exception:
        raise HTTPException(status_code=400, detail="Unsupported media_type; allowed: photo, video, document")
    upload_log: MediaUploadHistory | None = None
    try:
        upload_log = await _create_upload_log(
            db, workspace_id, owner_user_id, media_type_enum, source, location_id
        )
        mime_lower = _validate_mime(mime_type or file.content_type, media_type_enum)
        # Физическая структура хранения зависит от scope и владельца:
        # так проще разносить private/public и не смешивать загрузки.
        base = Path(settings.media_public_path if scope == "public" else settings.media_private_path)
        safe_workspace = _sanitize_segment(str(workspace_id), "workspace")
        safe_owner = _sanitize_segment(str(owner_user_id), "user")
        target_group = _sanitize_segment(subdir, "inbox") if not item_id else f"item_{item_id}"
        target_dir = base / safe_workspace / safe_owner / target_group / datetime.utcnow().strftime("%Y%m%d")
        target_dir.mkdir(parents=True, exist_ok=True)

        filename = file.filename or f"upload_{int(datetime.utcnow().timestamp())}"
        filename = _ensure_extension(filename, mime_lower or file.content_type, media_type)
        filename = _sanitize_segment(filename, f"upload.{media_type_enum.value}")
        target_path = target_dir / filename

        max_bytes = settings.media_max_photo_size_bytes if media_type_enum == MediaType.PHOTO else settings.media_max_video_size_bytes
        try:
            size_bytes, file_hash = await _write_file(target_path, file, max_bytes=max_bytes)
        finally:
            await file.close()

        rel_path = target_path.relative_to(base)
        rel_path_str = f"private/{rel_path}" if scope == "private" else str(rel_path)

        thumb_rel_path: str | None = None
        if media_type_enum in (MediaType.PHOTO, MediaType.VIDEO):
            # Превью не критично для upload: если оно не собралось,
            # сам файл всё равно считаем успешно загруженным.
            thumb_dir = base / "thumbs" / safe_workspace / safe_owner / target_group / target_dir.name
            thumb_name = f"{target_path.stem}.jpg"
            thumb_path = thumb_dir / thumb_name
            try:
                if media_type_enum == MediaType.PHOTO:
                    _make_image_thumb(target_path, thumb_path)
                else:
                    _make_video_thumb(target_path, thumb_path)
                if thumb_path.exists():
                    thumb_rel_path = thumb_path.relative_to(base)
                    thumb_rel_path = f"private/{thumb_rel_path}" if scope == "private" else str(thumb_rel_path)
                upload_log.thumb_path = thumb_rel_path
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to build thumbnail for %s: %s", target_path, exc)

        media = Media(
            workspace_id=workspace_id,
            owner_user_id=owner_user_id,
            location_id=location_id,
            media_type=media_type_enum,
            path=rel_path_str,
            mime_type=mime_type or file.content_type,
            size_bytes=size_bytes,
            file_hash=file_hash,
            thumb_path=thumb_rel_path,
        )
        db.add(media)
        await db.commit()
        await db.refresh(media)

        if item_id:
            existing = await db.execute(
                select(ItemMedia).where(ItemMedia.item_id == item_id, ItemMedia.media_id == media.id)
            )
            if not existing.scalar_one_or_none():
                db.add(ItemMedia(item_id=item_id, media_id=media.id))
                await db.commit()

        hint_items = _parse_hint_item_ids(hint_item_ids)
        analysis_status: dict | None = None
        if analyze:
            try:
                # Видео идёт через отдельный пайплайн с семплированием кадров,
                # фото и одиночные изображения — через обычный analyze_media.
                if media_type_enum == MediaType.VIDEO:
                    video_frame_stride, video_max_frames = _validate_video_params(
                        video_frame_stride, video_max_frames
                    )
                    detection_ids = await analyze_video(
                        media.id,
                        db,
                        frame_stride=video_frame_stride or settings.video_frame_stride,
                        max_frames=video_max_frames or settings.video_max_frames,
                        hint_item_ids=hint_items,
                    )
                    latest = None
                    if detection_ids:
                        latest = await db.get(AIDetection, detection_ids[-1])
                    analysis_status = {
                        "detection_ids": detection_ids,
                        "status": latest.status if latest else "done" if detection_ids else "pending",
                    }
                else:
                    det = await analyze_media(media.id, db, hint_item_ids=hint_items)
                    analysis_status = {"detection_id": det.id, "status": det.status}
            except Exception as exc:  # noqa: BLE001
                logger.exception("Analyze failed for media %s: %s", media.id, exc)
                db.add(AIDetection(media_id=media.id, status=AIDetectionStatus.FAILED, raw={"error": str(exc)}))
                await db.commit()
                analysis_status = {"status": "failed"}

        det, objects = await _latest_detection(db, media.id)
        upload_log.media_id = media.id
        upload_log.path = media.path
        upload_log.thumb_path = media.thumb_path or upload_log.thumb_path
        upload_log.status = UploadStatus.SUCCESS
        # История загрузки нужна mobile-клиенту как быстрый read-model:
        # он может показать статус AI без дополнительного похода по связанным таблицам.
        ai_status_value = (analysis_status or {}).get("status") or (det.status if det else None)
        if hasattr(ai_status_value, "value"):
            ai_status_value = ai_status_value.value
        upload_log.ai_status = ai_status_value
        upload_log.ai_summary = _serialize_detection(det, objects)
        upload_log.detection_id = det.id if det else None
        db.add(upload_log)
        await db.commit()

        logger.info(
            "media_upload",
            extra={
                "media_id": media.id,
                "source": source or "upload",
                "size_bytes": size_bytes,
                "mime": mime_type or file.content_type,
                "location_id": location_id,
                "item_id": item_id,
                "hint_item_ids": hint_items,
            },
        )

        return {
            "id": media.id,
            "path": media.path,
            "mime_type": media.mime_type,
            "size_bytes": media.size_bytes,
            "file_hash": media.file_hash,
            "thumb_path": media.thumb_path,
            "analysis": analysis_status,
        }
    except HTTPException as exc:
        logger.warning(
            "media.upload.failed status=%s detail=%s filename=%s workspace_id=%s owner_user_id=%s",
            exc.status_code,
            exc.detail if hasattr(exc, "detail") else str(exc),
            getattr(file, "filename", None),
            workspace_id,
            owner_user_id,
        )
        await _mark_upload_failed(db, upload_log, str(exc.detail if hasattr(exc, "detail") else exc))
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "media.upload.failed_unexpected filename=%s workspace_id=%s owner_user_id=%s",
            getattr(file, "filename", None),
            workspace_id,
            owner_user_id,
        )
        await _mark_upload_failed(db, upload_log, str(exc))
        raise


@router.get("/history", response_model=list[MediaUploadHistoryOut])
async def upload_history(
    owner_user_id: int | None = None,
    limit: int = 50,
    status: UploadStatus | None = None,
    source: str | None = None,
    location_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Возвращает журнал загрузок в удобном для mobile виде."""
    logger.info("media.history.list owner=%s limit=%s", owner_user_id, limit)
    stmt = select(MediaUploadHistory).order_by(MediaUploadHistory.created_at.desc()).limit(limit)
    if owner_user_id:
        stmt = stmt.where(MediaUploadHistory.owner_user_id == owner_user_id)
    if status:
        stmt = stmt.where(MediaUploadHistory.status == status)
    if source:
        stmt = stmt.where(MediaUploadHistory.source == source)
    if location_id:
        stmt = stmt.where(MediaUploadHistory.location_id == location_id)
    rows = (await db.execute(stmt)).scalars().all()
    result: list[MediaUploadHistoryOut] = []
    for entry in rows:
        det: AIDetection | None = None
        objects: list[AIDetectionObject] = []
        if entry.media_id:
            det, objects = await _latest_detection(db, entry.media_id)
        file_url = f"/api/v1/media/file/{entry.media_id}" if entry.media_id else None
        thumb_url = (
            f"/api/v1/media/file/{entry.media_id}?thumb=1"
            if entry.media_id and (entry.thumb_path or (det and det.media and det.media.thumb_path))
            else None
        )
        result.append(
            MediaUploadHistoryOut(
                id=entry.id,
                media_id=entry.media_id,
                workspace_id=entry.workspace_id,
                owner_user_id=entry.owner_user_id,
                location_id=entry.location_id,
                media_type=entry.media_type,
                status=entry.status,
                source=entry.source,
                ai_status=entry.ai_status,
                ai_summary=entry.ai_summary,
                path=entry.path,
                thumb_path=entry.thumb_path,
                file_url=file_url,
                thumb_url=thumb_url,
                detection_id=entry.detection_id or (det.id if det else None),
                objects=[_serialize_detection_object(obj) for obj in objects],
                created_at=entry.created_at,
            )
        )
    return result


@router.get("/recent")
async def recent_media(scope: str = "public", limit: int = 20, db: AsyncSession = Depends(get_db)):
    """Список последних медиа для быстрых превью и отладки."""
    stmt = (
        select(Media)
        .order_by(Media.id.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    result = []
    for m in rows:
        if scope == "public" and m.path.startswith("private/"):
            continue
        if scope == "private" and not m.path.startswith("private/"):
            continue
        det, objects = await _latest_detection(db, m.id)
        result.append(_serialize_media(m, det, objects))
    return result


@router.get("/file/{media_id}")
async def get_media_file(
    media_id: int,
    thumb: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Отдаёт оригинал или превью по id медиа."""
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    path_field = media.thumb_path if thumb else media.path
    scope = "private" if path_field and path_field.startswith("private/") else "public"
    base = Path(settings.media_private_path if scope == "private" else settings.media_public_path)
    rel_path = path_field or media.path
    rel = Path(rel_path.removeprefix("private/")) if scope == "private" else Path(rel_path)
    full_path = base / rel
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    media_type = "image/jpeg" if thumb else media.mime_type
    return FileResponse(full_path, media_type=media_type, filename=full_path.name)


@router.get("/{media_id}")
async def get_media(media_id: int, db: AsyncSession = Depends(get_db)):
    """Карточка одного медиа вместе с последним анализом."""
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    det, objects = await _latest_detection(db, media_id)
    return _serialize_media(media, det, objects)
