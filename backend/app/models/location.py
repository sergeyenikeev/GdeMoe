from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON, func, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.enums import LocationKind


class Location(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspace.id"), nullable=False, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[LocationKind] = mapped_column(
        Enum(LocationKind, values_callable=lambda x: [e.value for e in x]),
        default=LocationKind.OTHER,
    )
    path: Mapped[str | None] = mapped_column(String(1024), index=True)  # можно использовать ltree
    meta: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    parent = relationship("Location", remote_side="Location.id")
    workspace = relationship("Workspace", back_populates="locations")
    items = relationship("Item", back_populates="location")
