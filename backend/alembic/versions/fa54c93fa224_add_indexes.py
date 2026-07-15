"""add_indexes

Revision ID: fa54c93fa224
Revises: 0007_add_team_lead_text
Create Date: 2026-07-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision: str = "fa54c93fa224"
down_revision: Union[str, None] = "0007_add_team_lead_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
