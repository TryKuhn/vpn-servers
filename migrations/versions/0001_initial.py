"""initial users and devices

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-27
"""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(length=128), nullable=False), sa.Column("login", sa.String(length=128), nullable=True), sa.Column("password_hash", sa.String(length=255), nullable=True), sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False), sa.Column("device_limit", sa.Integer(), server_default="3", nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True), sa.Column("traffic_limit_gb", sa.Integer(), nullable=True), sa.Column("note", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_users_name", "users", ["name"], unique=True)
    op.create_index("ix_users_login", "users", ["login"], unique=True)
    op.create_table("devices", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("name", sa.String(length=128), nullable=False), sa.Column("os", sa.String(length=64), nullable=True), sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False), sa.Column("subscription_token", sa.String(length=255), nullable=False), sa.Column("vless_uuid", sa.String(length=36), nullable=False), sa.Column("hysteria_username", sa.String(length=128), nullable=False), sa.Column("hysteria_password", sa.String(length=255), nullable=False), sa.Column("naive_username", sa.String(length=128), nullable=False), sa.Column("naive_password", sa.String(length=255), nullable=False), sa.Column("torrent_strikes", sa.Integer(), server_default="0", nullable=False), sa.Column("last_subscription_request_at", sa.DateTime(timezone=True), nullable=True), sa.Column("last_subscription_user_agent", sa.String(length=512), nullable=True), sa.Column("last_subscription_ip", sa.String(length=64), nullable=True), sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("user_id", "name", name="uq_devices_user_name"))
    op.create_index("ix_devices_user_id", "devices", ["user_id"])
    op.create_index("ix_devices_subscription_token", "devices", ["subscription_token"], unique=True)
    op.create_index("ix_devices_vless_uuid", "devices", ["vless_uuid"], unique=True)
    op.create_index("ix_devices_hysteria_username", "devices", ["hysteria_username"], unique=True)
    op.create_index("ix_devices_naive_username", "devices", ["naive_username"], unique=True)

def downgrade() -> None:
    op.drop_index("ix_devices_naive_username", table_name="devices")
    op.drop_index("ix_devices_hysteria_username", table_name="devices")
    op.drop_index("ix_devices_vless_uuid", table_name="devices")
    op.drop_index("ix_devices_subscription_token", table_name="devices")
    op.drop_index("ix_devices_user_id", table_name="devices")
    op.drop_table("devices")
    op.drop_index("ix_users_login", table_name="users")
    op.drop_index("ix_users_name", table_name="users")
    op.drop_table("users")
