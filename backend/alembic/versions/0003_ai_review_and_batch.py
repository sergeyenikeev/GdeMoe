"""ai review logs and item batches

Revision ID: 0003_ai_review_and_batch
Revises: 0002_ai_status_in_progress
Create Date: 2025-12-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.models.enums import (
    AIDetectionDecision,
    AIDetectionReviewAction,
    AIDetectionStatus,
)

revision: str = "0003_ai_review_and_batch"
down_revision: Union[str, None] = "0002_ai_status_in_progress"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    decision_enum = sa.dialects.postgresql.ENUM(
        *[e.value for e in AIDetectionDecision], name="aidetectiondecision", create_type=False
    )
    review_action_enum = sa.dialects.postgresql.ENUM(
        *[e.value for e in AIDetectionReviewAction], name="aidetectionreviewaction", create_type=False
    )

    bind = op.get_bind()
    decision_enum.create(bind, checkfirst=True)
    review_action_enum.create(bind, checkfirst=True)

    op.create_table(
        "itembatch",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspace.id"), nullable=False, index=True),
        sa.Column("location_id", sa.Integer(), sa.ForeignKey("location.id"), nullable=True),
        sa.Column("title", sa.String(length=255)),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("user.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.add_column("item", sa.Column("batch_id", sa.Integer(), sa.ForeignKey("itembatch.id"), nullable=True))
    op.create_index("ix_item_batch", "item", ["batch_id"])

    op.add_column(
        "aidetectionobject",
        sa.Column("decision", decision_enum, nullable=False, server_default=AIDetectionDecision.PENDING.value),
    )
    op.add_column("aidetectionobject", sa.Column("decided_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=True))
    op.add_column("aidetectionobject", sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "aidetectionreview",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("detection_id", sa.Integer(), sa.ForeignKey("aidetection.id"), nullable=False, index=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("action", review_action_enum, nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("aidetectionreview")
    op.drop_column("aidetectionobject", "decided_at")
    op.drop_column("aidetectionobject", "decided_by")
    op.drop_column("aidetectionobject", "decision")
    op.drop_index("ix_item_batch", table_name="item")
    op.drop_column("item", "batch_id")
    op.drop_table("itembatch")

    op.execute("DROP TYPE IF EXISTS aidetectionreviewaction")
    op.execute("DROP TYPE IF EXISTS aidetectiondecision")
