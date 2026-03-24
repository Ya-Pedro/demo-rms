\
\
\
\
\
   
from alembic import op
import sqlalchemy as sa

revision = '0004_vacancy_delegations'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        'vacancy_delegations',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('vacancy_id', sa.Integer(), sa.ForeignKey('vacancies.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('delegated_to_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('delegated_by_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        'ix_vacancy_delegations_active',
        'vacancy_delegations',
        ['vacancy_id', 'delegated_to_id', 'is_active'],
    )

def downgrade() -> None:
    op.drop_index('ix_vacancy_delegations_active', table_name='vacancy_delegations')
    op.drop_table('vacancy_delegations')