from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class ItemRelation(Base):
    __tablename__ = "item_relations"

    parent_item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), primary_key=True)
    child_item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), primary_key=True)

    parent = relationship("Item", foreign_keys=[parent_item_id], back_populates="relations")
    child = relationship("Item", foreign_keys=[child_item_id], back_populates="children")


class ItemNote(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    content: Mapped[str] = mapped_column(String(4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    item = relationship("Item", back_populates="notes")


class ItemHistory(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("user.id"))
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    before: Mapped[dict | None] = mapped_column(JSON)
    after: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    item = relationship("Item", back_populates="history")
