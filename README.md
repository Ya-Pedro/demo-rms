# RMS — Recruitment Management System
### Инструкция по развёртыванию в OpenShift Local (CRC)

Репозиторий содержит полный стек Recruitment Management System, адаптированный под политику безопасности **SCC Restricted**: все контейнеры запускаются от non-root пользователей на непривилегированных портах.

---

## Требования

- OpenShift Local (CRC) — запущен и авторизован (`crc start`, `oc login`)
- Docker или Podman
- Утилита `oc` в `$PATH`
- Проект `demo-rms` создан в кластере: `oc new-project demo-rms`

---

## Шаг 1 — Сборка и публикация образов

> **Важно:** Сборку необходимо выполнять с флагом `--provenance=false`. Без него BuildKit добавляет аттестации происхождения, которые реестр OpenShift не может разобрать и возвращает ошибку 500.

Выполните из корня репозитория:

```bash
# Адрес внутреннего реестра кластера
REGISTRY=$(oc registry info)

# Бэкенд
docker build --provenance=false -t backend:latest ./backend
docker tag backend:latest $REGISTRY/demo-rms/backend:latest
docker push $REGISTRY/demo-rms/backend:latest

# Фронтенд
docker build --provenance=false -t frontend:latest ./frontend
docker tag frontend:latest $REGISTRY/demo-rms/frontend:latest
docker push $REGISTRY/demo-rms/frontend:latest

# Сервис бэкапов
docker build --provenance=false -t db-backup:latest ./backup
docker tag db-backup:latest $REGISTRY/demo-rms/db-backup:latest
docker push $REGISTRY/demo-rms/db-backup:latest
```

---

## Шаг 2 — Развёртывание инфраструктуры

Применяем все манифесты одной командой. `oc apply` автоматически создаст PVC, Secret, ConfigMap, Deployment, Service и Edge-маршруты:

```bash
cd openshift-manifests/
oc apply -f .
```

Дождитесь, пока все поды перейдут в статус `1/1 Running`:

```bash
oc get pods -w
```

---

## Шаг 3 — Инициализация базы данных

> **Обязательный шаг.** Тома базы данных разворачиваются пустыми — без этой команды приложение не будет работать.

```bash
oc exec -it deployment/backend -- python seed.py
```

Что делает скрипт:

1. Пересоздаёт все таблицы PostgreSQL по моделям SQLAlchemy.
2. Создаёт кастомные типы ENUM на уровне СУБД (`userrole`, `dictionarytype`).
3. Загружает справочники: ИТ-роли, проекты, ТЭО, блоки — всё необходимое для выпадающих списков интерфейса.
4. Создаёт два системных аккаунта с правами суперадминистратора для первоначального входа.

---

## Первый вход в систему

Добавьте домен в `/etc/hosts`:

```
127.0.0.1   rms.ittori.ru
```

| Параметр | Значение |
|----------|----------|
| URL | `https://rms.ittori.ru` |
| Логин | `admin1@rms-system.ru` или `admin2@rms-system.ru` |
| Пароль | `admin123` |

### Роли пользователей

| Роль | Доступ |
|------|--------|
| `SUPERADMIN` | Полное администрирование: пользователи, словари, настройки |
| `ADMIN` | Управление проектами и координация |
| `RECRUITER` | Ведение вакансий и работа с кандидатами |

---

## ⚠️ Безопасность — обязательно после первого входа

Дефолтные аккаунты созданы **только** для первоначального доступа. Сразу после входа:

1. Создайте собственные именные учётные записи с ролью `SUPERADMIN`.
2. Войдите под новыми аккаунтами.
3. Удалите дефолтных пользователей `admin1` и `admin2`.

---

## Структура репозитория

```
.
├── backend/                  # Исходный код бэкенда (FastAPI)
│   ├── alembic/versions/     # Миграции БД
│   └── seed.py               # Скрипт инициализации данных
├── frontend/                 # Исходный код фронтенда
│   ├── Dockerfile            # Запуск от пользователя 1001, порт 8080
│   └── nginx.conf            # Конфиг без SSL и секции Grafana
├── backup/                   # Сервис резервного копирования БД
├── openshift-manifests/      # YAML-манифесты для oc apply
│   ├── 01_shared.yaml
│   ├── 02_databases.yaml
│   ├── 03_backend_stack.yaml
│   ├── 04_frontend.yaml
│   └── 05_monitoring.yaml
└── README.md
```

> Переменные окружения и секреты хранятся в нативных объектах OpenShift (`ConfigMap` / `Secret`). Файлы `.env` и `.env.production` в репозиторий не включаются — они перечислены в `.gitignore`.
