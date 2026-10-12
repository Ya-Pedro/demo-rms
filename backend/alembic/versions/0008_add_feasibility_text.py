"""add_feasibility_text

Revision ID: 0008_add_feasibility_text
Revises: fa54c93fa224
Create Date: 2026-10-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision: str = "0008_add_feasibility_text"
down_revision: Union[str, None] = "fa54c93fa224"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vacancies", sa.Column("feasibility_text", sa.String(255), nullable=True, comment="ТЭО проекта (текст)"))
    op.execute(
        "UPDATE vacancies v SET feasibility_text = d.value "
        "FROM dictionaries d "
        "WHERE v.feasibility_id = d.id AND v.feasibility_text IS NULL"
    )


def downgrade() -> None:
    op.drop_column("vacancies", "feasibility_text")
