"""update_client_mail_template_fields

Revision ID: c0506085a86b
Revises: b515d0598f2a
Create Date: 2026-02-18 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c0506085a86b'
down_revision: Union[str, None] = 'b515d0598f2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add to_email column
    # Use String(500) to allow multiple emails if needed, although user asked for "clint email"
    op.add_column('client_mail_templates', sa.Column('to_email', sa.String(length=500), nullable=True))
    
    # We won't drop from_email as it might have data, but we can make it nullable (it is already nullable)


def downgrade() -> None:
    op.drop_column('client_mail_templates', 'to_email')
