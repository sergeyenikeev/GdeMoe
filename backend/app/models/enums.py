"""Справочные enum-значения, используемые в ORM и API."""

import enum


class ItemStatus(str, enum.Enum):
    """Состояние предмета."""
    NEW = "new"
    OK = "ok"
    BROKEN = "broken"
    LOST = "lost"
    REPAIRED = "repaired"
    SOLD = "sold"
    DISCARDED = "discarded"
    WANT = "want"
    IN_TRANSIT = "in_transit"
    NEEDS_REVIEW = "needs_review"


class LocationKind(str, enum.Enum):
    """Тип узла в дереве локаций."""
    HOME = "home"
    FLAT = "flat"
    ROOM = "room"
    CLOSET = "closet"
    SHELF = "shelf"
    BOX = "box"
    GARAGE = "garage"
    OTHER = "other"


class Scope(str, enum.Enum):
    """Область видимости данных."""
    PRIVATE = "private"
    PUBLIC = "public"
    GROUP = "group"


class TodoStatus(str, enum.Enum):
    """Статус задачи."""
    OPEN = "open"
    DONE = "done"


class MediaType(str, enum.Enum):
    """Тип загруженного медиа."""
    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"


class UploadStatus(str, enum.Enum):
    """Статус процесса загрузки файла."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class AIDetectionStatus(str, enum.Enum):
    """Статус AI-анализа."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"


class AIDetectionDecision(str, enum.Enum):
    """Решение по найденному объекту."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AIDetectionReviewAction(str, enum.Enum):
    """Тип действия пользователя в AI Review."""
    ACCEPT = "accept"
    REJECT = "reject"
    LINK = "link_existing"
    CREATE = "create_new"
    FIX_LOCATION = "fix_location"
