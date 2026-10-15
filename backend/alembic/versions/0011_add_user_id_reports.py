"""add_user_id_to_weekly_reports

Revision ID: 0011_add_user_id_reports
Revises: 0010_add_co_recruiter
Create Date: 2026-10-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision: str = "0011_add_user_id_reports"
down_revision: Union[str, None] = "0010_add_co_recruiter"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "weekly_reports",
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="Автор отчёта",
        ),
    )
    op.create_index("ix_weekly_reports_user_id", "weekly_reports", ["user_id"], unique=False)

    # Backfill user_id from vacancies.recruiter_id for existing reports
    op.execute(
        """
        UPDATE weekly_reports wr
        SET user_id = v.recruiter_id
        FROM vacancies v
        WHERE wr.vacancy_id = v.id AND v.recruiter_id IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.drop_index("ix_weekly_reports_user_id", table_name="weekly_reports")
    op.drop_column("weekly_reports", "user_id")
