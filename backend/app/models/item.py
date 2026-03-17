from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, Numeric, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base
from app.models.enums import ItemStatus, Scope


class Item(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workspace_id: Mapped[int] = mapped_column(ForeignKey("workspace.id"), index=True, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2048))
    category: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[ItemStatus] = mapped_column(
        Enum(ItemStatus, values_callable=lambda x: [e.value for e in x]),
        default=ItemStatus.NEW,
        nullable=False,
    )
    attributes: Mapped[dict | None] = mapped_column(JSON)
    model: Mapped[str | None] = mapped_column(String(255))
    serial_number: Mapped[str | None] = mapped_column(String(255))
    purchase_date: Mapped[str | None] = mapped_column(String(50))
    price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    store: Mapped[str | None] = mapped_column(String(255))
    order_number: Mapped[str | None] = mapped_column(String(255))
    order_url: Mapped[str | None] = mapped_column(String(2048))
    warranty_until: Mapped[str | None] = mapped_column(String(50))
    expiration_date: Mapped[str | None] = mapped_column(String(50))
    reminders: Mapped[dict | None] = mapped_column(JSON)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("location.id"), index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("itembatch.id"), nullable=True, index=True)
    scope: Mapped[Scope] = mapped_column(
        Enum(Scope, values_callable=lambda x: [e.value for e in x]),
        default=Scope.PRIVATE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    workspace = relationship("Workspace", back_populates="items")
    location = relationship("Location", back_populates="items")
    tags = relationship("ItemTag", back_populates="item")
    groups = relationship("GroupItem", back_populates="item")
    relations = relationship("ItemRelation", back_populates="parent", foreign_keys="ItemRelation.parent_item_id")
    children = relationship("ItemRelation", back_populates="child", foreign_keys="ItemRelation.child_item_id")
    media_links = relationship("ItemMedia", back_populates="item")
    notes = relationship("ItemNote", back_populates="item")
    history = relationship("ItemHistory", back_populates="item")
    batch = relationship("ItemBatch", back_populates="items")
