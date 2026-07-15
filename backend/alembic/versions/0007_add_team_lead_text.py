"""add_team_lead_text

Revision ID: 0007_add_team_lead_text
Revises: 0006_onboarding_flags
Create Date: 2026-07-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision: str = "0007_add_team_lead_text"
down_revision: Union[str, None] = "0006_onboarding_flags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vacancies", sa.Column("team_lead_text", sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column("vacancies", "team_lead_text")
