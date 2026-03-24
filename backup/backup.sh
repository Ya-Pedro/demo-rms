#!/bin/bash

echo "=== Запуск бэкапа: $(date) ==="

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_DIR="/tmp"
FILE_NAME="${POSTGRES_DB}_backup_${TIMESTAMP}.sql.gz"
FILE_PATH="${BACKUP_DIR}/${FILE_NAME}"

PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h "${DB_HOST}" -p 5432 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" | gzip > "${FILE_PATH}"

if [ $? -eq 0 ]; then
    echo "Дамп успешно создан: ${FILE_NAME}. Отправляем в S3..."
    
    export AWS_ACCESS_KEY_ID="${S3_ACCESS_KEY}"
    export AWS_SECRET_ACCESS_KEY="${S3_SECRET_KEY}"
    export AWS_DEFAULT_REGION="ru-central1"

    aws --endpoint-url=https://storage.yandexcloud.net s3 cp "${FILE_PATH}" "s3://${S3_BUCKET_NAME}/${FILE_NAME}"

    if [ $? -eq 0 ]; then
        echo "✅ Бэкап успешно загружен в Яндекс S3!"
    else
        echo "❌ Ошибка при загрузке в S3."
    fi
else
    echo "❌ Ошибка при создании дампа базы данных."
fi

rm -f "${FILE_PATH}"
echo "=== Процесс завершен ==="
echo ""
