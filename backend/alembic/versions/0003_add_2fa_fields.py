\
\
\
\
\
   
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
                                                                         
                                                                                     
        server_default=sa.text('false'),
    ))

def downgrade() -> None:
    op.drop_column('users', 'is_2fa_enabled')
    op.drop_column('users', 'totp_secret')