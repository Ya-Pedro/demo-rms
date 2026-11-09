from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from io import BytesIO
import secrets
import pandas as pd

from database import get_db
from models import User, Vacancy, UserRole, IntegrationToken
from auth import get_current_user

router = APIRouter(prefix="/integration", tags=["Интеграционный API"])

# 38 Integration fields specification from RMS Excel standard
INTEGRATION_FIELDS_SPEC = [
    {"field": "ID вакансии", "type": "целое число", "description": "Уникальный идентификатор вакансии в RMS"},
    {"field": "Дата открытия", "type": "дата д.м.г.", "description": "Дата открытия вакансии"},
    {"field": "Количество", "type": "целое число", "description": "Количество открытых позиций"},
    {"field": "Уровень специалиста", "type": "текст", "description": "Грейд / Уровень специалиста"},
    {"field": "Вакансия", "type": "текст", "description": "Наименование должности / роли"},
    {"field": "Статус вакансии", "type": "текст", "description": "Текущий эффективный статус вакансии"},
    {"field": "ИТ роль", "type": "текст", "description": "ИТ специализация роли"},
    {"field": "Адм. руководитель", "type": "текст", "description": "Административный руководитель"},
    {"field": "Тимлид", "type": "текст", "description": "Тимлид / Техлид подразделения"},
    {"field": "Проект", "type": "текст", "description": "Проект / Продуктовое направление"},
    {"field": "Передано заказчику", "type": "целое число", "description": "Количество резюме, переданных заказчику"},
    {"field": "Резюме одобрено", "type": "целое число", "description": "Количество резюме, одобренных заказчиком"},
    {"field": "Собеседования факт", "type": "целое число", "description": "Фактически проведённые собеседования"},
    {"field": "Собеседования план", "type": "целое число", "description": "Запланированные собеседования"},
    {"field": "Оффер сделан", "type": "целое число", "description": "Количество выставленных офферов"},
    {"field": "Оффер принят", "type": "целое число", "description": "Количество принятых кандидатами офферов"},
    {"field": "Причина отказа от Оффера", "type": "текст", "description": "Причина отказа кандидата от сделанного оффера"},
    {"field": "Город", "type": "текст", "description": "Город / Локация вакансии"},
    {"field": "Источник найма", "type": "текст", "description": "Канал привлечения кандидата"},
    {"field": "Внутренний перевод", "type": "текст", "description": "Тип внутреннего перемещения / перевода"},
    {"field": "ФИО рекомендателя", "type": "текст", "description": "ФИО рекомендателя"},
    {"field": "Дата изм. статуса", "type": "дата д.м.г.", "description": "Дата последнего изменения статуса вакансии"},
    {"field": "Дата закрытия", "type": "дата д.м.г.", "description": "Дата успешного закрытия вакансии"},
    {"field": "ФИО кандидата", "type": "текст", "description": "ФИО принятого или финального кандидата"},
    {"field": "Компания кандидата", "type": "текст", "description": "Текущая / прошлая компания кандидата"},
    {"field": "Новая / Замена", "type": "текст", "description": "Тип потребности: Новая позиция или Замена"},
    {"field": "ФИО бывшего сотр.", "type": "текст", "description": "ФИО замещаемого сотрудника при замене"},
    {"field": "ID ШЕ", "type": "текст", "description": "Идентификатор штатной единицы в кадровой системе"},
    {"field": "Вид занятости", "type": "текст", "description": "Вид занятости: Основное место, Совместительство и т.д."},
    {"field": "ТЭО проекта", "type": "текст", "description": "Технико-экономическое обоснование проекта"},
    {"field": "Ссылка IQHR", "type": "текст", "description": "Прямая ссылка на заявку в IQHR"},
    {"field": "Рекрутер", "type": "текст", "description": "ФИО ответственного рекрутера"},
    {"field": "Доп. рекрутер", "type": "текст", "description": "ФИО дополнительного / замещающего рекрутера"},
    {"field": "Блок", "type": "текст", "description": "Блок / Департамент компании"},
    {"field": "Срок работы (дней)", "type": "целое число", "description": "Количество рабочих дней нахождения вакансии в работе"},
    {"field": "Зарплата кандидатов Gross", "type": "целое число", "description": "Уровень заработной платы (Gross, руб.)"},
    {"field": "Год", "type": "дата", "description": "Календарный год открытия вакансии"},
    {"field": "Дата создания", "type": "дата", "description": "Дата создания карточки вакансии в RMS"},
    {"field": "Дата формирования выгрузки", "type": "дата", "description": "Дата и время генерации ответа API"},
]

# --- Integration Security ---
async def verify_integration_token(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
) -> IntegrationToken:
    """
    Проверяет валидность токена интеграции из заголовка X-API-Key или Authorization: Bearer <token>.
    """
    token_str = None
    if x_api_key and x_api_key.strip():
        token_str = x_api_key.strip()
    elif authorization and authorization.strip():
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token_str = parts[1]
        elif len(parts) == 1:
            token_str = parts[0]

    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Отсутствует токен авторизации. Передайте токен в заголовке X-API-Key или Authorization: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(IntegrationToken).where(IntegrationToken.token == token_str)
    result = await db.execute(stmt)
    token_record = result.scalars().first()

    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен API",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not token_record.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Данный токен API деактивирован администратором системы",
        )

    # Update last_used_at timestamp
    token_record.last_used_at = datetime.now()
    await db.commit()

    return token_record


def _format_date(dt) -> str:
    if not dt:
        return ""
    if isinstance(dt, datetime):
        return dt.strftime("%d.%m.%Y")
    if isinstance(dt, date):
        return dt.strftime("%d.%m.%Y")
    return str(dt)


def _serialize_vacancy_38_fields(v: Vacancy, export_timestamp: str) -> Dict[str, Any]:
    """Преобразует вакансию в точный формат из 38 полей согласно спецификации листа API."""
    reports = v.weekly_reports or []

    resume_at_customer = sum(r.resumes_sent or 0         for r in reports)
    resume_approved    = sum(r.candidates_agreed or 0    for r in reports)
    interviews_fact    = sum(r.interviews_conducted or 0 for r in reports)
    interviews_plan    = sum(r.interviews_planned or 0   for r in reports)
    offer_made         = sum(r.offer_made or 0           for r in reports)
    offer_accepted     = sum(r.offer_accepted or 0       for r in reports)

    work_duration = v.work_duration_days
    if work_duration is None and v.open_date and v.close_date:
        work_duration = (v.close_date - v.open_date).days
    elif work_duration is None and v.open_date:
        work_duration = (datetime.now().date() - v.open_date).days

    year_val = ""
    if v.open_date:
        year_val = v.open_date.year
    elif v.created_at:
        year_val = v.created_at.year

    status_name = v.status.value if v.status else ""
    # effective status logic
    if getattr(v, "is_closed", False) or status_name == "Закрыта":
        status_name = "Закрыта"

    # Offer rejection reason
    rej_reason = v.offer_rejection_reason or ""
    if not rej_reason and reports:
        for rep in sorted(reports, key=lambda r: (r.year or 0, r.week_number or 0), reverse=True):
            if rep.offer_rejection_reason:
                rej_reason = rep.offer_rejection_reason
                break

    return {
        "ID вакансии":                    v.id,
        "Дата открытия":                  _format_date(v.open_date),
        "Количество":                     v.quantity or 0,
        "Уровень специалиста":            v.level.value if v.level else "",
        "Вакансия":                       v.position_name or "",
        "Статус вакансии":                status_name,
        "ИТ роль":                        v.it_role.value if v.it_role else "",
        "Адм. руководитель":              v.admin_manager.value if v.admin_manager else "",
        "Тимлид":                         v.team_lead.value if v.team_lead else (v.team_lead_text or ""),
        "Проект":                         v.project.value if v.project else "",
        "Передано заказчику":             resume_at_customer,
        "Резюме одобрено":                resume_approved,
        "Собеседования факт":             interviews_fact,
        "Собеседования план":             interviews_plan,
        "Оффер сделан":                   offer_made,
        "Оффер принят":                   offer_accepted,
        "Причина отказа от Оффера":       rej_reason,
        "Город":                          v.city.value if v.city else (v.city_text or ""),
        "Источник найма":                 v.source.value if v.source else "",
        "Внутренний перевод":             v.internal_transfer.value if v.internal_transfer else "",
        "ФИО рекомендателя":              v.recommender_name or "",
        "Дата изм. статуса":              _format_date(v.status_changed_at),
        "Дата закрытия":                  _format_date(v.close_date),
        "ФИО кандидата":                  v.candidate_name or "",
        "Компания кандидата":             v.candidate_company or "",
        "Новая / Замена":                 v.replacement_type.value if v.replacement_type else "",
        "ФИО бывшего сотр.":              v.ex_employee_name or "",
        "ID ШЕ":                          v.unit_id or "",
        "Вид занятости":                  v.employment_type.value if v.employment_type else "",
        "ТЭО проекта":                    v.feasibility_text or (v.feasibility.value if v.feasibility else ""),
        "Ссылка IQHR":                    v.iqhr_link or "",
        "Рекрутер":                       v.recruiter.full_name if v.recruiter else "",
        "Доп. рекрутер":                  v.co_recruiter.full_name if v.co_recruiter else "",
        "Блок":                           v.block.value if v.block else "",
        "Срок работы (дней)":             work_duration if work_duration is not None else 0,
        "Зарплата кандидатов Gross":      v.salary_gross or 0,
        "Год":                            year_val,
        "Дата создания":                  _format_date(v.created_at),
        "Дата формирования выгрузки":     export_timestamp,
    }


# =====================================================================
# 1. Integration Endpoints for External Systems (Protected by API Key)
# =====================================================================

@router.get("/vacancies", summary="Выгрузка вакансий для внешних систем (38 полей)")
async def get_integration_vacancies(
    limit: int = Query(1000, ge=1, le=5000, description="Количество вакансий в ответе (1-5000)"),
    offset: int = Query(0, ge=0, description="Смещение (пагинация)"),
    status: Optional[str] = Query(None, description="Фильтр по статусу (например: Открыта, Закрыта, Hold)"),
    updated_after: Optional[datetime] = Query(None, description="Инкрементальная выгрузка: вакансии, обновленные после этой даты/времени"),
    format: str = Query("json", regex="^(json|csv|excel)$", description="Формат ответа: json, csv или excel"),
    db: AsyncSession = Depends(get_db),
    token: IntegrationToken = Depends(verify_integration_token),
):
    """
    Возвращает актуальные данные по вакансиям из RMS со всеми 38 полями.
    Требуется авторизация по токену в заголовке `X-API-Key: <token>` или `Authorization: Bearer <token>`.
    """
    query = (
        select(Vacancy)
        .options(
            selectinload(Vacancy.level),
            selectinload(Vacancy.status),
            selectinload(Vacancy.it_role),
            selectinload(Vacancy.project),
            selectinload(Vacancy.source),
            selectinload(Vacancy.employment_type),
            selectinload(Vacancy.replacement_type),
            selectinload(Vacancy.feasibility),
            selectinload(Vacancy.block),
            selectinload(Vacancy.admin_manager),
            selectinload(Vacancy.team_lead),
            selectinload(Vacancy.internal_transfer),
            selectinload(Vacancy.city),
            selectinload(Vacancy.recruiter),
            selectinload(Vacancy.co_recruiter),
            selectinload(Vacancy.weekly_reports),
        )
    )

    if status and status.strip():
        # filter by effective status or dictionary status
        query = query.filter(Vacancy.status.has(value=status.strip()))

    if updated_after:
        query = query.filter(
            (Vacancy.updated_at >= updated_after) | (Vacancy.created_at >= updated_after)
        )

    # Count total
    count_query = select(func.count(Vacancy.id))
    if status and status.strip():
        count_query = count_query.filter(Vacancy.status.has(value=status.strip()))
    if updated_after:
        count_query = count_query.filter(
            (Vacancy.updated_at >= updated_after) | (Vacancy.created_at >= updated_after)
        )
    total_res = await db.execute(count_query)
    total_count = total_res.scalar() or 0

    query = query.order_by(Vacancy.id.asc()).offset(offset).limit(limit)
    res = await db.execute(query)
    vacancies = res.scalars().all()

    export_timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    items = [_serialize_vacancy_38_fields(v, export_timestamp) for v in vacancies]

    if format == "csv":
        df = pd.DataFrame(items)
        output = BytesIO()
        output.write("\uFEFF".encode("utf-8")) # UTF-8 BOM for Excel
        df.to_csv(output, index=False, sep=";", encoding="utf-8")
        output.seek(0)
        filename = f"rms_vacancies_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return StreamingResponse(
            output,
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    if format == "excel":
        df = pd.DataFrame(items)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Вакансии", index=False)
            ws = writer.sheets["Вакансии"]
            if len(items) > 0:
                ws.add_table(0, 0, len(items), len(df.columns) - 1, {
                    "name": "VacanciesTable",
                    "style": "Table Style Medium 9",
                    "columns": [{"header": col} for col in df.columns],
                })
        output.seek(0)
        filename = f"rms_vacancies_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return {
        "success": True,
        "total": total_count,
        "count": len(items),
        "offset": offset,
        "limit": limit,
        "system": token.name,
        "generated_at": export_timestamp,
        "items": items,
    }


@router.get("/vacancies/{vacancy_id}", summary="Получение одной вакансии по ID (38 полей)")
async def get_integration_vacancy_by_id(
    vacancy_id: int,
    db: AsyncSession = Depends(get_db),
    token: IntegrationToken = Depends(verify_integration_token),
):
    """
    Возвращает детальные данные по одной вакансии по её ID со всеми 38 полями.
    """
    query = (
        select(Vacancy)
        .options(
            selectinload(Vacancy.level),
            selectinload(Vacancy.status),
            selectinload(Vacancy.it_role),
            selectinload(Vacancy.project),
            selectinload(Vacancy.source),
            selectinload(Vacancy.employment_type),
            selectinload(Vacancy.replacement_type),
            selectinload(Vacancy.feasibility),
            selectinload(Vacancy.block),
            selectinload(Vacancy.admin_manager),
            selectinload(Vacancy.team_lead),
            selectinload(Vacancy.internal_transfer),
            selectinload(Vacancy.city),
            selectinload(Vacancy.recruiter),
            selectinload(Vacancy.co_recruiter),
            selectinload(Vacancy.weekly_reports),
        )
        .where(Vacancy.id == vacancy_id)
    )
    res = await db.execute(query)
    vac = res.scalars().first()

    if not vac:
        raise HTTPException(status_code=404, detail=f"Вакансия с ID {vacancy_id} не найдена")

    export_timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    item = _serialize_vacancy_38_fields(vac, export_timestamp)

    return {
        "success": True,
        "system": token.name,
        "generated_at": export_timestamp,
        "item": item,
    }


@router.get("/fields", summary="Спецификация всех 38 полей интеграции")
async def get_integration_fields_spec():
    """
    Возвращает спецификацию всех 38 полей выгрузки (название, тип данных, описание).
    Доступно публично для документации интеграции.
    """
    return {
        "total_fields": len(INTEGRATION_FIELDS_SPEC),
        "fields": INTEGRATION_FIELDS_SPEC,
    }


# =====================================================================
# 2. Token Management Endpoints for System Admins
# =====================================================================

def _require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только администраторы и суперадминистраторы имеют доступ к управлению API-токенами",
        )
    return user


@router.get("/tokens", summary="Список токенов интеграции (только админы)")
async def list_tokens(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    """Возвращает список всех созданных токенов интеграции."""
    stmt = (
        select(IntegrationToken)
        .options(selectinload(IntegrationToken.created_by))
        .order_by(IntegrationToken.created_at.desc())
    )
    res = await db.execute(stmt)
    tokens = res.scalars().all()

    return {
        "items": [
            {
                "id": t.id,
                "name": t.name,
                "token": t.token,
                "token_masked": t.token[:8] + "..." + t.token[-4:] if len(t.token) > 16 else t.token,
                "description": t.description or "",
                "is_active": t.is_active,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
                "created_by": t.created_by.full_name if t.created_by else None,
            }
            for t in tokens
        ]
    }


@router.post("/tokens", summary="Создать токен интеграции для внешней системы (только админы)")
async def create_token(
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    """
    Создаёт новый API-токен для подключения внешней системы.
    Генерирует криптографически стойкий токен `rms_live_<uuid>`.
    """
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip()

    if not name:
        raise HTTPException(status_code=400, detail="Название подключаемой системы обязательно")

    generated_token = f"rms_live_{secrets.token_urlsafe(32)}"

    token_obj = IntegrationToken(
        name=name,
        token=generated_token,
        description=description or None,
        is_active=True,
        created_by_id=admin.id,
    )
    db.add(token_obj)
    await db.commit()
    await db.refresh(token_obj)

    return {
        "success": True,
        "message": "API токен успешно создан",
        "item": {
            "id": token_obj.id,
            "name": token_obj.name,
            "token": generated_token,
            "description": token_obj.description or "",
            "is_active": token_obj.is_active,
            "created_at": token_obj.created_at.isoformat(),
            "created_by": admin.full_name,
        },
    }


@router.patch("/tokens/{token_id}/toggle", summary="Включить / отключить токен интеграции")
async def toggle_token(
    token_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    """Активирует или приостанавливает действие токена."""
    token = await db.get(IntegrationToken, token_id)
    if not token:
        raise HTTPException(status_code=404, detail="Токен не найден")

    token.is_active = not token.is_active
    await db.commit()
    await db.refresh(token)

    return {
        "success": True,
        "id": token.id,
        "is_active": token.is_active,
        "message": "Токен активирован" if token.is_active else "Токен приостановлен",
    }


@router.delete("/tokens/{token_id}", summary="Удалить / отозвать токен интеграции навсегда")
async def delete_token(
    token_id: int,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(_require_admin),
):
    """Безвозвратно удаляет токен интеграции."""
    token = await db.get(IntegrationToken, token_id)
    if not token:
        raise HTTPException(status_code=404, detail="Токен не найден")

    await db.delete(token)
    await db.commit()

    return {
        "success": True,
        "message": f"Токен для системы «{token.name}» успешно удален",
    }
