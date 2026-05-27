"""add_bot_knowledge_chunks

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-04-13 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'bot_knowledge_chunks',
        sa.Column('bot_id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding_json', sa.JSON(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(['source_id'], ['bot_knowledge_sources.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bot_knowledge_chunks_bot_id'), 'bot_knowledge_chunks', ['bot_id'], unique=False)
    op.create_index(op.f('ix_bot_knowledge_chunks_source_id'), 'bot_knowledge_chunks', ['source_id'], unique=False)
    op.create_index(op.f('ix_bot_knowledge_chunks_content_hash'), 'bot_knowledge_chunks', ['content_hash'], unique=False)
    op.create_index(op.f('ix_bot_knowledge_chunks_id'), 'bot_knowledge_chunks', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_bot_knowledge_chunks_id'), table_name='bot_knowledge_chunks')
    op.drop_index(op.f('ix_bot_knowledge_chunks_content_hash'), table_name='bot_knowledge_chunks')
    op.drop_index(op.f('ix_bot_knowledge_chunks_source_id'), table_name='bot_knowledge_chunks')
    op.drop_index(op.f('ix_bot_knowledge_chunks_bot_id'), table_name='bot_knowledge_chunks')
    op.drop_table('bot_knowledge_chunks')
