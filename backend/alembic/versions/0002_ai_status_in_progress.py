"""Add in_progress status for AI detections.

Revision ID: 0002_ai_status_in_progress
Revises: 0001_init
Create Date: 2025-12-08
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_ai_status_in_progress"
down_revision = "0001_init"
branch_labels = None
depends_on = None

old_statuses = ("pending", "done", "failed")
new_statuses = ("pending", "in_progress", "done", "failed")


def upgrade() -> None:
    # Add new value to existing enum; IF NOT EXISTS is safe for idempotent runs
    op.execute("ALTER TYPE aidetectionstatus ADD VALUE IF NOT EXISTS 'in_progress'")


def downgrade() -> None:
    # Recreate enum without the new value and reassign
    op.execute("ALTER TYPE aidetectionstatus RENAME TO aidetectionstatus_old")
    sa.Enum(*old_statuses, name="aidetectionstatus").create(op.get_bind())
    op.execute(
        "ALTER TABLE aidetection ALTER COLUMN status TYPE aidetectionstatus USING status::text::aidetectionstatus"
    )
    op.execute("DROP TYPE aidetectionstatus_old")
