#!/bin/sh
set -e

echo "⏳ Применяем миграции Alembic..."
alembic upgrade head
echo "✅ Миграции применены"

echo "🚀 Запускаем сервер..."
exec uvicorn server:app --host 0.0.0.0 --port 8000