\
\
\
\
\
\
\
\
\
\
\
\
   
from alembic import op
import sqlalchemy as sa

revision = '0006_onboarding_flags'
down_revision = '0005_vacancy_history'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'is_vacancies_tour_completed',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )
    op.add_column(
        'users',
        sa.Column(
            'is_reports_tour_completed',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )

def downgrade() -> None:
    op.drop_column('users', 'is_reports_tour_completed')
    op.drop_column('users', 'is_vacancies_tour_completed')