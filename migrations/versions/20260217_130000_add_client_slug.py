"""Add slug to clients table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-17 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("clients", sa.Column("slug", sa.String(255), nullable=True))
    op.create_index("ix_clients_slug", "clients", ["slug"], unique=True)

    # Auto-populate slug from existing client names
    conn = op.get_bind()
    clients = conn.execute(sa.text("SELECT id, name FROM clients")).fetchall()
    import re
    for client in clients:
        slug = client[1].lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[\s_]+', '-', slug)
        conn.execute(
            sa.text("UPDATE clients SET slug = :slug WHERE id = :id"),
            {"slug": slug, "id": client[0]}
        )


def downgrade() -> None:
    op.drop_index("ix_clients_slug", table_name="clients")
    op.drop_column("clients", "slug")
