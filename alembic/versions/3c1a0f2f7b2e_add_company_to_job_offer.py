"""add company to job_offer

Revision ID: 3c1a0f2f7b2e
Revises: 2b7d5b3d9f1a
Create Date: 2026-03-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3c1a0f2f7b2e"
down_revision: Union[str, Sequence[str], None] = "2b7d5b3d9f1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("job_offer", sa.Column("company", sa.String(), nullable=True))
    op.create_index(op.f("ix_job_offer_company"), "job_offer", ["company"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_job_offer_company"), table_name="job_offer")
    op.drop_column("job_offer", "company")
