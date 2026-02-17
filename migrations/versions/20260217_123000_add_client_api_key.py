"""add client api key column

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-17 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('clients', sa.Column('api_key', sa.String(64), unique=True, nullable=True))
    op.create_index('ix_clients_api_key', 'clients', ['api_key'])


def downgrade() -> None:
    op.drop_index('ix_clients_api_key', 'clients')
    op.drop_column('clients', 'api_key')
