"""Revision ID: 0005_location_photo_and_history_location
Revises: 0004_upload_history_and_ai_links
Create Date: 2025-12-28
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005_location_photo_and_history_location"
down_revision = "0004_upload_history_and_ai_links"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("location", sa.Column("photo_media_id", sa.Integer(), sa.ForeignKey("media.id"), nullable=True))
    op.create_index("ix_location_photo_media_id", "location", ["photo_media_id"])

    op.add_column(
        "mediauploadhistory",
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("location.id"), nullable=True),
    )
    op.create_index("ix_mediauploadhistory_location_id", "mediauploadhistory", ["location_id"])


def downgrade() -> None:
    op.drop_index("ix_mediauploadhistory_location_id", table_name="mediauploadhistory")
    op.drop_column("mediauploadhistory", "location_id")

    op.drop_index("ix_location_photo_media_id", table_name="location")
    op.drop_column("location", "photo_media_id")
