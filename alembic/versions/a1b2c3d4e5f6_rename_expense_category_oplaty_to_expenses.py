"""rename expense category oplaty to expenses

Revision ID: a1b2c3d4e5f6
Revises: e65bf023f92e
Create Date: 2026-05-25

"""
from typing import Sequence, Union
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'e65bf023f92e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE expensecategory RENAME VALUE 'OPLATY' TO 'EXPENSES'")


def downgrade() -> None:
    op.execute("ALTER TYPE expensecategory RENAME VALUE 'EXPENSES' TO 'OPLATY'")
