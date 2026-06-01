"""Create events table

Revision ID: 0001
Revises:
Create Date: 2026-06-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(255), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_events_created_at", "events", ["created_at"])
    op.create_index("ix_events_event_type", "events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_events_event_type", table_name="events")
    op.drop_index("ix_events_created_at", table_name="events")
    op.drop_table("events")
