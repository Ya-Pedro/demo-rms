"""initial_schema — все таблицы RMS

Revision ID: 0001_initial
Revises: 
Create Date: 2026-03-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Создаём все таблицы RMS."""
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Создаем ENUM типы (безопасно)
    if is_postgres:
        op.execute("""
            DO $$
            BEGIN
                CREATE TYPE userrole AS ENUM ('superadmin', 'admin', 'recruiter');
            EXCEPTION WHEN duplicate_object THEN
                NULL;
            END
            $$;
        """)
        op.execute("""
            DO $$
            BEGIN
                CREATE TYPE dictionarytype AS ENUM (
                    'specialist_level', 'vacancy_status', 'it_role', 'project',
                    'source', 'employment_type', 'replacement_type', 'feasibility',
                    'block', 'admin_manager', 'team_lead', 'internal_transfer', 'city'
                );
            EXCEPTION WHEN duplicate_object THEN
                NULL;
            END
            $$;
        """)

    # 2. Таблица: users
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column(
            "role",
            # Создаем как String БЕЗ server_default, чтобы избежать конфликта типов при конвертации
            sa.String(50) if is_postgres else sa.Enum("superadmin", "admin", "recruiter", name="userrole"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("is_temporary_password", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Меняем тип role на ENUM и ТОЛЬКО ПОТОМ ставим default
    if is_postgres:
        op.execute("ALTER TABLE users ALTER COLUMN role TYPE userrole USING role::userrole")
        op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'recruiter'::userrole")

    # 3. Таблица: dictionaries
    op.create_table(
        "dictionaries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "type",
            sa.String(50) if is_postgres else sa.Enum(name="dictionarytype"),
            nullable=False,
        ),
        sa.Column("value", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dictionaries_id", "dictionaries", ["id"], unique=False)
    op.create_index("ix_dictionaries_type", "dictionaries", ["type"], unique=False)

    if is_postgres:
        op.execute("ALTER TABLE dictionaries ALTER COLUMN type TYPE dictionarytype USING type::dictionarytype")

    # 4. Таблица: vacancies
    op.create_table(
        "vacancies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vacancy_id", sa.String(50), nullable=True),
        sa.Column("open_date", sa.Date(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=True, server_default=sa.text("1")),
        sa.Column("level_id", sa.Integer(), nullable=True),
        sa.Column("position_name", sa.String(255), nullable=False),
        sa.Column("status_id", sa.Integer(), nullable=True),
        sa.Column("it_role_id", sa.Integer(), nullable=True),
        sa.Column("admin_manager_id", sa.Integer(), nullable=True),
        sa.Column("team_lead_id", sa.Integer(), nullable=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("resume_at_customer", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("resume_approved", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("interviews_fact", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("interviews_plan", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("offer_made", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("city_id", sa.Integer(), nullable=True),
        sa.Column("city_text", sa.String(100), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("internal_transfer_id", sa.Integer(), nullable=True),
        sa.Column("status_changed_at", sa.Date(), nullable=True),
        sa.Column("close_date", sa.Date(), nullable=True),
        sa.Column("candidate_name", sa.String(255), nullable=True),
        sa.Column("candidate_company", sa.String(255), nullable=True),
        sa.Column("replacement_type_id", sa.Integer(), nullable=True),
        sa.Column("ex_employee_name", sa.String(255), nullable=True),
        sa.Column("unit_id", sa.String(50), nullable=True),
        sa.Column("employment_type_id", sa.Integer(), nullable=True),
        sa.Column("feasibility_id", sa.Integer(), nullable=True),
        sa.Column("iqhr_link", sa.String(500), nullable=True),
        sa.Column("recruiter_id", sa.Integer(), nullable=True),
        sa.Column("block_id", sa.Integer(), nullable=True),
        sa.Column("hold_days", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("salary_gross", sa.Integer(), nullable=True),
        sa.Column("resumes_sent_cnt", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("candidates_agreed_cnt", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("interviews_planned_cnt", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("interviews_conducted_cnt", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("counters_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["level_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["status_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["it_role_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["admin_manager_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["team_lead_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["city_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["internal_transfer_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["replacement_type_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["employment_type_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["feasibility_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["block_id"], ["dictionaries.id"]),
        sa.ForeignKeyConstraint(["recruiter_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vacancies_id", "vacancies", ["id"], unique=False)
    op.create_index("ix_vacancies_vacancy_id", "vacancies", ["vacancy_id"], unique=False)

    # 5. Таблица: weekly_reports
    op.create_table(
        "weekly_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("vacancy_id", sa.Integer(), nullable=False),
        sa.Column("report_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("week_start", sa.Date(), nullable=True),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("resumes_sent", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("candidates_agreed", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("interviews_planned", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("interviews_conducted", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("offer_made", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["vacancy_id"], ["vacancies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_weekly_reports_id", "weekly_reports", ["id"], unique=False)


def downgrade() -> None:
    """Удаляем все таблицы в обратном порядке."""
    op.drop_table("weekly_reports")
    op.drop_table("vacancies")
    op.drop_table("dictionaries")
    op.drop_table("users")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS userrole CASCADE")
        op.execute("DROP TYPE IF EXISTS dictionarytype CASCADE")
