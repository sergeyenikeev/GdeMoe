from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ItemBatch(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspace.id"), nullable=False, index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("user.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    items = relationship("Item", back_populates="batch")
