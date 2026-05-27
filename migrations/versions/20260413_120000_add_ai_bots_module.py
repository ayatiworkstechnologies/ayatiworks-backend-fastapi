"""add_ai_bots_module

Revision ID: e1f2a3b4c5d6
Revises: c0506085a86b
Create Date: 2026-04-13 12:00:00.000000

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'c0506085a86b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_bots',
        sa.Column('company_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('slug', sa.String(length=160), nullable=False),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tone', sa.String(length=50), nullable=False),
        sa.Column('personality', sa.String(length=100), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('welcome_message', sa.Text(), nullable=True),
        sa.Column('primary_color', sa.String(length=20), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('ui_config', sa.JSON(), nullable=True),
        sa.Column('enabled_plugins', sa.JSON(), nullable=True),
        sa.Column('supported_languages', sa.JSON(), nullable=True),
        sa.Column('is_published', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_bots_company_id'), 'ai_bots', ['company_id'], unique=False)
    op.create_index(op.f('ix_ai_bots_id'), 'ai_bots', ['id'], unique=False)
    op.create_index(op.f('ix_ai_bots_industry'), 'ai_bots', ['industry'], unique=False)
    op.create_index(op.f('ix_ai_bots_slug'), 'ai_bots', ['slug'], unique=True)

    op.create_table(
        'bot_knowledge_sources',
        sa.Column('bot_id', sa.Integer(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('file_url', sa.String(length=500), nullable=True),
        sa.Column('website_url', sa.String(length=500), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('embedding_provider', sa.String(length=100), nullable=True),
        sa.Column('embedding_reference', sa.String(length=255), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['bot_id'], ['ai_bots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bot_knowledge_sources_bot_id'), 'bot_knowledge_sources', ['bot_id'], unique=False)
    op.create_index(op.f('ix_bot_knowledge_sources_id'), 'bot_knowledge_sources', ['id'], unique=False)

    op.create_table(
        'bot_conversations',
        sa.Column('bot_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('visitor_name', sa.String(length=150), nullable=True),
        sa.Column('visitor_email', sa.String(length=255), nullable=True),
        sa.Column('channel', sa.String(length=50), nullable=False),
        sa.Column('language', sa.String(length=20), nullable=False),
        sa.Column('mood', sa.String(length=50), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('last_message_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['bot_id'], ['ai_bots.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bot_conversations_bot_id'), 'bot_conversations', ['bot_id'], unique=False)
    op.create_index(op.f('ix_bot_conversations_id'), 'bot_conversations', ['id'], unique=False)
    op.create_index(op.f('ix_bot_conversations_user_id'), 'bot_conversations', ['user_id'], unique=False)

    op.create_table(
        'bot_messages',
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('detected_mood', sa.String(length=50), nullable=True),
        sa.Column('message_metadata', sa.JSON(), nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['bot_conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bot_messages_conversation_id'), 'bot_messages', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_bot_messages_id'), 'bot_messages', ['id'], unique=False)

    connection = op.get_bind()
    now = datetime.utcnow()
    permissions_table = sa.table(
        'permissions',
        sa.column('name', sa.String),
        sa.column('code', sa.String),
        sa.column('module', sa.String),
        sa.column('description', sa.String),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
        sa.column('is_deleted', sa.Boolean),
    )
    role_permissions_table = sa.table(
        'role_permissions',
        sa.column('role_id', sa.Integer),
        sa.column('permission_id', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
        sa.column('is_deleted', sa.Boolean),
    )

    bot_permissions = [
        ('View Bots', 'bot.view', 'bots'),
        ('Create Bots', 'bot.create', 'bots'),
        ('Edit Bots', 'bot.edit', 'bots'),
        ('Delete Bots', 'bot.delete', 'bots'),
    ]

    existing_codes = {
        row[0]
        for row in connection.execute(sa.text("SELECT code FROM permissions WHERE code IN ('bot.view', 'bot.create', 'bot.edit', 'bot.delete')"))
    }
    rows_to_insert = [
        {
            'name': name,
            'code': code,
            'module': module,
            'description': f'Permission to {name.lower()}',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
            'is_deleted': False,
        }
        for name, code, module in bot_permissions
        if code not in existing_codes
    ]
    if rows_to_insert:
        op.bulk_insert(permissions_table, rows_to_insert)

    role_rows = connection.execute(sa.text("SELECT id, code FROM roles WHERE code IN ('SUPER_ADMIN', 'ADMIN')")).fetchall()
    permission_rows = connection.execute(sa.text("SELECT id, code FROM permissions WHERE code IN ('bot.view', 'bot.create', 'bot.edit', 'bot.delete')")).fetchall()
    permission_ids = {row.code: row.id for row in permission_rows}

    existing_role_permission_pairs = {
        (row.role_id, row.permission_id)
        for row in connection.execute(
            sa.text(
                "SELECT role_id, permission_id FROM role_permissions WHERE role_id IN "
                "(SELECT id FROM roles WHERE code IN ('SUPER_ADMIN', 'ADMIN'))"
            )
        ).fetchall()
    }

    role_permission_rows = []
    for role in role_rows:
        for permission_id in permission_ids.values():
            if (role.id, permission_id) in existing_role_permission_pairs:
                continue
            role_permission_rows.append(
                {
                    'role_id': role.id,
                    'permission_id': permission_id,
                    'is_active': True,
                    'created_at': now,
                    'updated_at': now,
                    'is_deleted': False,
                }
            )
    if role_permission_rows:
        op.bulk_insert(role_permissions_table, role_permission_rows)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text(
        "DELETE FROM role_permissions WHERE permission_id IN "
        "(SELECT id FROM permissions WHERE code IN ('bot.view', 'bot.create', 'bot.edit', 'bot.delete'))"
    ))
    connection.execute(sa.text(
        "DELETE FROM permissions WHERE code IN ('bot.view', 'bot.create', 'bot.edit', 'bot.delete')"
    ))

    op.drop_index(op.f('ix_bot_messages_id'), table_name='bot_messages')
    op.drop_index(op.f('ix_bot_messages_conversation_id'), table_name='bot_messages')
    op.drop_table('bot_messages')

    op.drop_index(op.f('ix_bot_conversations_user_id'), table_name='bot_conversations')
    op.drop_index(op.f('ix_bot_conversations_id'), table_name='bot_conversations')
    op.drop_index(op.f('ix_bot_conversations_bot_id'), table_name='bot_conversations')
    op.drop_table('bot_conversations')

    op.drop_index(op.f('ix_bot_knowledge_sources_id'), table_name='bot_knowledge_sources')
    op.drop_index(op.f('ix_bot_knowledge_sources_bot_id'), table_name='bot_knowledge_sources')
    op.drop_table('bot_knowledge_sources')

    op.drop_index(op.f('ix_ai_bots_slug'), table_name='ai_bots')
    op.drop_index(op.f('ix_ai_bots_industry'), table_name='ai_bots')
    op.drop_index(op.f('ix_ai_bots_id'), table_name='ai_bots')
    op.drop_index(op.f('ix_ai_bots_company_id'), table_name='ai_bots')
    op.drop_table('ai_bots')
