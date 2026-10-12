"""add_co_recruiter

Revision ID: 0010_add_co_recruiter
Revises: 0009_add_offer_and_comments
Create Date: 2026-10-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision: str = "0010_add_co_recruiter"
down_revision: Union[str, None] = "0009_add_offer_and_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vacancies",
        sa.Column(
            "co_recruiter_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="Дополнительный рекрутер",
        ),
    )


def downgrade() -> None:
    op.drop_column("vacancies", "co_recruiter_id")
