"""add_client_module_records_sort_index

Adds a composite index covering the (module_id, created_at, id) ORDER BY used
by list_module_records, so MySQL can satisfy the query from the index instead
of a filesort — filesort on this table was exceeding sort_buffer_size once
record/JSON-payload counts grew ("Out of sort memory").

Revision ID: 20260802_010000
Revises: 20260802_000000
Create Date: 2026-08-02 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "20260802_010000"
down_revision: Union[str, None] = "20260802_000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_client_module_records_module_created_id",
        "client_module_records",
        ["module_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_client_module_records_module_created_id", table_name="client_module_records")
