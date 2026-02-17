"""add client modules smtp templates

Revision ID: a1b2c3d4e5f6
Revises: f78f3e739a8c
Create Date: 2026-02-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'f78f3e739a8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Client SMTP Config
    op.create_table(
        'client_smtp_configs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('host', sa.String(255), nullable=False),
        sa.Column('port', sa.Integer(), default=587),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('password', sa.String(500), nullable=False),
        sa.Column('from_email', sa.String(255), nullable=False),
        sa.Column('from_name', sa.String(255), nullable=True),
        sa.Column('use_tls', sa.Boolean(), default=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Client Mail Templates
    op.create_table(
        'client_mail_templates',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('html_body', sa.Text(), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Client Modules (dynamic field definitions)
    op.create_table(
        'client_modules',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('client_id', sa.Integer(), sa.ForeignKey('clients.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('icon', sa.String(50), nullable=True, default='HiOutlineCollection'),
        sa.Column('fields', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Client Module Records (JSON data storage)
    op.create_table(
        'client_module_records',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('module_id', sa.Integer(), sa.ForeignKey('client_modules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('is_deleted', sa.Boolean(), default=False, nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Add indexes
    op.create_index('ix_client_smtp_configs_client_id', 'client_smtp_configs', ['client_id'])
    op.create_index('ix_client_mail_templates_client_id', 'client_mail_templates', ['client_id'])
    op.create_index('ix_client_modules_client_id', 'client_modules', ['client_id'])
    op.create_index('ix_client_modules_slug', 'client_modules', ['slug'])
    op.create_index('ix_client_module_records_module_id', 'client_module_records', ['module_id'])


def downgrade() -> None:
    op.drop_index('ix_client_module_records_module_id', 'client_module_records')
    op.drop_index('ix_client_modules_slug', 'client_modules')
    op.drop_index('ix_client_modules_client_id', 'client_modules')
    op.drop_index('ix_client_mail_templates_client_id', 'client_mail_templates')
    op.drop_index('ix_client_smtp_configs_client_id', 'client_smtp_configs')
    op.drop_table('client_module_records')
    op.drop_table('client_modules')
    op.drop_table('client_mail_templates')
    op.drop_table('client_smtp_configs')
