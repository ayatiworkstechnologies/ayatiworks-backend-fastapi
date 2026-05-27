"""repair_client_module_schema

Revision ID: 20260527_170000
Revises: f2a3b4c5d6e7
Create Date: 2026-05-27 17:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260527_170000"
down_revision: str | None = "f2a3b4c5d6e7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector():
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(column["name"] == column_name for column in _inspector().get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    return any(index["name"] == index_name for index in _inspector().get_indexes(table_name))


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str], unique: bool = False) -> None:
    if _has_table(table_name) and not _has_index(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
    ]


def _repair_base_columns(table_name: str) -> None:
    _add_column_if_missing(table_name, sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    _add_column_if_missing(table_name, sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    _add_column_if_missing(table_name, sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    _add_column_if_missing(table_name, sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column_if_missing(table_name, sa.Column("deleted_at", sa.DateTime(), nullable=True))
    _add_column_if_missing(table_name, sa.Column("deleted_by", sa.Integer(), nullable=True))
    _add_column_if_missing(table_name, sa.Column("created_by", sa.Integer(), nullable=True))
    _add_column_if_missing(table_name, sa.Column("updated_by", sa.Integer(), nullable=True))


def upgrade() -> None:
    if not _has_table("client_smtp_configs"):
        op.create_table(
            "client_smtp_configs",
            sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, unique=True),
            sa.Column("host", sa.String(length=255), nullable=False),
            sa.Column("port", sa.Integer(), nullable=True, server_default="587"),
            sa.Column("username", sa.String(length=255), nullable=False),
            sa.Column("password", sa.String(length=500), nullable=False),
            sa.Column("from_email", sa.String(length=255), nullable=False),
            sa.Column("from_name", sa.String(length=255), nullable=True),
            sa.Column("use_tls", sa.Boolean(), nullable=True, server_default=sa.true()),
            *_base_columns(),
        )
    else:
        _add_column_if_missing("client_smtp_configs", sa.Column("client_id", sa.Integer(), nullable=False))
        _add_column_if_missing("client_smtp_configs", sa.Column("host", sa.String(length=255), nullable=False))
        _add_column_if_missing("client_smtp_configs", sa.Column("port", sa.Integer(), nullable=True, server_default="587"))
        _add_column_if_missing("client_smtp_configs", sa.Column("username", sa.String(length=255), nullable=False))
        _add_column_if_missing("client_smtp_configs", sa.Column("password", sa.String(length=500), nullable=False))
        _add_column_if_missing("client_smtp_configs", sa.Column("from_email", sa.String(length=255), nullable=False))
        _add_column_if_missing("client_smtp_configs", sa.Column("from_name", sa.String(length=255), nullable=True))
        _add_column_if_missing("client_smtp_configs", sa.Column("use_tls", sa.Boolean(), nullable=True, server_default=sa.true()))
        _repair_base_columns("client_smtp_configs")

    if not _has_table("client_mail_templates"):
        op.create_table(
            "client_mail_templates",
            sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("subject", sa.String(length=500), nullable=False),
            sa.Column("html_body", sa.Text(), nullable=False),
            sa.Column("from_email", sa.String(length=255), nullable=True),
            sa.Column("to_email", sa.String(length=500), nullable=True),
            sa.Column("cc_email", sa.JSON(), nullable=True),
            sa.Column("bcc_email", sa.JSON(), nullable=True),
            sa.Column("variables", sa.JSON(), nullable=True),
            *_base_columns(),
        )
    else:
        _add_column_if_missing("client_mail_templates", sa.Column("client_id", sa.Integer(), nullable=False))
        _add_column_if_missing("client_mail_templates", sa.Column("name", sa.String(length=255), nullable=False))
        _add_column_if_missing("client_mail_templates", sa.Column("subject", sa.String(length=500), nullable=False))
        _add_column_if_missing("client_mail_templates", sa.Column("html_body", sa.Text(), nullable=False))
        _add_column_if_missing("client_mail_templates", sa.Column("from_email", sa.String(length=255), nullable=True))
        _add_column_if_missing("client_mail_templates", sa.Column("to_email", sa.String(length=500), nullable=True))
        _add_column_if_missing("client_mail_templates", sa.Column("cc_email", sa.JSON(), nullable=True))
        _add_column_if_missing("client_mail_templates", sa.Column("bcc_email", sa.JSON(), nullable=True))
        _add_column_if_missing("client_mail_templates", sa.Column("variables", sa.JSON(), nullable=True))
        _repair_base_columns("client_mail_templates")

    if not _has_table("client_modules"):
        op.create_table(
            "client_modules",
            sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("slug", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("icon", sa.String(length=50), nullable=True),
            sa.Column("fields", sa.JSON(), nullable=False),
            sa.Column("mail_template_id", sa.Integer(), sa.ForeignKey("client_mail_templates.id", ondelete="SET NULL"), nullable=True),
            *_base_columns(),
        )
    else:
        _add_column_if_missing("client_modules", sa.Column("client_id", sa.Integer(), nullable=False))
        _add_column_if_missing("client_modules", sa.Column("name", sa.String(length=255), nullable=False))
        _add_column_if_missing("client_modules", sa.Column("slug", sa.String(length=255), nullable=False))
        _add_column_if_missing("client_modules", sa.Column("description", sa.Text(), nullable=True))
        _add_column_if_missing("client_modules", sa.Column("icon", sa.String(length=50), nullable=True))
        _add_column_if_missing("client_modules", sa.Column("fields", sa.JSON(), nullable=False))
        _add_column_if_missing("client_modules", sa.Column("mail_template_id", sa.Integer(), nullable=True))
        _repair_base_columns("client_modules")

    if not _has_table("client_module_records"):
        op.create_table(
            "client_module_records",
            sa.Column("module_id", sa.Integer(), sa.ForeignKey("client_modules.id", ondelete="CASCADE"), nullable=False),
            sa.Column("data", sa.JSON(), nullable=False),
            *_base_columns(),
        )
    else:
        _add_column_if_missing("client_module_records", sa.Column("module_id", sa.Integer(), nullable=False))
        _add_column_if_missing("client_module_records", sa.Column("data", sa.JSON(), nullable=False))
        _repair_base_columns("client_module_records")

    _create_index_if_missing("ix_client_smtp_configs_client_id", "client_smtp_configs", ["client_id"])
    _create_index_if_missing("ix_client_mail_templates_client_id", "client_mail_templates", ["client_id"])
    _create_index_if_missing("ix_client_modules_client_id", "client_modules", ["client_id"])
    _create_index_if_missing("ix_client_modules_slug", "client_modules", ["slug"])
    _create_index_if_missing("ix_client_module_records_module_id", "client_module_records", ["module_id"])


def downgrade() -> None:
    # This is a repair migration; intentionally do not drop user data.
    pass
