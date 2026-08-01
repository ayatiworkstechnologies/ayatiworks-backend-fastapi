"""add_client_record_flags

Revision ID: 20260802_000000
Revises: 20260527_170000
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260802_000000"
down_revision: Union[str, None] = "20260527_170000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'client_record_flags',
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('is_important', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('read_at', sa.DateTime(), nullable=True),
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_by', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['record_id'], ['client_module_records.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('record_id', 'user_id', name='uq_client_record_flags_record_user'),
    )
    op.create_index(op.f('ix_client_record_flags_record_id'), 'client_record_flags', ['record_id'], unique=False)
    op.create_index(op.f('ix_client_record_flags_user_id'), 'client_record_flags', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_client_record_flags_user_id'), table_name='client_record_flags')
    op.drop_index(op.f('ix_client_record_flags_record_id'), table_name='client_record_flags')
    op.drop_table('client_record_flags')
