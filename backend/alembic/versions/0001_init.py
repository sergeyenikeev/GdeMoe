"""initial schema

Revision ID: 0001_init
Revises:
Create Date: 2025-12-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.enums import (
    ItemStatus,
    LocationKind,
    Scope,
    TodoStatus,
    MediaType,
    AIDetectionStatus,
)

revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    item_status = sa.dialects.postgresql.ENUM(
        *[e.value for e in ItemStatus], name="itemstatus", create_type=False
    )
    location_kind = sa.dialects.postgresql.ENUM(
        *[e.value for e in LocationKind], name="locationkind", create_type=False
    )
    scope_enum = sa.dialects.postgresql.ENUM(
        *[e.value for e in Scope], name="scope", create_type=False
    )
    todo_status = sa.dialects.postgresql.ENUM(
        *[e.value for e in TodoStatus], name="todostatus", create_type=False
    )
    media_type = sa.dialects.postgresql.ENUM(
        *[e.value for e in MediaType], name="mediatype", create_type=False
    )
    ai_status = sa.dialects.postgresql.ENUM(
        *[e.value for e in AIDetectionStatus], name="aidetectionstatus", create_type=False
    )

    bind = op.get_bind()
    item_status.create(bind, checkfirst=True)
    location_kind.create(bind, checkfirst=True)
    scope_enum.create(bind, checkfirst=True)
    todo_status.create(bind, checkfirst=True)
    media_type.create(bind, checkfirst=True)
    ai_status.create(bind, checkfirst=True)

    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_email", "user", ["email"], unique=True)

    op.create_table(
        "workspace",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scope", scope_enum, nullable=False, server_default=Scope.PRIVATE.value),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "group",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("parent_group_id", sa.Integer(), sa.ForeignKey("group.id")),
        sa.Column("settings", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "membership",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("group.id"), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="reader"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "location",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("location.id")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", location_kind, nullable=False, server_default=LocationKind.OTHER.value),
        sa.Column("path", sa.String(length=1024)),
        sa.Column("meta", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_location_workspace", "location", ["workspace_id"])

    op.create_table(
        "item",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2048)),
        sa.Column("category", sa.String(length=255)),
        sa.Column("status", item_status, nullable=False, server_default=ItemStatus.NEW.value),
        sa.Column("attributes", sa.JSON()),
        sa.Column("model", sa.String(length=255)),
        sa.Column("serial_number", sa.String(length=255)),
        sa.Column("purchase_date", sa.String(length=50)),
        sa.Column("price", sa.Numeric(14, 2)),
        sa.Column("currency", sa.String(length=3)),
        sa.Column("store", sa.String(length=255)),
        sa.Column("order_number", sa.String(length=255)),
        sa.Column("order_url", sa.String(length=2048)),
        sa.Column("warranty_until", sa.String(length=50)),
        sa.Column("expiration_date", sa.String(length=50)),
        sa.Column("reminders", sa.JSON()),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("location.id")),
        sa.Column("scope", scope_enum, nullable=False, server_default=Scope.PRIVATE.value),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_item_workspace", "item", ["workspace_id"])
    op.create_index("ix_item_location", "item", ["location_id"])
    op.create_index("ix_item_status", "item", ["status"])

    op.create_table(
        "tag",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "item_tags",
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id"), primary_key=True),
        sa.Column("tag_id", sa.Integer(), sa.ForeignKey("tag.id"), primary_key=True),
    )
    op.create_index("ix_item_tags_item", "item_tags", ["item_id"])

    op.create_table(
        "group_items",
        sa.Column("group_id", sa.Integer(), sa.ForeignKey("group.id"), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id"), primary_key=True),
    )

    op.create_table(
        "item_relations",
        sa.Column("parent_item_id", sa.Integer(), sa.ForeignKey("item.id"), primary_key=True),
        sa.Column("child_item_id", sa.Integer(), sa.ForeignKey("item.id"), primary_key=True),
    )

    op.create_table(
        "itemnote",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("content", sa.String(length=4000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "itemhistory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("before", sa.JSON()),
        sa.Column("after", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("location.id")),
        sa.Column("media_type", media_type, nullable=False),
        sa.Column("path", sa.String(length=1024), nullable=False),
        sa.Column("thumb_path", sa.String(length=1024)),
        sa.Column("mime_type", sa.String(length=128)),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("file_hash", sa.String(length=128)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("analyzed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "item_media",
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id"), primary_key=True),
        sa.Column("media_id", sa.Integer(), sa.ForeignKey("media.id"), primary_key=True),
    )

    op.create_table(
        "todo",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id")),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("location.id")),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=2048)),
        sa.Column("status", todo_status, nullable=False, server_default=TodoStatus.OPEN.value),
        sa.Column("due_date", sa.String(length=50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "aidetection",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("media_id", sa.Integer(), sa.ForeignKey("media.id"), nullable=False),
        sa.Column("status", ai_status, nullable=False, server_default=AIDetectionStatus.PENDING.value),
        sa.Column("raw", sa.JSON()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "aidetectionobject",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("detection_id", sa.Integer(), sa.ForeignKey("aidetection.id"), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 3)),
        sa.Column("bbox", sa.JSON()),
        sa.Column("suggested_location_id", sa.Integer(), sa.ForeignKey("location.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "aidetectioncandidate",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("detection_object_id", sa.Integer(), sa.ForeignKey("aidetectionobject.id"), nullable=False),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("item.id"), nullable=False),
        sa.Column("score", sa.Numeric(5, 3)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("aidetectioncandidate")
    op.drop_table("aidetectionobject")
    op.drop_table("aidetection")
    op.drop_table("todo")
    op.drop_table("item_media")
    op.drop_table("media")
    op.drop_table("itemhistory")
    op.drop_table("itemnote")
    op.drop_table("item_relations")
    op.drop_table("group_items")
    op.drop_table("item_tags")
    op.drop_table("tag")
    op.drop_table("item")
    op.drop_table("location")
    op.drop_table("membership")
    op.drop_table("group")
    op.drop_table("workspace")
    op.drop_table("user")
    op.execute("DROP TYPE IF EXISTS itemstatus CASCADE")
    op.execute("DROP TYPE IF EXISTS locationkind CASCADE")
    op.execute("DROP TYPE IF EXISTS scope CASCADE")
    op.execute("DROP TYPE IF EXISTS todostatus CASCADE")
    op.execute("DROP TYPE IF EXISTS mediatype CASCADE")
    op.execute("DROP TYPE IF EXISTS aidetectionstatus CASCADE")
