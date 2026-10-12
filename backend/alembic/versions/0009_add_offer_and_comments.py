"""add_offer_and_comments

Revision ID: 0009_add_offer_and_comments
Revises: 0008_add_feasibility_text
Create Date: 2026-10-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision: str = "0009_add_offer_and_comments"
down_revision: Union[str, None] = "0008_add_feasibility_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columns for vacancies
    op.add_column("vacancies", sa.Column("offer_accepted_cnt", sa.Integer(), server_default="0", nullable=False, comment="Кол-во принятых офферов"))
    op.add_column("vacancies", sa.Column("offer_rejection_reason", sa.String(255), nullable=True, comment="Причина отказа от оффера"))
    op.add_column("vacancies", sa.Column("comment", sa.Text(), nullable=True, comment="Комментарий"))

    # Columns for weekly_reports
    op.add_column("weekly_reports", sa.Column("offer_accepted", sa.Integer(), server_default="0", nullable=False, comment="Оффер принят"))
    op.add_column("weekly_reports", sa.Column("offer_rejection_reason", sa.String(255), nullable=True, comment="Причина отказа от оффера"))
    op.add_column("weekly_reports", sa.Column("comment", sa.Text(), nullable=True, comment="Комментарий"))


def downgrade() -> None:
    op.drop_column("weekly_reports", "comment")
    op.drop_column("weekly_reports", "offer_rejection_reason")
    op.drop_column("weekly_reports", "offer_accepted")

    op.drop_column("vacancies", "comment")
    op.drop_column("vacancies", "offer_rejection_reason")
    op.drop_column("vacancies", "offer_accepted_cnt")
