from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String, JSON, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class Group(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspace.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_group_id: Mapped[int | None] = mapped_column(ForeignKey("group.id"), nullable=True)
    settings: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    workspace = relationship("Workspace", back_populates="groups")
    parent = relationship("Group", remote_side="Group.id")
    memberships = relationship("Membership", back_populates="group")
    items = relationship("GroupItem", back_populates="group")


class Membership(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="reader")  # owner/editor/reader
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="memberships")
    group = relationship("Group", back_populates="memberships")


class GroupItem(Base):
    __tablename__ = "group_items"

    group_id: Mapped[int] = mapped_column(ForeignKey("group.id"), primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), primary_key=True)

    group = relationship("Group", back_populates="items")
    item = relationship("Item", back_populates="groups")
