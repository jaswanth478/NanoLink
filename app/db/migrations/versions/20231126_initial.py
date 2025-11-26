"""initial schema"""

from alembic import op
import sqlalchemy as sa

revision = "20231126_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "url_mappings",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("short_code", sa.String(length=16), nullable=False, unique=True),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_ip", sa.String(length=64), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True, unique=True),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_url_mappings_short_code", "url_mappings", ["short_code"], unique=True)

    op.create_table(
        "click_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("short_code", sa.String(length=16), nullable=False),
        sa.Column("referrer", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("client_ip", sa.String(length=64), nullable=False),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["short_code"], ["url_mappings.short_code"], ondelete="CASCADE"),
    )
    op.create_index("ix_click_events_short_code", "click_events", ["short_code"])
    op.create_index("ix_click_events_clicked_at", "click_events", ["clicked_at"])


def downgrade() -> None:
    op.drop_table("click_events")
    op.drop_table("url_mappings")
