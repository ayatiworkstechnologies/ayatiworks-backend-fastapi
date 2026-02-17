"""Add mail_template_id to client_modules

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-17 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add mail_template_id column to client_modules table
    op.add_column('client_modules', sa.Column('mail_template_id', sa.Integer(), nullable=True))
    
    # Create foreign key constraint
    op.create_foreign_key(
        'fk_client_modules_mail_template_id', 
        'client_modules', 'client_mail_templates', 
        ['mail_template_id'], ['id'], 
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remove foreign key constraint
    op.drop_constraint('fk_client_modules_mail_template_id', 'client_modules', type_='foreignkey')
    
    # Remove column
    op.drop_column('client_modules', 'mail_template_id')
