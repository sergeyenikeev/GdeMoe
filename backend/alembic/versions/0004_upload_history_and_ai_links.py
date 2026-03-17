"""upload history and ai links

Revision ID: 0004_upload_history_and_ai_links
Revises: 0003_ai_review_and_batch
Create Date: 2025-12-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.enums import UploadStatus, MediaType


revision: str = "0004_upload_history_and_ai_links"
down_revision: Union[str, None] = "0003_ai_review_and_batch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    upload_status_enum = sa.dialects.postgresql.ENUM(
        *[e.value for e in UploadStatus], name="uploadstatus", create_type=False
    )
    media_type_enum = sa.dialects.postgresql.ENUM(
        *[e.value for e in MediaType], name="mediatype", create_type=False
    )
    bind = op.get_bind()
    upload_status_enum.create(bind, checkfirst=True)
    media_type_enum.create(bind, checkfirst=True)

    op.add_column("aidetectionobject", sa.Column("linked_item_id", sa.Integer(), sa.ForeignKey("item.id"), nullable=True))
    op.add_column("aidetectionobject", sa.Column("linked_location_id", sa.Integer(), sa.ForeignKey("location.id"), nullable=True))

    op.create_table(
        "mediauploadhistory",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("media_id", sa.Integer(), sa.ForeignKey("media.id"), nullable=True),
        sa.Column("detection_id", sa.Integer(), sa.ForeignKey("aidetection.id"), nullable=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id"), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("media_type", media_type_enum, nullable=False),
        sa.Column("status", upload_status_enum, nullable=False, server_default=UploadStatus.IN_PROGRESS.value),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column("ai_status", sa.String(length=64), nullable=True),
        sa.Column("ai_summary", sa.JSON(), nullable=True),
        sa.Column("path", sa.String(length=1024), nullable=True),
        sa.Column("thumb_path", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_mediauploadhistory_media_id", "mediauploadhistory", ["media_id"])
    op.create_index("ix_mediauploadhistory_owner", "mediauploadhistory", ["owner_user_id"])
    op.create_index("ix_mediauploadhistory_workspace", "mediauploadhistory", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_mediauploadhistory_workspace", table_name="mediauploadhistory")
    op.drop_index("ix_mediauploadhistory_owner", table_name="mediauploadhistory")
    op.drop_index("ix_mediauploadhistory_media_id", table_name="mediauploadhistory")
    op.drop_table("mediauploadhistory")
    op.drop_column("aidetectionobject", "linked_location_id")
    op.drop_column("aidetectionobject", "linked_item_id")
    op.execute("DROP TYPE IF EXISTS uploadstatus")
