from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, JSON, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.enums import AIDetectionStatus, AIDetectionDecision, AIDetectionReviewAction


class AIDetection(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id"), nullable=False)
    status: Mapped[AIDetectionStatus] = mapped_column(
        Enum(AIDetectionStatus, values_callable=lambda x: [e.value for e in x]),
        default=AIDetectionStatus.PENDING,
    )
    raw: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    media = relationship("Media")
    objects = relationship("AIDetectionObject", back_populates="detection")
    reviews = relationship("AIDetectionReview", back_populates="detection")


class AIDetectionObject(Base):
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    detection = relationship("AIDetection", back_populates="objects")
    candidates = relationship("AIDetectionCandidate", back_populates="detection_object")


class AIDetectionCandidate(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    detection_object_id: Mapped[int] = mapped_column(ForeignKey("aidetectionobject.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(5, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    detection_object = relationship("AIDetectionObject", back_populates="candidates")


class AIDetectionReview(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("aidetection.id"), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    action: Mapped[AIDetectionReviewAction] = mapped_column(
        Enum(AIDetectionReviewAction, values_callable=lambda x: [e.value for e in x]), nullable=False
    )
    payload: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    detection = relationship("AIDetection", back_populates="reviews")
