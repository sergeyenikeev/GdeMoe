from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.enums import TodoStatus


class Todo(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspace.id"), nullable=False)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("item.id"))
    location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"))
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2048))
    status: Mapped[TodoStatus] = mapped_column(
        Enum(TodoStatus, values_callable=lambda x: [e.value for e in x]),
        default=TodoStatus.OPEN,
    )
    due_date: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
