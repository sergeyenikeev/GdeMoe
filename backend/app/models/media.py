from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Numeric, func, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.enums import MediaType, UploadStatus


class Media(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspace.id"), nullable=False)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"))
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, values_callable=lambda x: [e.value for e in x])
    )
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    thumb_path: Mapped[str | None] = mapped_column(String(1024))
    mime_type: Mapped[str | None] = mapped_column(String(128))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    file_hash: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    items = relationship("ItemMedia", back_populates="media")


class ItemMedia(Base):
    __tablename__ = "item_media"

    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), primary_key=True)
    media_id: Mapped[int] = mapped_column(ForeignKey("media.id"), primary_key=True)

    item = relationship("Item", back_populates="media_links")
    media = relationship("Media", back_populates="items")


class MediaUploadHistory(Base):
    __tablename__ = "mediauploadhistory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    media_id: Mapped[int | None] = mapped_column(ForeignKey("media.id"), nullable=True)
    detection_id: Mapped[int | None] = mapped_column(ForeignKey("aidetection.id"), nullable=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspace.id"), nullable=False)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"), nullable=True)
    media_type: Mapped[MediaType] = mapped_column(
        Enum(MediaType, values_callable=lambda x: [e.value for e in x])
    )
    status: Mapped[UploadStatus] = mapped_column(
        Enum(UploadStatus, values_callable=lambda x: [e.value for e in x]),
        default=UploadStatus.PENDING,
    )
    source: Mapped[str | None] = mapped_column(String(128))
    ai_status: Mapped[str | None] = mapped_column(String(64))
    ai_summary: Mapped[dict | None] = mapped_column(JSON)
    path: Mapped[str | None] = mapped_column(String(1024))
    thumb_path: Mapped[str | None] = mapped_column(String(1024))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    media = relationship("Media")
