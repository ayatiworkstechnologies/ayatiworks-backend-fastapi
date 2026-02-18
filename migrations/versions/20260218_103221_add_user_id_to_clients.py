"""add_user_id_to_clients

Revision ID: b515d0598f2a
Revises: 449c94bfa744
Create Date: 2026-02-18 10:32:21.528740

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b515d0598f2a'
down_revision: Union[str, None] = '449c94bfa744'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column to clients table for direct user-client linking
    op.add_column('clients', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_clients_user_id',
        'clients', 'users',
        ['user_id'], ['id']
    )
    op.create_index('ix_clients_user_id', 'clients', ['user_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_clients_user_id', table_name='clients')
    op.drop_constraint('fk_clients_user_id', 'clients', type_='foreignkey')
    op.drop_column('clients', 'user_id')
