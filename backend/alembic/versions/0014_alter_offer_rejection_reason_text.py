"""alter_offer_rejection_reason_text

Revision ID: 0014_alter_rejection_reason_text
Revises: 0013_add_rejection_reason_dict
Create Date: 2026-11-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision: str = "0014_alter_rejection_reason_text"
down_revision: Union[str, None] = "0013_add_rejection_reason_dict"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("vacancies", "offer_rejection_reason", type_=sa.Text(), existing_type=sa.String(255), nullable=True)
    op.alter_column("weekly_reports", "offer_rejection_reason", type_=sa.Text(), existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    op.alter_column("vacancies", "offer_rejection_reason", type_=sa.String(255), existing_type=sa.Text(), nullable=True)
    op.alter_column("weekly_reports", "offer_rejection_reason", type_=sa.String(255), existing_type=sa.Text(), nullable=True)
