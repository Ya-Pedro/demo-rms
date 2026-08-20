#!/bin/sh
set -e

echo "⏳ Применяем миграции Alembic..."

# Проверяем: если таблицы уже существуют (например, БД создана вручную),
# но в alembic_version нет ни одной записи — стемпим текущую ревизию,
# чтобы Alembic не пытался создать таблицы заново.
TABLES_EXIST=$(python3 -c "
import asyncio, os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    url = os.environ.get('DATABASE_URL', '')
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        # Проверяем есть ли таблица users
        result = await conn.execute(text(
            \"SELECT COUNT(*) FROM information_schema.tables \"
            \"WHERE table_schema='public' AND table_name='users'\"
        ))
        has_tables = result.scalar() > 0

        # Проверяем есть ли запись в alembic_version
        has_version = False
        try:
            r2 = await conn.execute(text('SELECT COUNT(*) FROM alembic_version'))
            has_version = r2.scalar() > 0
        except Exception:
            pass

        print('stamp' if has_tables and not has_version else 'ok')
    await engine.dispose()

asyncio.run(check())
" 2>/dev/null || echo "ok")

if [ "$TABLES_EXIST" = "stamp" ]; then
    echo "⚠️  Таблицы уже существуют, но alembic_version пуста — выполняем stamp head..."
    alembic stamp head
    echo "✅ Stamp выполнен"
fi

alembic upgrade head
echo "✅ Миграции применены"

echo "🚀 Запускаем сервер..."
exec uvicorn server:app --host 0.0.0.0 --port 8000