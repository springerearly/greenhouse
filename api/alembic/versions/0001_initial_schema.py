"""Initial schema — all tables (idempotent)

Revision ID: 0001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, name: str) -> bool:
    return Inspector.from_engine(conn).has_table(name)


def _index_exists(conn, table: str, index: str) -> bool:
    indexes = Inspector.from_engine(conn).get_indexes(table)
    return any(i["name"] == index for i in indexes)


def upgrade() -> None:
    conn = op.get_bind()

    # ── gpios ─────────────────────────────────────────────────────────────────
    if not _table_exists(conn, "gpios"):
        op.create_table(
            "gpios",
            sa.Column("gpio_number", sa.Integer(), nullable=False),
            sa.Column("gpio_description", sa.String(), nullable=True),
            sa.Column("gpio_function", sa.String(), nullable=True),
            sa.Column("pwm_value", sa.Float(), nullable=True),
            sa.PrimaryKeyConstraint("gpio_number"),
        )
    if not _index_exists(conn, "gpios", "ix_gpios_gpio_description"):
        op.create_index("ix_gpios_gpio_description", "gpios", ["gpio_description"], unique=False)
    if not _index_exists(conn, "gpios", "ix_gpios_gpio_number"):
        op.create_index("ix_gpios_gpio_number", "gpios", ["gpio_number"], unique=False)

    # ── devices ───────────────────────────────────────────────────────────────
    if not _table_exists(conn, "devices"):
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
    if not _index_exists(conn, "devices", "ix_devices_id"):
        op.create_index("ix_devices_id", "devices", ["id"], unique=False)
    if not _index_exists(conn, "devices", "ix_devices_name"):
        op.create_index("ix_devices_name", "devices", ["name"], unique=False)

    # ── sensor_readings ───────────────────────────────────────────────────────
    if not _table_exists(conn, "sensor_readings"):
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
    if not _index_exists(conn, "sensor_readings", "ix_sensor_readings_id"):
        op.create_index("ix_sensor_readings_id", "sensor_readings", ["id"], unique=False)
    if not _index_exists(conn, "sensor_readings", "ix_sensor_readings_timestamp"):
        op.create_index("ix_sensor_readings_timestamp", "sensor_readings", ["timestamp"], unique=False)

    # ── automations ───────────────────────────────────────────────────────────
    if not _table_exists(conn, "automations"):
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
    if not _index_exists(conn, "automations", "ix_automations_id"):
        op.create_index("ix_automations_id", "automations", ["id"], unique=False)

    # ── alerts ────────────────────────────────────────────────────────────────
    if not _table_exists(conn, "alerts"):
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
    if not _index_exists(conn, "alerts", "ix_alerts_id"):
        op.create_index("ix_alerts_id", "alerts", ["id"], unique=False)


def downgrade() -> None:
    conn = op.get_bind()

    if _index_exists(conn, "alerts", "ix_alerts_id"):
        op.drop_index("ix_alerts_id", table_name="alerts")
    if _table_exists(conn, "alerts"):
        op.drop_table("alerts")

    if _index_exists(conn, "automations", "ix_automations_id"):
        op.drop_index("ix_automations_id", table_name="automations")
    if _table_exists(conn, "automations"):
        op.drop_table("automations")

    if _index_exists(conn, "sensor_readings", "ix_sensor_readings_timestamp"):
        op.drop_index("ix_sensor_readings_timestamp", table_name="sensor_readings")
    if _index_exists(conn, "sensor_readings", "ix_sensor_readings_id"):
        op.drop_index("ix_sensor_readings_id", table_name="sensor_readings")
    if _table_exists(conn, "sensor_readings"):
        op.drop_table("sensor_readings")

    if _index_exists(conn, "devices", "ix_devices_name"):
        op.drop_index("ix_devices_name", table_name="devices")
    if _index_exists(conn, "devices", "ix_devices_id"):
        op.drop_index("ix_devices_id", table_name="devices")
    if _table_exists(conn, "devices"):
        op.drop_table("devices")

    if _index_exists(conn, "gpios", "ix_gpios_gpio_number"):
        op.drop_index("ix_gpios_gpio_number", table_name="gpios")
    if _index_exists(conn, "gpios", "ix_gpios_gpio_description"):
        op.drop_index("ix_gpios_gpio_description", table_name="gpios")
    if _table_exists(conn, "gpios"):
        op.drop_table("gpios")
