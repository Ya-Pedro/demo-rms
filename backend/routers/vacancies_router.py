\
\
\
\
   
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any, Tuple
from io import BytesIO
import logging
import json
import re
from uuid import uuid4
import pandas as pd
from fastapi_cache import FastAPICache

from database import get_db
from models import User, Dictionary, DictionaryType, UserRole, Vacancy, WeeklyReport
from schemas import VacancyCreate, VacancyUpdate, VacancyResponse, VacancyListResponse, BulkDeleteRequest, BulkAssignRecruiterRequest
from auth import get_current_user, get_password_hash
from services.vacancy_service import VacancyService, vacancy_to_dict, get_current_week_info, get_current_week_monday
from datetime import datetime, timezone, date

router = APIRouter(prefix="/vacancies", tags=["Вакансии"])
logger = logging.getLogger(__name__)

@router.get("", response_model=VacancyListResponse)
async def get_vacancies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status_id: Optional[List[int]] = Query(None),
    exclude_status_id: Optional[List[int]] = Query(None),
    level_id: Optional[List[int]] = Query(None),
    it_role_id: Optional[List[int]] = Query(None),
    project_id: Optional[List[int]] = Query(None),
    admin_manager_id: Optional[List[int]] = Query(None),
    source_id: Optional[List[int]] = Query(None),
    block_id: Optional[List[int]] = Query(None),
    employment_type_id: Optional[List[int]] = Query(None),
    feasibility_id: Optional[List[int]] = Query(None),
    replacement_type_id: Optional[List[int]] = Query(None),
    internal_transfer_id: Optional[List[int]] = Query(None),
    recruiter_id: Optional[List[int]] = Query(None),
    co_recruiter_id: Optional[List[int]] = Query(None),
    search_recruiter: Optional[str] = Query(None),
    search_co_recruiter: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    search_vacancy_id: Optional[str] = Query(None),
    search_position_name: Optional[str] = Query(None),
    search_candidate_name: Optional[str] = Query(None),
    search_candidate_company: Optional[str] = Query(None),
    search_ex_employee_name: Optional[str] = Query(None),
    search_unit_id: Optional[str] = Query(None),
    search_iqhr_link: Optional[str] = Query(None),
    search_salary_gross: Optional[str] = Query(None),
    search_city_text: Optional[str] = Query(None),
    search_team_lead_text: Optional[str] = Query(None),
    search_feasibility_text: Optional[str] = Query(None),
    search_quantity: Optional[str] = Query(None),
    search_work_duration_days: Optional[str] = Query(None),
    search_resume_at_customer: Optional[str] = Query(None),
    search_resume_approved: Optional[str] = Query(None),
    search_interviews_fact: Optional[str] = Query(None),
    search_interviews_plan: Optional[str] = Query(None),
    search_offer_made: Optional[str] = Query(None),
    search_offer_accepted: Optional[str] = Query(None),
    search_offer_rejection_reason: Optional[str] = Query(None),
    search_comment: Optional[str] = Query(None),
    search_open_date: Optional[str] = Query(None),
    search_close_date: Optional[str] = Query(None),
    search_status_changed_at: Optional[str] = Query(None),
    search_open_date_from: Optional[str] = Query(None),
    search_open_date_to: Optional[str] = Query(None),
    search_close_date_from: Optional[str] = Query(None),
    search_close_date_to: Optional[str] = Query(None),
    search_status_changed_at_from: Optional[str] = Query(None),
    search_status_changed_at_to: Optional[str] = Query(None),
    sort_field: Optional[str] = Query(None),
    sort_by: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("desc"),
    week_number: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    print(f"DEBUG get_vacancies: user={current_user.email}, role={current_user.role}, exclude_status_id={exclude_status_id}", flush=True)
    sort_field = sort_field or sort_by
    filter_params = {k: v for k, v in locals().items()
                     if k not in ("db", "current_user", "skip", "limit",
                                  "sort_field", "sort_by", "sort_order", "week_number",
                                  "year", "start_date", "end_date")}
    service = VacancyService(db)
    vacancies, total, metrics_map = await service.list_vacancies(
        current_user=current_user, skip=skip, limit=limit,
        sort_field=sort_field, sort_order=sort_order,
        week_number=week_number, year=year,
        start_date=start_date, end_date=end_date,
        filter_params=filter_params,
    )
    items = [VacancyResponse(**vacancy_to_dict(v, metrics_map.get(v.id))) for v in vacancies]
    return VacancyListResponse(items=items, total=total)

@router.post("", response_model=VacancyResponse, status_code=status.HTTP_201_CREATED)
async def create_vacancy(
    vacancy_data: VacancyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = VacancyService(db)
    vacancy, metrics = await service.create_vacancy(vacancy_data.model_dump(), current_user)
    await FastAPICache.clear(namespace="dashboards")
    return VacancyResponse(**vacancy_to_dict(vacancy, metrics))

@router.post("/bulk-delete", status_code=status.HTTP_200_OK)
async def bulk_delete_vacancies(
    body: BulkDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Массовое удаление вакансий — только для суперадмина."""
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только для суперадмина")
    
    if body.delete_all:
        from sqlalchemy import select
        from models import Vacancy
        result = await db.execute(select(Vacancy.id))
        body.ids = result.scalars().all()
        
    if not body.ids:
        raise HTTPException(status_code=400, detail="Список ID пуст")

    service = VacancyService(db)
    deleted = 0
    errors = []
    for vid in body.ids:
        try:
            await service.delete_vacancy(vid, current_user)
            deleted += 1
        except HTTPException as e:
            errors.append(f"ID {vid}: {e.detail}")
        except Exception as e:
            errors.append(f"ID {vid}: {str(e)}")

    await FastAPICache.clear(namespace="dashboards")
    return {"deleted": deleted, "errors": errors}

@router.post("/bulk-assign-recruiter", status_code=status.HTTP_200_OK)
async def bulk_assign_recruiter(
    body: BulkAssignRecruiterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Массовое назначение рекрутера на выбранные вакансии."""
    if current_user.role not in (UserRole.SUPERADMIN, UserRole.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только для администраторов")
    
    if not body.ids:
        raise HTTPException(status_code=400, detail="Список ID пуст")

    result = await db.execute(select(User).where(User.id == body.recruiter_id, User.is_active == True))
    target_recruiter = result.scalar_one_or_none()
    if not target_recruiter:
        raise HTTPException(status_code=404, detail="Указанный рекрутер не найден или неактивен")

    service = VacancyService(db)
    assigned = 0
    errors = []
    for vid in body.ids:
        try:
            await service.update_vacancy(vid, {"recruiter_id": body.recruiter_id}, current_user)
            assigned += 1
        except Exception as e:
            errors.append(f"ID {vid}: {str(e)}")

    await FastAPICache.clear(namespace="dashboards")
    return {"assigned": assigned, "assigned_count": assigned, "errors": errors}

@router.get("/{vacancy_id}", response_model=VacancyResponse)
async def get_vacancy(
    vacancy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = VacancyService(db)
    vacancy = await service.get_vacancy_or_404(vacancy_id)
    await service.check_recruiter_access(vacancy, current_user)
    return VacancyResponse(**vacancy_to_dict(vacancy))

@router.patch("/{vacancy_id}", response_model=VacancyResponse)
async def update_vacancy(
    vacancy_id: int,
    vacancy_data: VacancyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = VacancyService(db)
    vacancy, metrics = await service.update_vacancy(
        vacancy_id, vacancy_data.model_dump(exclude_unset=True), current_user
    )
    await FastAPICache.clear(namespace="dashboards")
    return VacancyResponse(**vacancy_to_dict(vacancy, metrics))

@router.delete("/{vacancy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vacancy(
    vacancy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = VacancyService(db)
    await service.delete_vacancy(vacancy_id, current_user)
    await FastAPICache.clear(namespace="dashboards")

EMPTY_DATE_STRINGS = {
    "-", "—", "–", "нет", "н/д", "н\\д", "n/a", "none", "null",
    ".", "/", "\\", "не указано", "отсутствует", "0", "00.00.0000"
}

def _norm_str(s) -> str:
    if s is None or pd.isna(s):
        return ""
    cleaned = (
        str(s)
        .replace("\xa0", " ")
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("\\", " ")
        .replace("/", " ")
    )
    return " ".join(cleaned.strip().lower().split()).rstrip(":.")

def _clean_dict_val(v) -> str:
    s = _norm_str(v).replace(" +", "+").replace("+ ", "+")
    if s == "внутренее совместительство":
        s = "внутреннее совместительство"
    return s

COLUMN_DEFINITIONS = [
    {
        "field": "vacancy_id",
        "display": "ID вакансии",
        "aliases": ["id вакансии", "ид вакансии", "id", "ид", "номер вакансии", "№ вакансии", "vacancy id", "vacancy_id"],
        "type": "string",
    },
    {
        "field": "position_name",
        "display": "Вакансия",
        "aliases": ["вакансия", "позиция", "наименование вакансии", "название вакансии", "должность", "position_name"],
        "type": "string",
    },
    {
        "field": "quantity",
        "display": "Количество",
        "aliases": ["количество", "кол-во", "кол-во вакансий", "кол во вакансий", "количество вакансий", "quantity"],
        "type": "int",
        "min": 1,
    },
    {
        "field": "salary_gross",
        "display": "Зарплата кандидатов Gross",
        "aliases": ["зарплата кандидатов gross", "зарплата gross", "зарплата", "gross", "оклад", "зарплата кандидатов", "salary_gross"],
        "type": "int",
        "min": 0,
    },
    {
        "field": "candidate_name",
        "display": "ФИО кандидата",
        "aliases": ["фио кандидата", "кандидат", "фио", "candidate_name"],
        "type": "string",
    },
    {
        "field": "candidate_company",
        "display": "Компания кандидата",
        "aliases": ["компания из которой пришел кандидат", "компания кандидата", "текущая компания кандидата", "компания", "candidate_company"],
        "type": "string",
    },
    {
        "field": "ex_employee_name",
        "display": "ФИО бывшего сотр.",
        "aliases": ["фио бывшего сотрудника", "фио бывшего сотр.", "фио бывшего сотр", "бывший сотрудник", "ex_employee_name"],
        "type": "string",
    },
    {
        "field": "unit_id",
        "display": "ID ШЕ",
        "aliases": ["id ше", "ид ше", "ше", "id штатной единицы", "unit_id"],
        "type": "string",
    },
    {
        "field": "iqhr_link",
        "display": "Ссылка IQHR",
        "aliases": [
            "ссылка на вакансию iqhr (если вакансия не заведена- указывай грейд в строчке)",
            "ссылка на вакансию iqhr",
            "ссылка iqhr",
            "ссылка на заявку iqhr",
            "ссылка на iqhr",
            "iqhr",
            "iqhr_link",
        ],
        "type": "string",
    },
    {
        "field": "comment",
        "display": "Комментарий",
        "aliases": ["комментарий", "комментарии", "comment"],
        "type": "string",
    },
    {
        "field": "offer_rejection_reason",
        "display": "Причина отказа от Оффера",
        "aliases": ["причина отказа от оффера", "причина отказа от оффер", "причина отказа", "offer_rejection_reason"],
        "type": "string",
    },
    # Воронка
    {
        "field": "resume_at_customer",
        "display": "Передано заказчику",
        "aliases": ["резюме у заказчика", "передано заказчику", "направлено резюме", "резюме направлено", "resumes_sent", "resume_at_customer"],
        "type": "funnel",
    },
    {
        "field": "resume_approved",
        "display": "Резюме одобрено",
        "aliases": ["резюме одобрено", "согласовано кандидатов", "одобрено резюме", "candidates_agreed", "resume_approved"],
        "type": "funnel",
    },
    {
        "field": "interviews_fact",
        "display": "Собеседования факт",
        "aliases": [
            "собеседования факт на эту неделю",
            "собеседования факт",
            "проведено интервью",
            "интервью факт",
            "interviews_conducted",
            "interviews_fact",
        ],
        "type": "funnel",
    },
    {
        "field": "interviews_plan",
        "display": "Собеседования план",
        "aliases": [
            "запланировано собеседований на след неделю",
            "собеседования план",
            "запланировано интервью",
            "интервью план",
            "interviews_planned",
            "interviews_plan",
        ],
        "type": "funnel",
    },
    {
        "field": "offer_made",
        "display": "Оффер сделан",
        "aliases": ["сделан оффер", "оффер сделан", "сделано офферов", "offer_made"],
        "type": "funnel",
    },
    {
        "field": "offer_accepted",
        "display": "Оффер принят",
        "aliases": ["оффер принят", "принято офферов", "принят оффер", "offer_accepted"],
        "type": "funnel",
    },
    # Даты
    {
        "field": "open_date",
        "display": "Дата открытия",
        "aliases": ["дата открытия вакансии", "дата открытия", "open_date"],
        "type": "date",
    },
    {
        "field": "close_date",
        "display": "Дата закрытия",
        "aliases": ["дата выхода", "дата выхода кандидата", "дата закрытия", "дата закрытия вакансии", "close_date"],
        "type": "date",
    },
    {
        "field": "status_changed_at",
        "display": "Дата изм. статуса",
        "aliases": ["дата изменения статуса", "дата изм. статуса", "дата изм статуса", "дата смены статуса", "status_changed_at"],
        "type": "date",
    },
    # Справочники
    {
        "field": "level_id",
        "display": "Уровень специалиста",
        "aliases": ["уровень специалиста", "уровень", "грейд", "specialist_level", "level_id"],
        "type": "dict",
        "dict_type": "specialist_level",
        "dict_title": "Уровень специалиста",
    },
    {
        "field": "status_id",
        "display": "Статус вакансии",
        "aliases": ["статус вакансии", "статус", "vacancy_status", "status_id"],
        "type": "dict",
        "dict_type": "vacancy_status",
        "dict_title": "Статус вакансии",
    },
    {
        "field": "it_role_id",
        "display": "ИТ роль",
        "aliases": ["стек", "стек технологий", "ит роль", "it роль", "ит-роль", "it-роль", "роль", "it_role", "it_role_id"],
        "type": "dict",
        "dict_type": "it_role",
        "dict_title": "ИТ роль",
    },
    {
        "field": "project_id",
        "display": "Проект",
        "aliases": ["проект направление", "проект", "project", "project_id"],
        "type": "dict",
        "dict_type": "project",
        "dict_title": "Проект",
    },
    {
        "field": "source_id",
        "display": "Источник найма",
        "aliases": ["источник найма", "источник", "source", "source_id"],
        "type": "dict",
        "dict_type": "source",
        "dict_title": "Источник найма",
    },
    {
        "field": "internal_transfer_id",
        "display": "Внутренний перевод",
        "aliases": ["боруп внутренний перевод", "боруп", "внутренний перевод", "перевод", "internal_transfer", "internal_transfer_id"],
        "type": "dict",
        "dict_type": "internal_transfer",
        "dict_title": "Внутренний перевод",
    },
    {
        "field": "replacement_type_id",
        "display": "Новая / Замена",
        "aliases": ["новая замена", "новая / замена", "новая/замена", "новая или замена", "тип вакансии", "replacement_type", "replacement_type_id"],
        "type": "dict",
        "dict_type": "replacement_type",
        "dict_title": "Новая / Замена",
    },
    {
        "field": "employment_type_id",
        "display": "Вид занятости",
        "aliases": ["вид занятости", "тип занятости", "занятость", "employment_type", "employment_type_id"],
        "type": "dict",
        "dict_type": "employment_type",
        "dict_title": "Вид занятости",
    },
    {
        "field": "block_id",
        "display": "Блок",
        "aliases": ["блок", "подразделение", "block", "block_id"],
        "type": "dict",
        "dict_type": "block",
        "dict_title": "Блок",
    },
    {
        "field": "admin_manager_id",
        "display": "Адм. руководитель",
        "aliases": [
            "администратирвный руководитель",
            "административный руководитель",
            "адм. руководитель",
            "адм руководитель",
            "руководитель",
            "admin_manager",
            "admin_manager_id",
        ],
        "type": "dict",
        "dict_type": "admin_manager",
        "dict_title": "Адм. руководитель",
    },
    # Справочники с текстовым фоллбэком
    {
        "field": "city_id",
        "text_field": "city_text",
        "display": "Город",
        "aliases": ["город выхода кандидата", "город выхода", "город", "локация", "city", "city_id"],
        "type": "dict_with_text",
        "dict_type": "city",
        "dict_title": "Город",
    },
    {
        "field": "feasibility_id",
        "text_field": "feasibility_text",
        "display": "ТЭО проекта",
        "aliases": ["тэо проекта", "тэо", "feasibility", "feasibility_id"],
        "type": "dict_with_text",
        "dict_type": "feasibility",
        "dict_title": "ТЭО проекта",
    },
    {
        "field": "team_lead_id",
        "text_field": "team_lead_text",
        "display": "Тимлид",
        "aliases": ["тимлид (кто технически оценивает кандидата)", "тимлид", "тим-лид", "лид", "team_lead", "team_lead_id"],
        "type": "dict_with_text",
        "dict_type": "team_lead",
        "dict_title": "Тимлид",
    },
    # Пользователи
    {
        "field": "recruiter_id",
        "display": "Рекрутер",
        "aliases": ["рекрутер", "ответственный рекрутер", "основной рекрутер", "recruiter", "recruiter_id"],
        "type": "user",
    },
    {
        "field": "co_recruiter_id",
        "display": "Доп. рекрутер",
        "aliases": ["доп. рекрутер", "доп рекрутер", "дополнительный рекрутер", "второй рекрутер", "co_recruiter", "co_recruiter_id"],
        "type": "user",
    },
]

IGNORED_COLUMNS = {
    "срок работы (дней)", "срок работы", "дни в работе",
    "срок работы над вакансией, дни", "срок работы над вакансией дни",
    "месяц", "год", "№", "№ п/п",
}

FUNNEL_MAP_WR = {
    "resume_at_customer": "resumes_sent",
    "resume_approved":    "candidates_agreed",
    "interviews_fact":    "interviews_conducted",
    "interviews_plan":    "interviews_planned",
    "offer_made":         "offer_made",
    "offer_accepted":     "offer_accepted",
}

def _parse_cell_int(val, col_title: str, excel_row: int, min_val: Optional[int] = 0) -> Tuple[Optional[int], Optional[str]]:
    if pd.isna(val) or val is None or str(val).strip() == "":
        return None, None
    s = str(val).replace("\xa0", " ").replace(" ", "").replace(",", ".")
    try:
        num = float(s)
        if not num.is_integer():
            return None, f"Строка {excel_row}, колонка «{col_title}»: значение «{val}» должно быть целым числом"
        int_v = int(num)
        if min_val is not None and int_v < min_val:
            return None, f"Строка {excel_row}, колонка «{col_title}»: значение «{val}» не может быть меньше {min_val}"
        return int_v, None
    except (ValueError, TypeError):
        return None, f"Строка {excel_row}, колонка «{col_title}»: значение «{val}» не является числом"

def _parse_cell_date(val, col_title: str, excel_row: int) -> Tuple[Optional[date], Optional[str]]:
    if pd.isna(val) or val is None or str(val).strip() == "":
        return None, None
    if isinstance(val, (datetime, pd.Timestamp)):
        return val.date(), None
    if isinstance(val, date):
        return val, None
    if isinstance(val, (int, float)):
        try:
            return pd.to_datetime(val, unit="D", origin="1899-12-30").date(), None
        except Exception:
            pass
    s = str(val).strip()
    if s.lower() in EMPTY_DATE_STRINGS:
        return None, None
    try:
        if re.match(r"^\d{4}[-./]\d{1,2}[-./]\d{1,2}", s):
            parsed = pd.to_datetime(s, dayfirst=False)
            return parsed.date(), None
        elif re.match(r"^\d{1,2}[-./]\d{1,2}[-./]\d{4}", s):
            parsed = pd.to_datetime(s, dayfirst=True)
            return parsed.date(), None
        else:
            parsed = pd.to_datetime(s)
            return parsed.date(), None
    except Exception:
        return None, f"Строка {excel_row}, колонка «{col_title}»: неверный формат даты «{s}» (ожидается ДД.ММ.ГГГГ)"

def _match_columns(df) -> Tuple[Dict[str, Tuple[str, dict]], Optional[str]]:
    matched_columns = {}
    matched_fields = set()
    for col in df.columns:
        norm_c = _norm_str(col)
        if not norm_c or norm_c in IGNORED_COLUMNS:
            continue
        for defn in COLUMN_DEFINITIONS:
            if defn["field"] in matched_fields:
                continue
            if norm_c == defn["display"].lower() or norm_c in defn["aliases"]:
                matched_columns[defn["field"]] = (str(col), defn)
                matched_fields.add(defn["field"])
                break
    if "vacancy_id" not in matched_columns:
        found_headers = [str(c).strip() for c in df.columns if str(c).strip() and not str(c).startswith("Unnamed")]
        cols_preview = ", ".join(f"«{c}»" for c in found_headers[:10])
        if len(found_headers) > 10:
            cols_preview += f" (всего колонок: {len(found_headers)})"
        elif not found_headers:
            cols_preview = "заголовки колонок не распознаны"
        return {}, f"Не найден обязательный столбец «ID вакансии» (или «ID»). Обнаружены столбцы: {cols_preview}."
    return matched_columns, None

@router.post("/import/preview")
async def preview_vacancies_import(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только для суперадмина")
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Поддерживаются только .xlsx/.xls файлы")

    contents = await file.read()
    try:
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка чтения файла Excel: {str(e)}")

    if df.empty or len(df.columns) == 0:
        raise HTTPException(
            status_code=400,
            detail={"message": "Файл пуст", "errors": ["В файле нет колонок или данных."]},
        )

    matched_columns, err_msg = _match_columns(df)
    if err_msg:
        raise HTTPException(status_code=400, detail={"message": err_msg, "errors": [err_msg]})

    dict_result = await db.execute(select(Dictionary))
    dict_lookup = {}
    for d in dict_result.scalars().all():
        if d.value:
            key = (d.type.value if hasattr(d.type, 'value') else str(d.type), _clean_dict_val(d.value))
            dict_lookup[key] = d.id

    from models import User as UserModel
    user_result = await db.execute(select(UserModel))
    users = user_result.scalars().all()
    user_lookup_by_name = {}
    user_lookup_by_email = {}
    for u in users:
        if u.full_name:
            user_lookup_by_name[_norm_str(u.full_name)] = u.id
        if u.email:
            user_lookup_by_email[_norm_str(u.email)] = u.id

    existing_vids = set((await db.execute(select(Vacancy.vacancy_id))).scalars().all())

    vid_col_name = matched_columns["vacancy_id"][0]
    pos_col_name = matched_columns.get("position_name", (None, None))[0]

    missing_dict_map = {}
    missing_recruiter_map = {}
    missing_positions = []
    dash_dates_count = 0
    other_errors = []
    existing_count = 0
    new_count = 0

    for idx, row in df.iterrows():
        excel_row = idx + 2
        raw_vid = row.get(vid_col_name)
        if pd.isna(raw_vid) or str(raw_vid).strip() == "":
            other_errors.append(f"Строка {excel_row}: не указан ID вакансии")
            continue

        vid_str = str(raw_vid).strip()[:50]
        if vid_str in existing_vids:
            existing_count += 1
        else:
            new_count += 1
            raw_pos = row.get(pos_col_name) if pos_col_name else None
            if pd.isna(raw_pos) or not str(raw_pos).strip():
                missing_positions.append({
                    "row": excel_row,
                    "vacancy_id": vid_str,
                    "suggested_name": f"Вакансия {vid_str}",
                })

        for field, (col_name, defn) in matched_columns.items():
            if field == "vacancy_id":
                continue
            raw_val = row.get(col_name)
            if pd.isna(raw_val) or str(raw_val).strip() == "":
                continue

            col_type = defn["type"]
            raw_str = str(raw_val).strip()

            if col_type == "int":
                _, err = _parse_cell_int(raw_val, col_name, excel_row, min_val=defn.get("min", 0))
                if err:
                    other_errors.append(err)
            elif col_type == "funnel":
                _, err = _parse_cell_int(raw_val, col_name, excel_row, min_val=0)
                if err:
                    other_errors.append(err)
            elif col_type == "date":
                if raw_str.lower() in EMPTY_DATE_STRINGS:
                    dash_dates_count += 1
                else:
                    _, err = _parse_cell_date(raw_val, col_name, excel_row)
                    if err:
                        other_errors.append(err)
            elif col_type == "dict":
                norm_v = _clean_dict_val(raw_val)
                dtype = defn["dict_type"]
                dtitle = defn.get("dict_title", col_name)
                if (dtype, norm_v) not in dict_lookup:
                    k = (dtype, dtitle, raw_str)
                    if k not in missing_dict_map:
                        missing_dict_map[k] = {"count": 0, "sample_rows": []}
                    missing_dict_map[k]["count"] += 1
                    if len(missing_dict_map[k]["sample_rows"]) < 5:
                        missing_dict_map[k]["sample_rows"].append(excel_row)
            elif col_type == "user":
                norm_v = _norm_str(raw_val)
                uid = user_lookup_by_name.get(norm_v) or user_lookup_by_email.get(norm_v)
                if not uid:
                    if raw_str not in missing_recruiter_map:
                        missing_recruiter_map[raw_str] = {"count": 0, "roles": set(), "sample_rows": []}
                    missing_recruiter_map[raw_str]["count"] += 1
                    missing_recruiter_map[raw_str]["roles"].add(defn.get("display", "Рекрутер"))
                    if len(missing_recruiter_map[raw_str]["sample_rows"]) < 5:
                        missing_recruiter_map[raw_str]["sample_rows"].append(excel_row)

    missing_dictionaries = [
        {
            "dict_type": dtype,
            "dict_title": dtitle,
            "value": val,
            "count": info["count"],
            "sample_rows": info["sample_rows"],
        }
        for (dtype, dtitle, val), info in sorted(missing_dict_map.items(), key=lambda x: (x[0][1], x[0][2]))
    ]

    missing_recruiters = [
        {
            "name": val,
            "count": info["count"],
            "roles": sorted(list(info["roles"])),
            "sample_rows": info["sample_rows"],
        }
        for val, info in sorted(missing_recruiter_map.items(), key=lambda x: x[0])
    ]

    has_conflicts = bool(missing_dictionaries or missing_recruiters or missing_positions or other_errors)

    return {
        "total_rows": len(df),
        "existing_count": existing_count,
        "new_count": new_count,
        "has_conflicts": has_conflicts,
        "missing_dictionaries": missing_dictionaries,
        "missing_recruiters": missing_recruiters,
        "missing_positions": missing_positions,
        "dash_dates_count": dash_dates_count,
        "other_errors": other_errors[:50],
    }

@router.post("/import")
async def import_vacancies(
    file: UploadFile = File(...),
    add_dictionaries_json: Optional[str] = Form(None),
    recruiters_action: Optional[str] = Form("leave_empty"),
    create_recruiters_json: Optional[str] = Form(None),
    auto_fill_missing_positions: Optional[bool] = Form(True),
    treat_dash_as_empty_date: Optional[bool] = Form(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только для суперадмина")
    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Поддерживаются только .xlsx/.xls файлы")

    contents = await file.read()
    try:
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка чтения файла Excel: {str(e)}")

    if df.empty or len(df.columns) == 0:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Файл пуст",
                "errors": ["В загруженном файле нет колонок или данных для импорта."],
            },
        )

    matched_columns, err_msg = _match_columns(df)
    if err_msg:
        raise HTTPException(status_code=400, detail={"message": err_msg, "errors": [err_msg]})

    dict_result = await db.execute(select(Dictionary))
    dict_lookup = {}
    for d in dict_result.scalars().all():
        if d.value:
            key = (d.type.value if hasattr(d.type, 'value') else str(d.type), _clean_dict_val(d.value))
            dict_lookup[key] = d.id

    # 1. Если переданы новые справочники для добавления
    if add_dictionaries_json:
        try:
            to_add = json.loads(add_dictionaries_json)
            added_any = False
            for item in to_add:
                dtype_str = item.get("type") or item.get("dict_type")
                dval = (item.get("value") or "").strip()
                if not dtype_str or not dval:
                    continue
                clean_val = _clean_dict_val(dval)
                if (dtype_str, clean_val) not in dict_lookup:
                    try:
                        dtype_enum = DictionaryType(dtype_str)
                    except ValueError:
                        continue
                    new_dict = Dictionary(
                        type=dtype_enum,
                        value=dval,
                        sort_order=0,
                        is_active=True,
                    )
                    db.add(new_dict)
                    await db.flush()
                    dict_lookup[(dtype_str, clean_val)] = new_dict.id
                    added_any = True
            if added_any:
                logger.info(f"Auto-created {len(to_add)} dictionaries for import")
        except Exception as e:
            logger.error(f"Error auto-creating dictionaries: {e}")

    # 2. Пользователи
    from models import User as UserModel
    user_result = await db.execute(select(UserModel))
    users = user_result.scalars().all()
    user_lookup_by_name = {}
    user_lookup_by_email = {}
    for u in users:
        if u.full_name:
            user_lookup_by_name[_norm_str(u.full_name)] = u.id
        if u.email:
            user_lookup_by_email[_norm_str(u.email)] = u.id

    # 2.1 Создание рекрутеров с указанными пользователем email
    if create_recruiters_json and recruiters_action == "create_users":
        try:
            r_list = json.loads(create_recruiters_json)
            for item in r_list:
                r_name = (item.get("name") or "").strip()
                r_email = (item.get("email") or "").strip().lower()
                if not r_name:
                    continue
                norm_r_name = _norm_str(r_name)
                if norm_r_name in user_lookup_by_name:
                    continue
                if not r_email:
                    r_email = f"recruiter_{uuid4().hex[:6]}@rms.local"
                existing_u = (await db.execute(select(UserModel).where(UserModel.email == r_email))).scalar_one_or_none()
                if existing_u:
                    user_lookup_by_name[norm_r_name] = existing_u.id
                    user_lookup_by_email[_norm_str(r_email)] = existing_u.id
                else:
                    new_u = UserModel(
                        email=r_email,
                        full_name=r_name,
                        hashed_password=get_password_hash("RMS_recruiter_2026!"),
                        role=UserRole.RECRUITER,
                        is_active=True,
                        is_temporary_password=True,
                    )
                    db.add(new_u)
                    await db.flush()
                    user_lookup_by_name[norm_r_name] = new_u.id
                    user_lookup_by_email[_norm_str(r_email)] = new_u.id
                    logger.info(f"Created new recruiter user: {r_name} <{r_email}>")
        except Exception as e:
            logger.error(f"Error creating recruiters from JSON: {e}")

    created = updated = 0
    errors = []
    week_num, yr = get_current_week_info()
    week_start = get_current_week_monday()

    vid_col_name = matched_columns["vacancy_id"][0]

    for idx, row in df.iterrows():
        excel_row = idx + 2
        row_errors = []
        data, funnel = {}, {}

        # 1. Проверяем vacancy_id
        raw_vid = row.get(vid_col_name)
        if pd.isna(raw_vid) or str(raw_vid).strip() == "":
            row_errors.append(f"Строка {excel_row}, колонка «{vid_col_name}»: не указан идентификатор вакансии (обязательное поле)")
        else:
            data["vacancy_id"] = str(raw_vid).strip()[:50]

        # 2. Проверяем все остальные поля
        for field, (col_name, defn) in matched_columns.items():
            if field == "vacancy_id":
                continue
            raw_val = row.get(col_name)
            if pd.isna(raw_val) or str(raw_val).strip() == "":
                continue

            col_type = defn["type"]
            if col_type == "int":
                iv, err = _parse_cell_int(raw_val, col_name, excel_row, min_val=defn.get("min", 0))
                if err:
                    row_errors.append(err)
                elif iv is not None:
                    data[field] = iv

            elif col_type == "funnel":
                iv, err = _parse_cell_int(raw_val, col_name, excel_row, min_val=0)
                if err:
                    row_errors.append(err)
                elif iv is not None:
                    funnel[field] = iv
                    if field == "resume_at_customer":
                        data["resume_at_customer"] = iv
                    elif field == "resume_approved":
                        data["resume_approved"] = iv
                    elif field == "interviews_fact":
                        data["interviews_fact"] = iv
                    elif field == "interviews_plan":
                        data["interviews_plan"] = iv
                    elif field == "offer_made":
                        data["offer_made"] = iv
                    elif field == "offer_accepted":
                        data["offer_accepted_cnt"] = iv

            elif col_type == "date":
                dv, err = _parse_cell_date(raw_val, col_name, excel_row)
                if err:
                    row_errors.append(err)
                elif dv is not None:
                    data[field] = dv

            elif col_type == "dict":
                norm_v = _clean_dict_val(raw_val)
                raw_str = str(raw_val).strip()
                did = dict_lookup.get((defn["dict_type"], norm_v))
                if not did:
                    row_errors.append(
                        f"Строка {excel_row}, колонка «{col_name}»: значение «{raw_str}» не найдено в справочнике «{defn.get('dict_title', col_name)}»"
                    )
                else:
                    data[field] = did

            elif col_type == "dict_with_text":
                norm_v = _clean_dict_val(raw_val)
                raw_str = str(raw_val).strip()
                did = dict_lookup.get((defn["dict_type"], norm_v))
                data[defn["text_field"]] = raw_str[:255]
                if did:
                    data[field] = did

            elif col_type == "user":
                norm_v = _norm_str(raw_val)
                raw_str = str(raw_val).strip()
                uid = user_lookup_by_name.get(norm_v) or user_lookup_by_email.get(norm_v)
                if not uid:
                    if recruiters_action == "create_users":
                        try:
                            clean_uname = raw_str[:255]
                            email_slug = f"recruiter_{uuid4().hex[:6]}@rms.local"
                            new_u = User(
                                email=email_slug,
                                full_name=clean_uname,
                                hashed_password=get_password_hash("RMS_recruiter_2026!"),
                                role=UserRole.RECRUITER,
                                is_active=True,
                                is_temporary_password=True,
                            )
                            db.add(new_u)
                            await db.flush()
                            uid = new_u.id
                            user_lookup_by_name[norm_v] = uid
                            data[field] = uid
                        except Exception as e:
                            logger.error(f"Failed to auto-create user: {e}")
                            data[field] = None
                    elif recruiters_action == "leave_empty":
                        data[field] = None
                    else:
                        row_errors.append(
                            f"Строка {excel_row}, колонка «{col_name}»: пользователь «{raw_str}» не найден в системе"
                        )
                else:
                    data[field] = uid

            elif col_type == "string":
                raw_str = str(raw_val).strip()
                if field in ("candidate_name", "candidate_company", "ex_employee_name", "comment"):
                    data[field] = raw_str
                elif field in ("position_name", "offer_rejection_reason"):
                    data[field] = raw_str[:255]
                elif field == "unit_id":
                    data[field] = raw_str[:50]
                elif field == "iqhr_link":
                    data[field] = raw_str[:500]
                else:
                    data[field] = raw_str

        if row_errors:
            errors.extend(row_errors)
            continue

        try:
            async with db.begin_nested():
                existing = (await db.execute(select(Vacancy).where(Vacancy.vacancy_id == data["vacancy_id"]))).scalar_one_or_none()
                if existing:
                    for k, v in data.items():
                        if k != "vacancy_id":
                            setattr(existing, k, v)
                    vacancy_obj = existing
                    await db.flush()
                    updated += 1
                else:
                    if not data.get("position_name"):
                        if auto_fill_missing_positions:
                            data["position_name"] = f"Вакансия {data.get('vacancy_id', excel_row)}"
                        else:
                            pos_col = matched_columns.get("position_name", (None, None))[0] or "Вакансия"
                            errors.append(f"Строка {excel_row}, колонка «{pos_col}»: наименование вакансии обязательно для создания новой вакансии")
                            continue
                    vacancy_obj = Vacancy(**data)
                    db.add(vacancy_obj)
                    await db.flush()
                    created += 1

                if vacancy_obj.id:
                    wr_data = {FUNNEL_MAP_WR[k]: v for k, v in (funnel or {}).items() if k in FUNNEL_MAP_WR}
                    if "comment" in data:
                        wr_data["comment"] = data["comment"]
                    if "offer_rejection_reason" in data:
                        wr_data["offer_rejection_reason"] = data["offer_rejection_reason"]

                    wr = (await db.execute(select(WeeklyReport).where(
                        WeeklyReport.vacancy_id == vacancy_obj.id,
                        WeeklyReport.week_number == week_num,
                        WeeklyReport.year == yr,
                    ))).scalar_one_or_none()
                    if wr:
                        for k, v in wr_data.items():
                            setattr(wr, k, v)
                    else:
                        db.add(WeeklyReport(
                            vacancy_id=vacancy_obj.id,
                            week_number=week_num,
                            year=yr,
                            week_start=week_start,
                            report_date=datetime.now(timezone.utc),
                            **wr_data,
                        ))
                    await db.flush()
        except Exception as e:
            errors.append(f"Строка {excel_row}: ошибка сохранения записи — {str(e)}")

    if created == 0 and updated == 0 and errors:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Ошибки в строках файла импорта",
                "errors": errors[:50],
            },
        )

    await db.commit()
    try:
        await FastAPICache.clear(namespace="dashboards")
    except Exception:
        pass
    return {"created": created, "updated": updated, "errors": errors[:50], "total_rows": len(df)}

@router.get("/{vacancy_id}/history", summary="История изменений вакансии")
async def get_vacancy_history(
    vacancy_id: int,
    start_date: Optional[str] = Query(None),
    end_date:   Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import date as _date
    from services.vacancy_history_service import VacancyHistoryService, ROLE_LABELS
    import json as _json

    sd = _date.fromisoformat(start_date) if start_date else None
    ed = _date.fromisoformat(end_date)   if end_date   else None

    svc = VacancyHistoryService(db)
    records = await svc.get_history(vacancy_id, sd, ed)

    def _user_info(u):
        if not u:
            return {"id": None, "full_name": "Система", "email": None, "role_label": ""}
        role_val = u.role.value if hasattr(u.role, "value") else str(u.role)
        role_label = ROLE_LABELS.get(role_val, role_val)
        return {
            "id":         u.id,
            "full_name":  u.full_name or u.email or f"ID {u.id}",
            "email":      u.email,
            "role_label": role_label,
        }

    return [
        {
            "id":               r.id,
            "action_type":      r.action_type,
            "changes":          _json.loads(r.changes) if r.changes else {},
            "vacancy_snapshot": r.vacancy_snapshot,
            "created_at":       r.created_at.isoformat() if r.created_at else None,
            "user":             _user_info(r.user),
        }
        for r in records
    ]