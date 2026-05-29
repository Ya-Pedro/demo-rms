"""Add vacancy_history table

Revision ID: 0005_vacancy_history
Revises: 0004_vacancy_delegations
Create Date: 2026-03-11
"""
from alembic import op
import sqlalchemy as sa

revision = '0005_vacancy_history'
down_revision = '0004_vacancy_delegations'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'vacancy_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('vacancy_id', sa.Integer(),
                  sa.ForeignKey('vacancies.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('action_type', sa.String(20), nullable=False, index=True),
        sa.Column('changes', sa.Text, nullable=True),
        sa.Column('vacancy_snapshot', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table('vacancy_history')
