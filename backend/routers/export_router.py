\
\
\
\
   
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, List
from io import BytesIO
from datetime import datetime, timedelta, date
from enum import Enum
import pandas as pd

from database import get_db
from models import User, Vacancy, UserRole
from schemas import SmartExportRequest
from auth import get_current_user
from services.vacancy_filter import apply_vacancy_filters

router = APIRouter(prefix="/export", tags=["Экспорт"])

class ExportPeriod(str, Enum):
    CURRENT_WEEK = "current_week"
    CURRENT_MONTH = "current_month"
    LAST_MONTH = "last_month"
    CURRENT_YEAR = "current_year"
    ALL_TIME = "all_time"
    CUSTOM = "custom"

def get_period_dates(period: str, start_date: Optional[date] = None, end_date: Optional[date] = None):
                                                   
    today = datetime.now().date()
    
    if period == "current_week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif period == "current_month":
        start = today.replace(day=1)
        if today.month == 12:
            end = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            end = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    elif period == "last_month":
        first_of_this = today.replace(day=1)
        end = first_of_this - timedelta(days=1)
        start = end.replace(day=1)
    elif period == "current_year":
        start = today.replace(month=1, day=1)
        end = today.replace(month=12, day=31)
    elif period == "custom" and start_date and end_date:
        start = start_date
        end = end_date
    else:            
        start = None
        end = None
    
    return start, end

def build_vacancy_query_with_filters(
    query,
    current_user: User,
    filters: Optional[dict] = None,
    search: Optional[str] = None,
    sort_field: Optional[str] = None,
    sort_order: Optional[str] = "desc",
    filter_start: Optional[date] = None,
    filter_end: Optional[date] = None,
):
\
\
\
       
                                                             
    kwargs: dict = {}
    if filters:
        for field, values in filters.items():
            if values:
                kwargs[field] = values

    query, _ = apply_vacancy_filters(
        query,
        current_user,
        search=search,
        date_from=filter_start,
        date_to=filter_end,
        **kwargs,
    )

                                                                    
    if sort_field:
        sort_column = getattr(Vacancy, sort_field, None)
        if sort_column is not None:
            query = query.order_by(sort_column.asc() if sort_order == "asc" else sort_column.desc())
        else:
            query = query.order_by(Vacancy.id.desc())
    else:
        query = query.order_by(Vacancy.id.desc())

    return query

def build_excel_from_vacancies(vacancies: List[Vacancy], period: str) -> tuple[BytesIO, str]:
\
\
\
\
       
    data = []
    for v in vacancies:
                                                                           
                                                                               
        reports = v.weekly_reports or []
        resume_at_customer = sum(r.resumes_sent or 0        for r in reports)
        resume_approved    = sum(r.candidates_agreed or 0   for r in reports)
        interviews_fact    = sum(r.interviews_conducted or 0 for r in reports)
        interviews_plan    = sum(r.interviews_planned or 0  for r in reports)
        offer_made         = sum(r.offer_made or 0          for r in reports)

                                                                            
        work_duration = v.work_duration_days                                     
        if work_duration is None and v.open_date and v.close_date:
            work_duration = (v.close_date - v.open_date).days

                                                                           
        row = {
                                         
            "ID вакансии":                    v.vacancy_id or "",
            "Дата открытия":                  str(v.open_date) if v.open_date else "",
                                   
            "Количество":                     v.quantity or 0,
                                              
            "Уровень специалиста":            v.level.value if v.level else "",
            "Вакансия":                       v.position_name or "",
                                        
            "Статус вакансии":                v.status.value if v.status else "",
            "ИТ роль":                        v.it_role.value if v.it_role else "",
                                                
            "Адм. руководитель":              v.admin_manager.value if v.admin_manager else "",
            "Тимлид":                         v.team_lead.value if v.team_lead else "",
            "Проект":                         v.project.value if v.project else "",
                                                                    
            "Передано заказчику":             resume_at_customer,
            "Резюме одобрено":                resume_approved,
            "Собеседования факт":             interviews_fact,
            "Собеседования план":             interviews_plan,
            "Оффер сделан":                   offer_made,
                                           
            "Город":                          v.city.value if v.city else (v.city_text or ""),
            "Источник найма":                 v.source.value if v.source else "",
            "Внутренний перевод":             v.internal_transfer.value if v.internal_transfer else "",
                                 
            "Дата изм. статуса":              str(v.status_changed_at) if v.status_changed_at else "",
            "Дата закрытия":                  str(v.close_date) if v.close_date else "",
                                     
            "ФИО кандидата":                  v.candidate_name or "",
            "Компания кандидата":             v.candidate_company or "",
                                   
            "Новая / Замена":                 v.replacement_type.value if v.replacement_type else "",
            "ФИО бывшего сотр.":              v.ex_employee_name or "",
                                      
            "ID ШЕ":                          v.unit_id or "",
            "Вид занятости":                  v.employment_type.value if v.employment_type else "",
            "ТЭО проекта":                    v.feasibility.value if v.feasibility else "",
            "Ссылка IQHR":                    v.iqhr_link or "",
                                            
            "Рекрутер":                       v.recruiter.full_name if v.recruiter else "",
            "Блок":                           v.block.value if v.block else "",
                                           
            "Срок работы (дней)":             work_duration if work_duration is not None else "",
            "Зарплата кандидатов Gross":      v.salary_gross or "",
        }
        data.append(row)

    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Вакансии', index=False, startrow=0)

        workbook  = writer.book
        worksheet = writer.sheets['Вакансии']

        if len(data) > 0:
            max_row = len(data)
            max_col = len(df.columns) - 1
            worksheet.add_table(0, 0, max_row, max_col, {
                'name': 'VacanciesTable',
                'style': 'Table Style Medium 9',
                'columns': [{'header': col} for col in df.columns],
            })
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(idx, idx, min(max_len, 35))

    output.seek(0)

    period_names = {
        "current_week": "week", "current_month": "month",
        "current_year": "year", "all_time": "all", "custom": "custom",
    }
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"vacancies_{period_names.get(period, 'export')}_{timestamp}.xlsx"

    return output, filename

@router.get("/vacancies")
async def export_vacancies_excel(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    period: ExportPeriod = Query(ExportPeriod.ALL_TIME, description="Export period"),
    start_date: Optional[date] = Query(None, description="Custom start date"),
    end_date: Optional[date] = Query(None, description="Custom end date"),
                                                          
    status_id: Optional[List[int]] = Query(None),
    project_id: Optional[List[int]] = Query(None),
    recruiter_id: Optional[List[int]] = Query(None),
    it_role_id: Optional[List[int]] = Query(None),
    level_id: Optional[List[int]] = Query(None),
    city_id: Optional[List[int]] = Query(None),
    source_id: Optional[List[int]] = Query(None),
    block_id: Optional[List[int]] = Query(None),
    employment_type_id: Optional[List[int]] = Query(None),
    feasibility_id: Optional[List[int]] = Query(None),
    replacement_type_id: Optional[List[int]] = Query(None),
    admin_manager_id: Optional[List[int]] = Query(None),
    team_lead_id: Optional[List[int]] = Query(None),
    internal_transfer_id: Optional[List[int]] = Query(None),
                         
    search_vacancy_id: Optional[str] = Query(None),
    search_position_name: Optional[str] = Query(None),
    search_candidate_name: Optional[str] = Query(None),
    search_candidate_company: Optional[str] = Query(None),
    search_ex_employee_name: Optional[str] = Query(None),
    search_unit_id: Optional[str] = Query(None),
    search_salary_gross: Optional[str] = Query(None),
    search_iqhr_link: Optional[str] = Query(None),
):
                                                                         
    query = select(Vacancy).options(
        selectinload(Vacancy.recruiter),
        selectinload(Vacancy.level),
        selectinload(Vacancy.status),
        selectinload(Vacancy.it_role),
        selectinload(Vacancy.admin_manager),
        selectinload(Vacancy.team_lead),
        selectinload(Vacancy.project),
        selectinload(Vacancy.city),
        selectinload(Vacancy.source),
        selectinload(Vacancy.internal_transfer),
        selectinload(Vacancy.replacement_type),
        selectinload(Vacancy.employment_type),
        selectinload(Vacancy.feasibility),
        selectinload(Vacancy.block),
        selectinload(Vacancy.weekly_reports),
    )
    
                                                           
    filter_start, filter_end = get_period_dates(period.value, start_date, end_date)
    query, _ = apply_vacancy_filters(
        query,
        current_user,
        status_id=status_id,
        project_id=project_id,
        recruiter_id=recruiter_id,
        it_role_id=it_role_id,
        level_id=level_id,
        city_id=city_id,
        source_id=source_id,
        block_id=block_id,
        employment_type_id=employment_type_id,
        feasibility_id=feasibility_id,
        replacement_type_id=replacement_type_id,
        admin_manager_id=admin_manager_id,
        team_lead_id=team_lead_id,
        internal_transfer_id=internal_transfer_id,
        search_vacancy_id=search_vacancy_id,
        search_position_name=search_position_name,
        search_candidate_name=search_candidate_name,
        search_candidate_company=search_candidate_company,
        search_ex_employee_name=search_ex_employee_name,
        search_unit_id=search_unit_id,
        search_salary_gross=search_salary_gross,
        search_iqhr_link=search_iqhr_link,
        date_from=filter_start,
        date_to=filter_end,
    )
    query = query.order_by(Vacancy.id)
    result = await db.execute(query)
    vacancies = result.scalars().all()
    
    output, filename = build_excel_from_vacancies(vacancies, period.value)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
    )

@router.post("/vacancies/smart")
async def export_vacancies_smart(
    export_request: SmartExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
\
       
    
                                    
    query = select(Vacancy).options(
        selectinload(Vacancy.recruiter),
        selectinload(Vacancy.level),
        selectinload(Vacancy.status),
        selectinload(Vacancy.it_role),
        selectinload(Vacancy.admin_manager),
        selectinload(Vacancy.team_lead),
        selectinload(Vacancy.project),
        selectinload(Vacancy.city),
        selectinload(Vacancy.source),
        selectinload(Vacancy.internal_transfer),
        selectinload(Vacancy.replacement_type),
        selectinload(Vacancy.employment_type),
        selectinload(Vacancy.feasibility),
        selectinload(Vacancy.block),
        selectinload(Vacancy.weekly_reports),
    )
    
                      
    filter_start, filter_end = get_period_dates(
        export_request.period or "all_time",
        export_request.start_date,
        export_request.end_date
    )
    
                                     
    filters_to_apply = export_request.filters if export_request.apply_filters else None
    
    query = build_vacancy_query_with_filters(
        query=query,
        current_user=current_user,
        filters=filters_to_apply,
        search=export_request.search if export_request.apply_filters else None,
        sort_field=export_request.sort_field,
        sort_order=export_request.sort_order,
        filter_start=filter_start,
        filter_end=filter_end,
    )
    
    result = await db.execute(query)
    vacancies = result.scalars().all()
    
    output, filename = build_excel_from_vacancies(vacancies, export_request.period or "all_time")
    
                                                    
    if export_request.apply_filters and export_request.filters:
        filename = filename.replace(".xlsx", "_filtered.xlsx")
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
    )