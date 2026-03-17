"""ORM-модели AI-анализа, найденных объектов и review-действий."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, JSON, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.enums import AIDetectionStatus, AIDetectionDecision, AIDetectionReviewAction


class AIDetection(Base):
    """Одна сессия анализа медиа.

    Представляет процесс AI-анализа одного медиафайла (фото или видео).
    Для статичного изображения обычно создается одна запись, для видео -
    может быть несколько детекций по разным кадрам или временным интервалам.

    Хранит статус выполнения анализа, технические детали в JSON-поле raw
    (warnings, progress, embeddings, ошибки) и временные метки.

    Attributes:
        id (int): Уникальный идентификатор детекции.
        media_id (int): ID анализируемого медиафайла.
        status (AIDetectionStatus): Текущий статус анализа (PENDING, IN_PROGRESS, DONE, FAILED).
        raw (dict | None): Технические детали анализа в JSON-формате.
        created_at (datetime): Время создания записи анализа.
        completed_at (datetime | None): Время завершения анализа.

    Relationships:
        media: Связанный медиафайл.
        objects: Найденные объекты в этом анализе.
        reviews: Действия review пользователей по этому анализу.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id"), nullable=False)
    status: Mapped[AIDetectionStatus] = mapped_column(
        Enum(AIDetectionStatus, values_callable=lambda x: [e.value for e in x]),
        default=AIDetectionStatus.PENDING,
    )
    # `raw` хранит технические детали анализа: warnings, progress, embeddings и ошибки.
    raw: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    media = relationship("Media")
    objects = relationship("AIDetectionObject", back_populates="detection")
    reviews = relationship("AIDetectionReview", back_populates="detection")


class AIDetectionObject(Base):
    """Один найденный объект внутри детекции.

    Хранит информацию об отдельном распознанном объекте в медиафайле:
    метку класса (label), уверенность модели (confidence), bounding box,
    предложенную AI локацию и итоговое решение пользователя после review.

    Attributes:
        id (int): Уникальный идентификатор объекта.
        detection_id (int): ID родительской детекции.
        label (str): Метка распознанного объекта (например, "bottle", "book").
        confidence (float): Уверенность модели в распознавании (0.0-1.0).
        bbox (dict | None): Координаты bounding box в формате {"x1": float, "y1": float, "x2": float, "y2": float}.
        suggested_location_id (int | None): ID локации, предложенной AI.
        decision (AIDetectionDecision): Решение пользователя (PENDING, ACCEPT, REJECT, MANUAL).
        decided_by (int | None): ID пользователя, принявшего решение.
        decided_at (datetime | None): Время принятия решения.
        linked_item_id (int | None): ID предмета, к которому привязан объект после review.
        linked_location_id (int | None): ID локации, к которой привязан объект после review.
        created_at (datetime): Время создания записи.

    Relationships:
        detection: Родительская детекция.
        candidates: Кандидаты для сопоставления с предметами.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("aidetection.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 3))
    bbox: Mapped[dict | None] = mapped_column(JSON)
    suggested_location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"))
    decision: Mapped[AIDetectionDecision] = mapped_column(
        Enum(AIDetectionDecision, values_callable=lambda x: [e.value for e in x]),
        default=AIDetectionDecision.PENDING,
        nullable=False,
    )
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # linked_* — итоговые привязки после ручного подтверждения в AI Review.
    linked_item_id: Mapped[int | None] = mapped_column(ForeignKey("item.id"), nullable=True)
    linked_location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    detection = relationship("AIDetection", back_populates="objects")
    candidates = relationship("AIDetectionCandidate", back_populates="detection_object")
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("aidetection.id"), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 3))
    bbox: Mapped[dict | None] = mapped_column(JSON)
    suggested_location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"))
    decision: Mapped[AIDetectionDecision] = mapped_column(
        Enum(AIDetectionDecision, values_callable=lambda x: [e.value for e in x]),
        default=AIDetectionDecision.PENDING,
        nullable=False,
    )
    decided_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # linked_* — итоговые привязки после ручного подтверждения в AI Review.
    linked_item_id: Mapped[int | None] = mapped_column(ForeignKey("item.id"), nullable=True)
    linked_location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    detection = relationship("AIDetection", back_populates="objects")
    candidates = relationship("AIDetectionCandidate", back_populates="detection_object")


class AIDetectionCandidate(Base):
    """Кандидат привязки объекта к предмету с вычисленным score.

    Хранит возможные соответствия между распознанным AI объектом и существующими
    предметами в базе данных. Каждый кандидат имеет score схожести (0.0-1.0),
    вычисленный на основе embeddings или других метрик.

    Attributes:
        id (int): Уникальный идентификатор кандидата.
        detection_object_id (int): ID объекта детекции.
        item_id (int): ID кандидата-предмета.
        score (float): Степень схожести (0.0-1.0, где 1.0 - идеальное совпадение).
        created_at (datetime): Время создания кандидата.

    Relationships:
        detection_object: Связанный объект детекции.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    detection_object_id: Mapped[int] = mapped_column(ForeignKey("aidetectionobject.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    detection_object = relationship("AIDetectionObject", back_populates="candidates")
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    detection_object_id: Mapped[int] = mapped_column(ForeignKey("aidetectionobject.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    detection_object = relationship("AIDetectionObject", back_populates="candidates")


class AIDetectionReview(Base):
    """Аудит-лог пользовательских действий в AI Review.

    Записывает все действия пользователя по взаимодействию с результатами AI-анализа:
    подтверждение распознаваний, отклонение, ручная привязка и т.д.
    Используется для аудита изменений и истории review-процесса.

    Attributes:
        id (int): Уникальный идентификатор записи review.
        detection_id (int): ID детекции, к которой относится действие.
        user_id (int | None): ID пользователя, выполнившего действие.
        action (AIDetectionReviewAction): Тип действия (ACCEPT, REJECT, MANUAL_LINK и т.д.).
        payload (dict | None): Дополнительные данные действия в JSON-формате.
        created_at (datetime): Время выполнения действия.

    Relationships:
        detection: Связанная детекция.
    """
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("aidetection.id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    action: Mapped[AIDetectionReviewAction] = mapped_column(
        Enum(AIDetectionReviewAction, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    detection = relationship("AIDetection", back_populates="reviews")
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("aidetection.id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    action: Mapped[AIDetectionReviewAction] = mapped_column(
        Enum(AIDetectionReviewAction, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    detection = relationship("AIDetection", back_populates="reviews")
