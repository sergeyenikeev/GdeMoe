"""ORM-модель локации и иерархии хранения."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, JSON, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.enums import LocationKind


class Location(Base):
    """Локация в дереве хранения: дом, комната, шкаф, коробка и т.д."""
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspace.id"), nullable=False, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[LocationKind] = mapped_column(
        Enum(LocationKind, values_callable=lambda x: [e.value for e in x]),
        default=LocationKind.OTHER,
    )
    # `path` хранит materialized path и помогает быстро перестраивать дерево.
    path: Mapped[str | None] = mapped_column(String(1024), index=True)  # можно использовать ltree
    photo_media_id: Mapped[int | None] = mapped_column(ForeignKey("media.id"), nullable=True, index=True)
    meta: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # self-reference задаёт иерархию родитель -> потомок.
    parent = relationship("Location", remote_side="Location.id")
    photo_media = relationship("Media", foreign_keys=[photo_media_id])
    workspace = relationship("Workspace", back_populates="locations")
    items = relationship("Item", back_populates="location")
