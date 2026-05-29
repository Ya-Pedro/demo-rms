"""add 2fa fields to users

Revision ID: 0003
Revises: 0002_refresh_tokens_audit_log
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002_refresh_tokens_audit_log'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('totp_secret', sa.String(64), nullable=True))
    op.add_column('users', sa.Column(
        'is_2fa_enabled',
        sa.Boolean(),
        nullable=False,
        # Исправлено: '0' — невалидное значение для Boolean в PostgreSQL.
        # Нужно 'false' (PostgreSQL) или sa.text('false') для кросс-БД совместимости.
        server_default=sa.text('false'),
    ))


def downgrade() -> None:
    op.drop_column('users', 'is_2fa_enabled')
    op.drop_column('users', 'totp_secret')
