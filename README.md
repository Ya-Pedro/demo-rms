# RMS - Recruitment Management System

Внутренняя HR система для управления вакансиями.

## Требования

- Docker (для PostgreSQL)
- Python 3.11+
- Node.js 18+

## Быстрый старт

### 1. Запуск PostgreSQL

```bash
cd /app
docker-compose up -d
```

PostgreSQL будет доступен на `localhost:5432`:
- User: `postgres`
- Password: `postgres`
- Database: `rms_db`

### 2. Запуск Backend

```bash
cd /app/backend

# Создание виртуального окружения (опционально)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или venv\Scripts\activate  # Windows

# Установка зависимостей
pip install -r requirements.txt

# Инициализация базы данных и создание тестовых данных
python seed.py

# Запуск сервера
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Backend будет доступен на `http://localhost:8001`
API документация: `http://localhost:8001/docs`

### 3. Запуск Frontend

```bash
cd /app/frontend

# Установка зависимостей
yarn install

# Запуск dev сервера
yarn start
```

Frontend будет доступен на `http://localhost:3000`

## Учетные данные для входа

После запуска `seed.py` в консоли будут выведены учетные данные:

```
[MOCK EMAIL] Администратор создан
Login: admin@rms-system.ru
Pass: admin123
```

Также будут созданы рекрутеры:
- recruiter1@rms-system.ru / recruiter1
- recruiter2@rms-system.ru / recruiter2
- recruiter3@rms-system.ru / recruiter3

## Структура проекта

```
/app/
├── docker-compose.yml    # PostgreSQL конфигурация
├── backend/
│   ├── server.py         # Главный FastAPI приложение
│   ├── database.py       # Подключение к PostgreSQL
│   ├── models.py         # SQLAlchemy модели
│   ├── schemas.py        # Pydantic схемы
│   ├── auth.py           # JWT аутентификация
│   ├── seed.py           # Скрипт инициализации данных
│   ├── requirements.txt  # Python зависимости
│   └── routers/
│       ├── auth_router.py
│       ├── users_router.py
│       ├── dictionaries_router.py
│       ├── vacancies_router.py
│       ├── weekly_reports_router.py
│       └── export_router.py
└── frontend/
    ├── package.json
    └── src/
        ├── App.js        # Главный компонент с роутингом
        ├── App.css       # Стили
        └── pages/
            ├── LoginPage.js
            ├── DashboardPage.js    # Главная таблица вакансий
            ├── DictionaryPage.js   # Управление справочниками
            └── UsersPage.js        # Управление пользователями
```

## API Endpoints

### Аутентификация
- `POST /api/auth/login` - Вход в систему
- `GET /api/auth/me` - Текущий пользователь

### Пользователи (admin/superadmin)
- `GET /api/users` - Список пользователей
- `POST /api/users` - Создать пользователя (пароль генерируется автоматически)
- `PATCH /api/users/{id}` - Обновить пользователя
- `DELETE /api/users/{id}` - Деактивировать пользователя

### Справочники
- `GET /api/dictionaries` - Список элементов справочника
- `GET /api/dictionaries/types` - Типы справочников
- `GET /api/dictionaries/by-type/{type}` - Элементы по типу
- `POST /api/dictionaries` - Создать элемент
- `PATCH /api/dictionaries/{id}` - Обновить элемент
- `DELETE /api/dictionaries/{id}` - Деактивировать элемент

### Вакансии
- `GET /api/vacancies` - Список вакансий (с фильтрами и недельными данными)
- `GET /api/vacancies/{id}` - Получить вакансию
- `POST /api/vacancies` - Создать вакансию
- `PATCH /api/vacancies/{id}` - Обновить вакансию
- `DELETE /api/vacancies/{id}` - Удалить вакансию

### Еженедельные отчеты
- `GET /api/weekly-reports/weeks` - Доступные недели
- `GET /api/weekly-reports` - Список отчетов
- `POST /api/weekly-reports` - Создать отчет
- `PATCH /api/weekly-reports/{id}` - Обновить отчет

### Экспорт
- `GET /api/export/vacancies` - Экспорт в Excel (.xlsx)

## Тестовые данные

Скрипт `seed.py` создает:
- 1 суперадминистратора
- 3 рекрутера
- Все типы справочников с примерами
- 25 вакансий с рандомными данными
- Еженедельные отчеты для недель W40-W52 (2024) и W1-W10 (2025)

## Переменные окружения

### Backend (.env)
```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/rms_db
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=http://localhost:8001
```
# job_reg
