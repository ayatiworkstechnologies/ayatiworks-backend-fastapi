"""add email fields to client mail template

Revision ID: 4c8e452c2f2c
Revises: d4e5f6a7b8c9
Create Date: 2026-02-17 21:43:16.473872

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c8e452c2f2c'
down_revision: Union[str, None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('client_mail_templates', sa.Column('from_email', sa.String(length=255), nullable=True))
    op.add_column('client_mail_templates', sa.Column('cc_email', sa.JSON(), nullable=True))
    op.add_column('client_mail_templates', sa.Column('bcc_email', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('client_mail_templates', 'bcc_email')
    op.drop_column('client_mail_templates', 'cc_email')
    op.drop_column('client_mail_templates', 'from_email')
