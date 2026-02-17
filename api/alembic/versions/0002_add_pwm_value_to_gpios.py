"""Add pwm_value column to existing gpios table

This migration is safe to run even if the column already exists
(uses IF NOT EXISTS via server_default approach).
It adds the pwm_value column that was introduced with PWM support.

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    """Check if a column already exists (idempotent guard)."""
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    cols = [c["name"] for c in inspector.get_columns(table)]
    return column in cols


def upgrade() -> None:
    # Идемпотентная добавка: пропускаем, если колонка уже есть
    # (актуально для пользователей, сделавших ALTER TABLE вручную)
    if not _column_exists("gpios", "pwm_value"):
        op.add_column(
            "gpios",
            sa.Column("pwm_value", sa.Float(), nullable=True, server_default="0.0"),
        )


def downgrade() -> None:
    if _column_exists("gpios", "pwm_value"):
        op.drop_column("gpios", "pwm_value")
