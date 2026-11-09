"""add_recommender_name

Revision ID: 0016_add_recommender_name
Revises: 0015_add_system_settings
Create Date: 2026-11-09

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op


revision: str = "0016_add_recommender_name"
down_revision: Union[str, None] = "0015_add_system_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vacancies",
        sa.Column("recommender_name", sa.Text(), nullable=True, comment="ФИО рекомендателя")
    )


def downgrade() -> None:
    op.drop_column("vacancies", "recommender_name")
