"""Initial schema — all tables

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── gpios ─────────────────────────────────────────────────────────────────
    op.create_table(
        "gpios",
        sa.Column("gpio_number", sa.Integer(), nullable=False),
        sa.Column("gpio_description", sa.String(), nullable=True),
        sa.Column("gpio_function", sa.String(), nullable=True),
        sa.Column("pwm_value", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("gpio_number"),
    )
    op.create_index(op.f("ix_gpios_gpio_description"), "gpios", ["gpio_description"], unique=False)
    op.create_index(op.f("ix_gpios_gpio_number"), "gpios", ["gpio_number"], unique=False)

    # ── devices ───────────────────────────────────────────────────────────────
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("device_type", sa.String(), nullable=False),
        sa.Column("ip_address", sa.String(), nullable=False),
        sa.Column("port", sa.Integer(), nullable=True),
        sa.Column("poll_interval", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
        sa.Column("firmware_version", sa.String(), nullable=True),
        sa.Column("mac_address", sa.String(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ip_address"),
    )
    op.create_index(op.f("ix_devices_id"), "devices", ["id"], unique=False)
    op.create_index(op.f("ix_devices_name"), "devices", ["name"], unique=False)

    # ── sensor_readings ───────────────────────────────────────────────────────
    op.create_table(
        "sensor_readings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("sensor_type", sa.String(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sensor_readings_id"), "sensor_readings", ["id"], unique=False)
    op.create_index(op.f("ix_sensor_readings_timestamp"), "sensor_readings", ["timestamp"], unique=False)

    # ── automations ───────────────────────────────────────────────────────────
    op.create_table(
        "automations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=True),
        sa.Column("trigger_json", sa.Text(), nullable=False),
        sa.Column("action_json", sa.Text(), nullable=False),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=True),
        sa.Column("last_triggered", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_automations_id"), "automations", ["id"], unique=False)

    # ── alerts ────────────────────────────────────────────────────────────────
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("level", sa.String(), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_alerts_id"), "alerts", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_alerts_id"), table_name="alerts")
    op.drop_table("alerts")

    op.drop_index(op.f("ix_automations_id"), table_name="automations")
    op.drop_table("automations")

    op.drop_index(op.f("ix_sensor_readings_timestamp"), table_name="sensor_readings")
    op.drop_index(op.f("ix_sensor_readings_id"), table_name="sensor_readings")
    op.drop_table("sensor_readings")

    op.drop_index(op.f("ix_devices_name"), table_name="devices")
    op.drop_index(op.f("ix_devices_id"), table_name="devices")
    op.drop_table("devices")

    op.drop_index(op.f("ix_gpios_gpio_number"), table_name="gpios")
    op.drop_index(op.f("ix_gpios_gpio_description"), table_name="gpios")
    op.drop_table("gpios")
