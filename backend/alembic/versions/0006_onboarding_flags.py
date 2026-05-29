"""Add onboarding tour completion flags to users

Revision ID: 0006_onboarding_flags
Revises: 0005_vacancy_history
Create Date: 2026-03-16

Добавляет два булевых флага в таблицу users:
  - is_vacancies_tour_completed  — рекрутер прошёл/закрыл тур на вкладке «Вакансии»
  - is_reports_tour_completed    — рекрутер прошёл/закрыл тур на вкладке «Отчёты»

Оба поля nullable=False, server_default='false' — существующие записи
получают значение FALSE без ручного UPDATE.
"""
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
