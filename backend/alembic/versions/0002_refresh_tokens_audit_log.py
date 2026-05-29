"""Add refresh_tokens and audit_log tables

Revision ID: 0002_refresh_tokens_audit_log
Revises: 0001_initial_schema
Create Date: 2026-03-01
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0002_refresh_tokens_audit_log'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('token', sa.String(128), unique=True, nullable=False, index=True),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now()),
        sa.Column('created_from_ip', sa.String(50), nullable=True),
    )
    # Этот индекс оставляем, так как в таблице выше index=True для user_id не стоял
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])

    # ── audit_log ─────────────────────────────────────────────────────────────
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('timestamp', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        
        # УБРАНО: index=True (потому что индекс создается явно ниже)
        sa.Column('user_id', sa.Integer(), nullable=True),
        
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('user_role', sa.String(50), nullable=True),
        
        # УБРАНО: index=True (потому что индекс создается явно ниже)
        sa.Column('action', sa.String(100), nullable=False),
        
        sa.Column('resource', sa.String(100), nullable=True),
        sa.Column('resource_id', sa.String(50), nullable=True),
        sa.Column('method', sa.String(10), nullable=True),
        sa.Column('path', sa.String(500), nullable=True),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(50), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
    )
    
    # Теперь эти команды отработают без ошибки "DuplicateTableError"
    op.create_index('ix_audit_log_timestamp', 'audit_log', ['timestamp'])
    op.create_index('ix_audit_log_action', 'audit_log', ['action'])
    op.create_index('ix_audit_log_user_id', 'audit_log', ['user_id'])


def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('refresh_tokens')
