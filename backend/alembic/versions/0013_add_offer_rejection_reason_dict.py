"""add_offer_rejection_reason_dict

Revision ID: 0013_add_rejection_reason_dict
Revises: 0012_add_notes_table
Create Date: 2026-10-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision: str = "0013_add_rejection_reason_dict"
down_revision: Union[str, None] = "0012_add_notes_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_REASONS = [
    "Контроффер от текущего работодателя",
    "Не устроила заработная плата / условия",
    "Не подошел проект / стек технологий",
    "Личные / семейные обстоятельства",
    "Выбрал другое предложение",
    "Не подошел формат работы (удаленка/офис)",
    "Отказ без объяснения причин",
]


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("ALTER TYPE dictionarytype ADD VALUE IF NOT EXISTS 'OFFER_REJECTION_REASON'")
        op.execute("ALTER TYPE dictionarytype ADD VALUE IF NOT EXISTS 'offer_rejection_reason'")

    for i, reason in enumerate(DEFAULT_REASONS):
        escaped_reason = reason.replace("'", "''")
        op.execute(
            f"""
            INSERT INTO dictionaries (type, value, sort_order, is_active, created_at)
            SELECT 'OFFER_REJECTION_REASON', '{escaped_reason}', {i + 1}, true, NOW()
            WHERE NOT EXISTS (
                SELECT 1 FROM dictionaries 
                WHERE type IN ('OFFER_REJECTION_REASON', 'offer_rejection_reason') AND value = '{escaped_reason}'
            );
            """
        )


def downgrade() -> None:
    op.execute("DELETE FROM dictionaries WHERE type IN ('OFFER_REJECTION_REASON', 'offer_rejection_reason')")
