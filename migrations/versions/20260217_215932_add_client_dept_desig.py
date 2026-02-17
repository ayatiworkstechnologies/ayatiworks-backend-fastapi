"""add_client_dept_desig

Revision ID: 449c94bfa744
Revises: 4c8e452c2f2c
Create Date: 2026-02-17 21:59:32.792075

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '449c94bfa744'
down_revision: Union[str, None] = '4c8e452c2f2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use a connection to interact with data
    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)

    try:
        # 1. Get the main company ID
        company = session.execute(sa.text("SELECT id FROM companies LIMIT 1")).first()
        if not company:
            return
        
        company_id = company[0]

        # 2. Ensure "Client" Role exists
        role = session.execute(sa.text("SELECT id FROM roles WHERE code = 'CLIENT'")).first()
        if not role:
            session.execute(sa.text(
                "INSERT INTO roles (name, code, scope, is_system, is_active, company_id, created_at, updated_at) "
                "VALUES ('Client', 'CLIENT', 'company', 1, 1, :cid, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ), {"cid": company_id})

        # 3. Ensure "Client" Department exists
        dept = session.execute(sa.text("SELECT id FROM departments WHERE name = 'Client' AND company_id = :cid"), {"cid": company_id}).first()
        if not dept:
            session.execute(sa.text(
                "INSERT INTO departments (name, code, company_id, level, created_at, updated_at) "
                "VALUES ('Client', 'CLT', :cid, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ), {"cid": company_id})
            session.commit() # Commit to get the ID in next select if needed, or use RETURNING
            dept = session.execute(sa.text("SELECT id FROM departments WHERE name = 'Client' AND company_id = :cid"), {"cid": company_id}).first()

        dept_id = dept[0]

        # 4. Ensure "Client" Designation exists
        desig = session.execute(sa.text("SELECT id FROM designations WHERE name = 'Client' AND department_id = :did"), {"did": dept_id}).first()
        if not desig:
            session.execute(sa.text(
                "INSERT INTO designations (name, code, department_id, level, created_at, updated_at) "
                "VALUES ('Client', 'CLT-C', :did, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ), {"did": dept_id})
        
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def downgrade() -> None:
    pass
