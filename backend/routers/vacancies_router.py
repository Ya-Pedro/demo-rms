\
\
\
\
   
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from io import BytesIO
import logging
import pandas as pd
from fastapi_cache import FastAPICache

from database import get_db
from models import User, Dictionary, UserRole, Vacancy, WeeklyReport
from schemas import VacancyCreate, VacancyUpdate, VacancyResponse, VacancyListResponse
from auth import get_current_user
from services.vacancy_service import VacancyService, vacancy_to_dict, get_current_week_info, get_current_week_monday
from datetime import datetime, timezone

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
    search_quantity: Optional[str] = Query(None),
    search_work_duration_days: Optional[str] = Query(None),
    search_resume_at_customer: Optional[str] = Query(None),
    search_resume_approved: Optional[str] = Query(None),
    search_interviews_fact: Optional[str] = Query(None),
    search_interviews_plan: Optional[str] = Query(None),
    search_offer_made: Optional[str] = Query(None),
    search_open_date: Optional[str] = Query(None),
    search_close_date: Optional[str] = Query(None),
    search_status_changed_at: Optional[str] = Query(None),
    sort_field: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("desc"),
    week_number: Optional[int] = Query(None),
    year: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    print(f"DEBUG get_vacancies: user={current_user.email}, role={current_user.role}, exclude_status_id={exclude_status_id}", flush=True)
    filter_params = {k: v for k, v in locals().items()
                     if k not in ("db", "current_user", "skip", "limit",
                                  "sort_field", "sort_order", "week_number",
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

@router.get("/{vacancy_id}", response_model=VacancyResponse)
async def get_vacancy(
    vacancy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = VacancyService(db)
    vacancy = await service.get_vacancy_or_404(vacancy_id)
    service.check_recruiter_access(vacancy, current_user)
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

@router.post("/import")
async def import_vacancies(
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
        raise HTTPException(status_code=400, detail=f"Ошибка чтения файла: {str(e)}")

                                                                 
                                                                                         
    COL_MAP = {
                        
        "ID вакансии":               ("vacancy_id",        None),
        "Вакансия":                  ("position_name",     None),
        "Количество":                ("quantity",          None),
        "Зарплата кандидатов Gross": ("salary_gross",      None),
        "ФИО кандидата":             ("candidate_name",    None),
        "Компания кандидата":        ("candidate_company", None),
        "ФИО бывшего сотр.":         ("ex_employee_name",  None),
        "ID ШЕ":                     ("unit_id",           None),
        "Ссылка IQHR":               ("iqhr_link",         None),
                                                                     
        "Передано заказчику":        ("resume_at_customer", None),
        "Резюме одобрено":           ("resume_approved",    None),
        "Собеседования факт":        ("interviews_fact",    None),
        "Собеседования план":        ("interviews_plan",    None),
        "Оффер сделан":              ("offer_made",         None),
                     
        "Уровень специалиста":       ("level_id",             "specialist_level"),
        "Статус вакансии":           ("status_id",            "vacancy_status"),
        "ИТ роль":                   ("it_role_id",           "it_role"),
        "Проект":                    ("project_id",           "project"),
        "Город":                     ("city_id",              "city"),
        "Источник найма":            ("source_id",            "source"),
        "Внутренний перевод":        ("internal_transfer_id", "internal_transfer"),
        "Новая / Замена":            ("replacement_type_id",  "replacement_type"),
        "Вид занятости":             ("employment_type_id",   "employment_type"),
        "ТЭО проекта":               ("feasibility_id",       "feasibility"),
        "Блок":                      ("block_id",             "block"),
        "Адм. руководитель":         ("admin_manager_id",     "admin_manager"),
        "Тимлид":                    ("team_lead_id",         "team_lead"),
    }
    DATE_COLS = {
        "Дата открытия":     "open_date",
        "Дата закрытия":     "close_date",
        "Дата изм. статуса": "status_changed_at",
    }
    FUNNEL_FIELDS = {"resume_at_customer", "resume_approved", "interviews_fact", "interviews_plan", "offer_made"}
    INT_FIELDS    = {"quantity", "salary_gross"}
    FUNNEL_MAP_WR = {
        "resume_at_customer": "resumes_sent",
        "resume_approved":    "candidates_agreed",
        "interviews_fact":    "interviews_conducted",
        "interviews_plan":    "interviews_planned",
        "offer_made":         "offer_made",
    }

    dict_result = await db.execute(select(Dictionary))
    dict_lookup = {(d.type, (d.value or "").strip().lower()): d.id for d in dict_result.scalars().all()}
    from models import User as UserModel
    user_result = await db.execute(select(UserModel))
    recruiter_lookup = {(u.full_name or "").strip().lower(): u.id for u in user_result.scalars().all()}

    created = updated = 0
    errors = []
    week_num, yr = get_current_week_info()
    week_start = get_current_week_monday()

    for idx, row in df.iterrows():
        try:
            data, funnel = {}, {}
            for excel_col, (field, dict_type) in COL_MAP.items():
                if excel_col not in df.columns or pd.isna(row[excel_col]):
                    continue
                val = row[excel_col]
                if dict_type:
                    did = dict_lookup.get((dict_type, str(val).strip().lower()))
                    if did:
                        data[field] = did
                elif field in FUNNEL_FIELDS:
                    funnel[field] = int(val) if val else 0
                elif field in INT_FIELDS:
                    try:
                        data[field] = int(float(str(val)))
                    except (ValueError, TypeError):
                        pass
                else:
                    data[field] = str(val).strip() if val else None

            for excel_col, field in DATE_COLS.items():
                if excel_col in df.columns and not pd.isna(row.get(excel_col, float("nan"))):
                    try:
                        data[field] = pd.to_datetime(row[excel_col]).date()
                    except Exception:
                        pass

            if "Рекрутер" in df.columns and not pd.isna(row.get("Рекрутер", float("nan"))):
                r_id = recruiter_lookup.get(str(row["Рекрутер"]).strip().lower())
                if r_id:
                    data["recruiter_id"] = r_id

            if not data.get("vacancy_id"):
                errors.append(f"Строка {idx+2}: нет ID вакансии")
                continue

            existing = (await db.execute(select(Vacancy).where(Vacancy.vacancy_id == data["vacancy_id"]))).scalar_one_or_none()
            if existing:
                for k, v in data.items():
                    if k != "vacancy_id":
                        setattr(existing, k, v)
                vacancy_obj = existing
                updated += 1
            else:
                vacancy_obj = Vacancy(**data)
                db.add(vacancy_obj)
                await db.flush()
                created += 1

            if funnel and vacancy_obj.id:
                wr_data = {FUNNEL_MAP_WR[k]: v for k, v in funnel.items() if k in FUNNEL_MAP_WR}
                wr = (await db.execute(select(WeeklyReport).where(
                    WeeklyReport.vacancy_id == vacancy_obj.id,
                    WeeklyReport.week_number == week_num,
                    WeeklyReport.year == yr,
                ))).scalar_one_or_none()
                if wr:
                    for k, v in wr_data.items():
                        setattr(wr, k, v)
                else:
                    db.add(WeeklyReport(vacancy_id=vacancy_obj.id, week_number=week_num,
                                        year=yr, week_start=week_start,
                                        report_date=datetime.now(timezone.utc), **wr_data))
        except Exception as e:
            errors.append(f"Строка {idx+2}: {str(e)}")

    await db.commit()
    return {"created": created, "updated": updated, "errors": errors[:20], "total_rows": len(df)}

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