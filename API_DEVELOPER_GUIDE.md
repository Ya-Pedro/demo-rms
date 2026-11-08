# Руководство разработчика по интеграции с RMS API

Документ содержит техническое описание программного интерфейса (REST API) системы управления рекрутментом RMS (Recruitment Management System). Руководство предназначено для разработчиков внешних систем (1С:ЗУП, BI-системы, корпоративные порталы, кадровые сервисы), а также инженеров, разрабатывающих клиентские модули.

---

## 1. Общие сведения и сетевой доступ

### 1.1. Базовые URL

| Окружение | Базовый URL | Назначение |
|---|---|---|
| Production / Тестовый стенд | `https://rms.ittori.online` | Основной боевой/тестовый стенд |
| Локальная разработка (Nginx) | `http://localhost` | Доступ через локальный веб-сервер |
| Локальная разработка (Backend) | `http://localhost:8000` | Прямой доступ к Uvicorn/FastAPI |

Все эндпоинты API начинаются с префикса `/api`.

### 1.2. Форматы данных и кодировка

- Формат передачи тела запросов и ответов по умолчанию: `application/json; charset=utf-8`.
- Формат дат: `YYYY-MM-DD` (стандарт ISO 8601, например: `2026-11-08`).
- Формат даты и времени: `YYYY-MM-DDTHH:MM:SSZ` (ISO 8601, UTC).
- Кодировка текстовых данных: `UTF-8`.
- Экспорт в CSV: разделитель точка с запятой (`;`), кодировка UTF-8 с сигнатурой BOM (`\uFEFF`) для корректного открытия в Microsoft Excel.
- Экспорт в Excel: формат Office Open XML (`.xlsx`).

### 1.3. Интерактивная спецификация OpenAPI

- Swagger UI: `https://rms.ittori.online/api/docs`
- ReDoc UI: `https://rms.ittori.online/api/redoc`
- OpenAPI JSON Schema: `https://rms.ittori.online/api/openapi.json`

---

## 2. Аутентификация и безопасность

В RMS реализовано два независимых механизма аутентификации в зависимости от сценария использования.

### 2.1. Сервисные токены интеграции (Integration Tokens)

Используются внешними корпоративными системами (1С:ЗУП, BI-системы, фоновые скрипты выгрузки данных) для доступа к эндпоинтам `/api/integration/*`.

- Токен создается администратором в интерфейсе системы или через API.
- Токен является статическим и действует до момента его ручной деактивации или отзыва.
- Передача токена поддерживается двумя способами:
  1. Заголовок `X-API-Key: <token>`
  2. Заголовок `Authorization: Bearer <token>`

Пример запроса с сервисным токеном:
```http
GET /api/integration/vacancies?limit=100 HTTP/1.1
Host: rms.ittori.online
X-API-Key: <YOUR_API_TOKEN>
```

### 2.2. Пользовательские JWT-токены (User Bearer Tokens)

Используются веб-интерфейсом и клиентскими приложениями от имени зарегистрированных пользователей.

1. **Получение токена (Login):**
   - `POST /api/auth/login`
   - Content-Type: `application/json`
   - Тело запроса:
     ```json
     {
       "email": "user@company.ru",
       "password": "Password123"
     }
     ```
   - Тело ответа:
     ```json
     {
       "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
       "refresh_token": "ab2ee7993e64e5b95f6f1d...",
       "token_type": "bearer",
       "is_temporary_password": false,
       "requires_2fa": false,
       "user": {
         "id": 1,
         "email": "user@company.ru",
         "full_name": "Иванов Иван Иванович",
         "role": "recruiter"
       }
     }
     ```

2. **Использование токена:**
   Во всех последующих запросах токен передается в заголовке:
   ```http
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsIn...
   ```

3. **Обновление токена (Refresh):**
   - `POST /api/auth/refresh`
   - Тело запроса:
     ```json
     {
       "refresh_token": "ab2ee7993e64e5b95f6f1d..."
     }
     ```

4. **Завершение сессии (Logout):**
   - `POST /api/auth/logout` — деактивирует текущую пользовательскую сессию в Redis.

### 2.3. Ролевая модель доступа (RBAC)

- `SUPERADMIN` — полный доступ ко всем данным, пользователям, словарям, системным настройкам и аудиту.
- `ADMIN` — доступ к управлению справочниками, вакансиями, сводным отчетам и генерации интеграционных токенов.
- `RECRUITER` — доступ ограничен вакансиями, где пользователь указан в качестве основного рекрутера (`recruiter_id`), со-рекрутера (`co_recruiter_id`) или назначен через делегирование прав.

---

## 3. Интеграционный API (38 полей RMS)

Интеграционный API специально спроектирован для экспорта и синхронизации вакансий с внешними кадровыми и аналитическими системами. Данные стандартизированы согласно корпоративному формату из 38 ключевых полей.

### 3.1. Эндпоинт `GET /api/integration/vacancies`

Возвращает плоский список вакансий со всеми 38 атрибутами, включая развернутые текстовые значения из связанных справочников.

#### Параметры запроса (Query Parameters):

| Параметр | Тип | По умолчанию | Описание |
|---|---|---|---|
| `limit` | integer | `1000` | Количество записей в ответе (от 1 до 5000). |
| `offset` | integer | `0` | Смещение для постраничной выгрузки. |
| `status` | string | `null` | Фильтр по названию статуса вакансии (например: `В работе`, `Hold`, `Закрыта`). |
| `updated_after` | datetime | `null` | Инкрементальная выгрузка: фильтрация записей, измененных или созданных после указанной даты/времени (ISO 8601). |
| `format` | string | `json` | Формат выдачи данных: `json`, `csv` или `excel`. |

#### Пример запроса:
```http
GET /api/integration/vacancies?limit=500&offset=0&status=В%20работе&format=json HTTP/1.1
Host: rms.ittori.online
X-API-Key: <INTEGRATION_TOKEN>
```

#### Пример ответа (`format=json`):
```json
{
  "success": true,
  "total": 1245,
  "count": 1,
  "limit": 500,
  "offset": 0,
  "items": [
    {
      "ID вакансии": "7926",
      "Дата открытия": "15.09.2026",
      "Количество": 1,
      "Уровень специалиста": "Senior",
      "Вакансия": "Lead DevOps Инженер",
      "Статус вакансии": "В работе",
      "ИТ роль": "DevOps",
      "Адм. руководитель": "Петров П.П.",
      "Тимлид": "Сидоров С.С.",
      "Проект": "Единая платформа данных",
      "Передано заказчику": 12,
      "Резюме одобрено": 8,
      "Собеседования факт": 5,
      "Собеседования план": 2,
      "Оффер сделан": 1,
      "Оффер принят": 0,
      "Причина отказа от Оффера": null,
      "Город": "Москва",
      "Источник найма": "HeadHunter",
      "Внутренний перевод": "Нет",
      "Дата изм. статуса": "01.10.2026",
      "Дата закрытия": null,
      "ФИО кандидата": null,
      "Компания кандидата": null,
      "Новая / Замена": "Новая",
      "ФИО бывшего сотр.": null,
      "ID ШЕ": "ШЕ-004921",
      "Вид занятости": "Основное место работы",
      "ТЭО проекта": "63129 - Сопровождение ЦХД",
      "Ссылка IQHR": "https://iqhr.company.ru/vacancies/7926",
      "Рекрутер": "Иванов И.И.",
      "Доп. рекрутер": "Смирнова А.В.",
      "Блок": "ИТ и Инновации",
      "Срок работы (дней)": 38,
      "Зарплата кандидатов Gross": 350000,
      "Год": 2026,
      "Дата создания": "15.09.2026 10:20:00",
      "Дата формирования выгрузки": "08.11.2026 19:30:00"
    }
  ]
}
```

### 3.2. Эндпоинт `GET /api/integration/vacancies/{vacancy_id}`

Получение одной конкретной вакансии по её системному ID в формате 38 полей.

#### Параметры пути (Path Parameters):
- `vacancy_id` (integer) — идентификатор вакансии в базе данных.

#### Пример ответа:
```json
{
  "success": true,
  "vacancy": {
    "ID вакансии": "7926",
    "Вакансия": "Lead DevOps Инженер",
    "Статус вакансии": "В работе",
    "...": "..."
  }
}
```

### 3.3. Эндпоинт `GET /api/integration/fields`

Возвращает метаданные и спецификацию всех 38 полей схемы интеграции (название поля, тип данных, описание).

#### Пример ответа:
```json
{
  "total_fields": 38,
  "specification": [
    {
      "field": "ID вакансии",
      "type": "целое число",
      "description": "Уникальный идентификатор вакансии в RMS"
    },
    {
      "field": "Дата открытия",
      "type": "дата д.м.г.",
      "description": "Дата открытия вакансии"
    },
    {
      "field": "Зарплата кандидатов Gross",
      "type": "целое число",
      "description": "Уровень заработной платы (Gross, руб.)"
    }
  ]
}
```

---

## 4. API управления вакансиями (`/api/vacancies`)

Предназначен для полного жизненного цикла вакансий (создание, чтение, редактирование, удаление, история изменений). Требует JWT-аутентификации.

### 4.1. Эндпоинт `GET /api/vacancies`

Получение списка вакансий с поддержкой фильтрации по всем колонкам, сортировки и пагинации.

#### Параметры пагинации и сортировки:
- `skip` (integer, default `0`, min `0`) — количество пропускаемых записей.
- `limit` (integer, default `100`, min `1`, max `500`) — количество записей на странице.
- `sort_field` или `sort_by` (string) — имя поля для сортировки (например: `id`, `open_date`, `position_name`, `status_id`, `work_duration_days`).
- `sort_order` (string, `asc` или `desc`, default `desc`) — направление сортировки.

#### Параметры фильтрации по справочникам (поддерживают множественный выбор):
- `status_id` (массив integer) — фильтр по ID статуса (`?status_id=1&status_id=2`).
- `exclude_status_id` (массив integer) — исключить указанные ID статусов.
- `level_id` (массив integer) — фильтр по ID грейда/уровня.
- `it_role_id` (массив integer) — фильтр по ID ИТ-роли.
- `project_id` (массив integer) — фильтр по ID проекта.
- `admin_manager_id` (массив integer) — фильтр по ID административного руководителя.
- `source_id` (массив integer) — фильтр по ID источника найма.
- `block_id` (массив integer) — фильтр по ID блока компании.
- `employment_type_id` (массив integer) — фильтр по типу занятости.
- `feasibility_id` (массив integer) — фильтр по ID обоснования/ТЭО.
- `replacement_type_id` (массив integer) — фильтр по типу потребности (Новая/Замена).
- `internal_transfer_id` (массив integer) — фильтр по типу внутреннего перевода.
- `recruiter_id` (массив integer) — фильтр по основному рекрутеру.
- `co_recruiter_id` (массив integer) — фильтр по со-рекрутеру.

#### Параметры текстового поиска (подстрочный поиск без учета регистра):
- `search` (string) — глобальный поиск по названию вакансии и ID.
- `search_vacancy_id` (string) — точный или префиксный поиск по ID.
- `search_position_name` (string) — поиск по должности.
- `search_candidate_name` (string) — поиск по ФИО кандидата.
- `search_candidate_company` (string) — поиск по компании кандидата.
- `search_city_text` (string) — поиск по городу.
- `search_salary_gross` (string) — поиск по уровню заработной платы.
- `search_comment` (string) — поиск по комментарию.

#### Параметры фильтрации по датам:
- `search_open_date_from` / `search_open_date_to` (date) — диапазон даты открытия (`YYYY-MM-DD`).
- `search_close_date_from` / `search_close_date_to` (date) — диапазон даты закрытия (`YYYY-MM-DD`).
- `search_status_changed_at_from` / `search_status_changed_at_to` (date) — диапазон даты изменения статуса.

#### Формат ответа:
```json
{
  "items": [
    {
      "id": 5061,
      "vacancy_id": "5061",
      "open_date": "2026-09-15",
      "quantity": 1,
      "level_id": 1,
      "position_name": "Lead DevOps Инженер",
      "status_id": 7,
      "it_role_id": 16,
      "admin_manager_id": 2,
      "team_lead_id": 3,
      "project_id": 4,
      "resume_at_customer": 12,
      "resume_approved": 8,
      "interviews_fact": 5,
      "interviews_plan": 2,
      "offer_made": 1,
      "offer_accepted": 0,
      "offer_rejection_reason": null,
      "city_id": 1,
      "city_text": "Москва",
      "team_lead_text": "Сидоров С.С.",
      "source_id": 2,
      "internal_transfer_id": 1,
      "status_changed_at": "2026-10-01",
      "close_date": null,
      "candidate_name": null,
      "candidate_company": null,
      "replacement_type_id": 1,
      "ex_employee_name": null,
      "unit_id": "ШЕ-004921",
      "employment_type_id": 1,
      "feasibility_id": 5,
      "feasibility_text": "63129 - Сопровождение ЦХД",
      "feasibility_name": "63129 - Сопровождение ЦХД",
      "iqhr_link": "https://iqhr.company.ru/vacancies/5061",
      "recruiter_id": 1,
      "co_recruiter_id": 2,
      "block_id": 1,
      "hold_days": 0,
      "salary_gross": 350000,
      "comment": "В активном поиске",
      "work_duration_days": 38,
      "created_at": "2026-09-15T07:20:00Z",
      "updated_at": "2026-10-01T12:00:00Z"
    }
  ],
  "total": 1236,
  "skip": 0,
  "limit": 100
}
```

### 4.2. Эндпоинт `POST /api/vacancies`

Создание новой вакансии.

- Если параметр `quantity` передан больше 1 (например: `quantity: 3`), система автоматически создает указанное количество независимых вакансий с одинаковыми параметрами и уникальными ID.
- Поле `vacancy_id` генерируется автоматически, если не передано явно.

#### Тело запроса (`application/json`):
```json
{
  "position_name": "Senior Backend Developer (Python)",
  "open_date": "2026-11-08",
  "quantity": 1,
  "level_id": 1,
  "it_role_id": 16,
  "status_id": 1,
  "project_id": 4,
  "admin_manager_id": 2,
  "city_text": "Санкт-Петербург",
  "employment_type_id": 1,
  "recruiter_id": 1,
  "co_recruiter_id": 4,
  "block_id": 1,
  "salary_gross": 300000,
  "comment": "Срочная потребность в связи с расширением команды"
}
```

#### Ответ:
- HTTP 201 Created — возвращает созданный объект вакансии со всеми присвоенными идентификаторами.

### 4.3. Эндпоинт `PATCH /api/vacancies/{vacancy_id}`

Частичное обновление полей вакансии и показателей воронки подбора.

- Передаются только те поля, которые необходимо обновить.
- Любое изменение критических полей (статус, рекрутер, воронка, оклад) автоматически протоколируется в таблице истории изменений.

#### Тело запроса (`application/json`):
```json
{
  "status_id": 2,
  "resume_at_customer": 14,
  "resume_approved": 10,
  "interviews_fact": 6,
  "offer_made": 1,
  "offer_accepted": 1,
  "candidate_name": "Алексеев Алексей Алексеевич",
  "close_date": "2026-11-08"
}
```

#### Ответ:
- HTTP 200 OK — обновленная карточка вакансии.

### 4.4. Эндпоинт `DELETE /api/vacancies/{vacancy_id}`

Удаление карточки вакансии по её числовому идентификатору.
- Доступно пользователям с ролями `ADMIN`, `SUPERADMIN`, а также основному рекрутеру вакансии.

#### Ответ:
- HTTP 204 No Content.

### 4.5. Эндпоинт `POST /api/vacancies/bulk-delete`

Массовое удаление вакансий.

#### Тело запроса:
```json
{
  "vacancy_ids": [5061, 5062, 5063]
}
```

#### Ответ:
```json
{
  "deleted_count": 3
}
```

### 4.6. Эндпоинт `GET /api/vacancies/{vacancy_id}/history`

Получение полной хронологической истории изменений полей карточки вакансии (аудит изменений).

#### Пример ответа:
```json
[
  {
    "id": 1284,
    "vacancy_id": 5061,
    "field": "status_id",
    "field_label": "Статус вакансии",
    "old_value": "В работе",
    "new_value": "Оффер принят",
    "changed_by": "Иванов И.И.",
    "changed_at": "2026-11-08T15:30:00Z"
  }
]
```

---

## 5. Справочники системы (`/api/dictionaries`)

Все категориальные поля в RMS нормализованы и привязаны к централизованным справочникам.

### 5.1. Типы справочников (`DictionaryType`)

| Значение `type` | Наименование справочника | Назначение |
|---|---|---|
| `specialist_level` | Уровень специалиста | Грейд (Junior, Middle, Senior, Lead и т.д.) |
| `vacancy_status` | Статус вакансии | Статусы жизненного цикла (Новая, В работе, Hold, Закрыта и т.д.) |
| `it_role` | ИТ роль | Специализация (Backend, Frontend, QA, DevOps, Аналитик и т.д.) |
| `project` | Проект | Продукты и проекты компании |
| `source` | Источник найма | Каналы привлечения (HeadHunter, Хабр, Рекомендация и т.д.) |
| `employment_type` | Вид занятости | Основное место работы, Совместительство, ДГПХ |
| `replacement_type` | Новая / Замена | Тип кадровой потребности |
| `feasibility` | ТЭО проекта | Технико-экономическое обоснование |
| `block` | Блок компании | Корпоративный блок / Дирекция |
| `admin_manager` | Адм. руководитель | Административные руководители подразделений |
| `team_lead` | Тимлид | Руководители команд разработки |
| `internal_transfer` | Внутренний перевод | Типы внутреннего перевода сотрудников |
| `city` | Город | Локации и города присутствия |
| `offer_rejection_reason` | Причина отказа от оффера | Аналитика причин отказов со стороны кандидатов |

### 5.2. Эндпоинты справочников

1. **Получить справочник по типу:**
   - `GET /api/dictionaries/by-type/{dict_type}`
   - Пример: `GET /api/dictionaries/by-type/vacancy_status`
   - Ответ:
     ```json
     {
       "items": [
         {
           "id": 1,
           "type": "vacancy_status",
           "value": "В работе",
           "description": "Вакансия в активном поиске",
           "sort_order": 1,
           "is_active": true
         }
       ],
       "total": 1
     }
     ```

2. **Создать элемент справочника (только Администраторы):**
   - `POST /api/dictionaries`
   - Тело запроса:
     ```json
     {
       "type": "project",
       "value": "Корпоративный портал 2.0",
       "description": "Разработка нового портала",
       "sort_order": 10
     }
     ```

3. **Обновить элемент справочника:**
   - `PATCH /api/dictionaries/{id}`
   - Тело запроса:
     ```json
     {
       "value": "Корпоративный портал 2.0 (Архив)",
       "is_active": false
     }
     ```

---

## 6. Еженедельная отчетность рекрутеров (`/api/reports`)

Модуль еженедельной фиксации движений кандидатов по воронке подбора за конкретные производственные недели года.

### 6.1. Эндпоинты

1. **Получить список отчетов:**
   - `GET /api/reports/`
   - Параметры:
     - `week_number` (integer) — номер недели (1–53).
     - `year` (integer) — календарный год (например: `2026`).
     - `recruiter_id` (integer, опционально) — фильтр по ID рекрутера.
     - `vacancy_id` (integer, опционально) — фильтр по конкретной вакансии.

2. **Создать отчет по вакансии за неделю:**
   - `POST /api/reports/`
   - Тело запроса:
     ```json
     {
       "vacancy_id": 5061,
       "week_number": 45,
       "year": 2026,
       "resume_at_customer": 4,
       "resume_approved": 3,
       "interviews_fact": 2,
       "interviews_plan": 1,
       "offer_made": 1,
       "offer_accepted": 0,
       "comment": "Кандидат думает над оффером до понедельника"
     }
     ```

3. **Редактировать существующий отчет:**
   - `PUT /api/reports/{report_id}`

4. **Удалить отчет:**
   - `DELETE /api/reports/{report_id}`

---

## 7. Аналитические дашборды (`/api/dashboards`)

Эндпоинты для агрегации статистических метрик, конверсии офферов (Job Offer Conversion) и распределения вакансий.

### 7.1. Эндпоинт `GET /api/dashboards/metrics`

#### Параметры запроса:
- `start_date` (date, обязательный) — начало периода (`YYYY-MM-DD`).
- `end_date` (date, обязательный) — конец периода (`YYYY-MM-DD`).
- `recruiter_id` (integer) — срез по рекрутеру.
- `it_role_id` (integer) — срез по ИТ-роли.
- `project_id` (integer) — срез по проекту.
- `source_id` (integer) — срез по источнику найма.
- `status_id` (integer) — срез по статусу.

#### Возвращаемые метрики:
- `total_vacancies` — общее число вакансий за период.
- `active_vacancies` — число вакансий в работе.
- `closed_vacancies` — число успешно закрытых вакансий.
- `avg_close_time_days` — средний срок закрытия вакансии в рабочих днях.
- `funnel` — агрегированная воронка: резюме передано, одобрено, собеседования, офферы.
- `jo_conversion` — конверсия принятия офферов: `(Оффер принят / Оффер сделан) * 100%`.
- `rejection_reasons` — распределение причин отказа от предложений работы.

---

## 8. Экспорт данных (`/api/export`)

Генерация отчетов в формате Excel (.xlsx) с сохранением текущих фильтров и срезов.

1. **Экспорт вакансий в Excel:**
   - `GET /api/export/vacancies`
   - Принимает те же query-параметры фильтрации, что и `GET /api/vacancies`.
   - Ответ: бинарный поток `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

2. **Экспорт еженедельных отчетов в Excel:**
   - `GET /api/export/reports`
   - Параметры: `year`, `week_number`, `recruiter_id`.
   - Включает полные данные движения по всем рекрутерам, в том числе с нулевыми движениями за отчетную неделю.

---

## 9. Формат ошибок и HTTP-статусы

Все ошибки возвращаются в стандартизированном JSON-формате:

```json
{
  "detail": "Описание ошибки для разработчика"
}
```

В случае ошибки валидации параметров (HTTP 422 Unprocessable Entity) возвращается массив некорректных полей:

```json
{
  "detail": [
    {
      "loc": ["body", "open_date"],
      "msg": "invalid date format, expected YYYY-MM-DD",
      "type": "value_error"
    }
  ]
}
```

### Коды ответов:

| HTTP Код | Значение | Причина возникновения |
|---|---|---|
| `200 OK` | Успешно | Запрос выполнен, тело ответа содержит запрошенные данные. |
| `201 Created` | Создано | Ресурс успешно создан (вакансия, пользователь, отчет). |
| `204 No Content` | Нет содержимого | Успешное удаление ресурса (тело ответа пустое). |
| `400 Bad Request` | Некорректный запрос | Ошибка логики запроса или несовместимые параметры. |
| `401 Unauthorized` | Не авторизован | Отсутствует, просрочен или недействителен токен авторизации. |
| `403 Forbidden` | Запрещено | Недостаточно прав для выполнения операции (ограничение RBAC). |
| `404 Not Found` | Не найдено | Запрашиваемый ресурс (вакансия, справочник) не существует. |
| `422 Unprocessable Entity` | Ошибка валидации | Переданы поля некорректного типа или формата. |
| `429 Too Many Requests` | Превышен лимит | Сработал Rate Limiter. Заголовок `Retry-After` содержит время ожидания в секундах. |
| `500 Internal Error` | Ошибка сервера | Необработанная ошибка на стороне сервера. |

---

## 10. Примеры кода интеграции

### 10.1. Python (инкрементальная выгрузка всех вакансий через Integration Token)

```python
import os
import requests

RMS_BASE_URL = "https://rms.ittori.online"
INTEGRATION_TOKEN = os.getenv("RMS_INTEGRATION_TOKEN", "your_token_here")

def fetch_all_vacancies(updated_after=None):
    headers = {
        "X-API-Key": INTEGRATION_TOKEN,
        "Accept": "application/json"
    }
    
    limit = 500
    offset = 0
    all_vacancies = []

    while True:
        params = {
            "limit": limit,
            "offset": offset,
            "format": "json"
        }
        if updated_after:
            params["updated_after"] = updated_after

        response = requests.get(
            f"{RMS_BASE_URL}/api/integration/vacancies",
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        items = data.get("items", [])
        all_vacancies.extend(items)
        
        total = data.get("total", 0)
        offset += limit
        
        if offset >= total or not items:
            break

    return all_vacancies

if __name__ == "__main__":
    vacancies = fetch_all_vacancies(updated_after="2026-11-01T00:00:00Z")
    print(f"Выгружено {len(vacancies)} вакансий.")
    for v in vacancies[:3]:
        print(f"ID: {v['ID вакансии']} | Должность: {v['Вакансия']} | Статус: {v['Статус вакансии']}")
```

### 10.2. Bash / cURL (Авторизация и получение списка вакансий)

```bash
# 1. Получение JWT-токена
AUTH_RESPONSE=$(curl -s -X POST https://rms.ittori.online/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin1@rms-system.ru", "password": "adminpassword"}')

ACCESS_TOKEN=$(echo $AUTH_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# 2. Запрос списка вакансий с фильтром по статусу и сортировкой
curl -s -X GET "https://rms.ittori.online/api/vacancies?limit=10&sort_field=id&sort_order=desc" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Accept: application/json"
```

### 10.3. cURL (Прямая выгрузка вакансий в Excel файл через сервис-токен)

```bash
curl -X GET "https://rms.ittori.online/api/integration/vacancies?format=excel" \
  -H "X-API-Key: <YOUR_API_TOKEN>" \
  -o "vacancies_export.xlsx"
```
