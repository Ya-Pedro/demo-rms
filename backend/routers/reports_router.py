\
\
\
\
\
\
   
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, date, timedelta
from io import BytesIO
import logging

import pandas as pd

from database import get_db
from models import User, Vacancy, WeeklyReport, UserRole
from schemas import (
    WeeklyReportCreate, WeeklyReportUpdate, WeeklyReportResponse, WeeklyReportListResponse
)
from auth import get_current_user
from services.vacancy_filter import apply_vacancy_filters
from services.delegation_service import DelegationService

router = APIRouter(prefix="/reports", tags=["Еженедельные отчеты"])
logger = logging.getLogger(__name__)

def get_current_week_info():
                                          
    now = datetime.now()
    week_number = now.isocalendar()[1]
    year = now.year
    return week_number, year

def _get_week_start(year: int, week: int) -> date:
                                                   
    jan4 = date(year, 1, 4)
    start_of_week1 = jan4 - timedelta(days=jan4.weekday())
    return start_of_week1 + timedelta(weeks=week - 1)

def _get_week_end(year: int, week: int) -> date:
                                                   
    return _get_week_start(year, week) + timedelta(days=6)

@router.post("", response_model=WeeklyReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_data: WeeklyReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
                                                                    
    result = await db.execute(
        select(Vacancy).where(Vacancy.id == report_data.vacancy_id)
    )
    vacancy = result.scalar_one_or_none()
    
    if not vacancy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")
    
    if current_user.role == UserRole.RECRUITER and vacancy.recruiter_id != current_user.id:
        delegation_svc = DelegationService(db)
        if not await delegation_svc.has_delegated_access(vacancy.id, current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой вакансии")
    
                         
    existing = await db.execute(
        select(WeeklyReport).where(
            WeeklyReport.vacancy_id == report_data.vacancy_id,
            WeeklyReport.week_number == report_data.week_number,
            WeeklyReport.year == report_data.year
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Отчет за неделю {report_data.week_number} уже существует. Используйте редактирование."
        )
    
                          
    week_start = _get_week_start(report_data.year, report_data.week_number)
    
    report_dict = report_data.model_dump()
    report_dict['week_start'] = week_start
    report_dict['report_date'] = datetime.now()
    
    new_report = WeeklyReport(**report_dict)
    db.add(new_report)

                                                                                                  
    await db.commit()
    await db.refresh(new_report)

                                  
    try:
        from services.vacancy_history_service import VacancyHistoryService
        _hist = VacancyHistoryService(db)
        await _hist.record_report_created(
            vacancy_id=vacancy.id,
            vacancy_name=vacancy.position_name,
            week_number=report_data.week_number,
            year=report_data.year,
            metrics={
                "resumes_sent":         report_data.resumes_sent,
                "candidates_agreed":    report_data.candidates_agreed,
                "interviews_planned":   report_data.interviews_planned,
                "interviews_conducted": report_data.interviews_conducted,
                "offer_made":           report_data.offer_made,
            },
            user=current_user,
        )
        await db.commit()
    except Exception:
        import logging, traceback
        logging.getLogger(__name__).warning(
            "history REPORT create failed:\n%s", traceback.format_exc()
        )

    return new_report

@router.get("/vacancy/{vacancy_id}", response_model=WeeklyReportListResponse)
async def get_vacancy_reports(
    vacancy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(52, ge=1, le=100),
):
                                                        
    result = await db.execute(select(Vacancy).where(Vacancy.id == vacancy_id))
    vacancy = result.scalar_one_or_none()
    
    if not vacancy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")
    
    if current_user.role == UserRole.RECRUITER and vacancy.recruiter_id != current_user.id:
        delegation_svc = DelegationService(db)
        if not await delegation_svc.has_delegated_access(vacancy.id, current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этой вакансии")
    
    count_query = select(func.count(WeeklyReport.id)).where(WeeklyReport.vacancy_id == vacancy_id)
    total = (await db.execute(count_query)).scalar()
    
    query = select(WeeklyReport).where(
        WeeklyReport.vacancy_id == vacancy_id
    ).order_by(
        WeeklyReport.year.desc(),
        WeeklyReport.week_number.desc()
    ).offset(skip).limit(limit)
    
    result = await db.execute(query)
    reports = result.scalars().all()
    
    return WeeklyReportListResponse(items=reports, total=total)

@router.get("/current-week")
async def get_current_week(current_user: User = Depends(get_current_user)):
                                          
    week_number, year = get_current_week_info()
    return {"week_number": week_number, "year": year}

@router.get("/all")
async def get_all_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    year: Optional[int] = Query(None),
    week_number: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    recruiter_id: Optional[List[int]] = Query(None),
    project_id: Optional[List[int]] = Query(None),
    vacancy_search: Optional[str] = Query(None),
                          
    sort_field: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("desc"),
                                   
    search_vacancy_id: Optional[str] = Query(None),
    search_vacancy_name: Optional[str] = Query(None),
    search_recruiter: Optional[str] = Query(None),
    search_status: Optional[str] = Query(None),
    search_candidate: Optional[str] = Query(None),
):
\
\
\
\
\
       
                                                
    conditions = []
                                                           
    if current_user.role == UserRole.RECRUITER:
        from sqlalchemy import or_
        from datetime import date as _date
        from models import VacancyDelegation
        today = _date.today()
        delegated_subq = (
            select(VacancyDelegation.vacancy_id)
            .where(
                VacancyDelegation.delegated_to_id == current_user.id,
                VacancyDelegation.is_active == True,
                VacancyDelegation.start_date <= today,
                VacancyDelegation.end_date >= today,
            )
        )
        conditions.append(
            or_(
                Vacancy.recruiter_id == current_user.id,
                Vacancy.id.in_(delegated_subq),
            )
        )
    
    if year is not None:
        conditions.append(WeeklyReport.year == year)
    if week_number is not None:
        conditions.append(WeeklyReport.week_number == week_number)
    
                                              
    if month is not None and year is not None:
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        conditions.append(WeeklyReport.week_start >= month_start)
        conditions.append(WeeklyReport.week_start <= month_end)
    elif month is not None:
                                                 
        cur_year = datetime.now().year
        month_start = date(cur_year, month, 1)
        if month == 12:
            month_end = date(cur_year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(cur_year, month + 1, 1) - timedelta(days=1)
        conditions.append(WeeklyReport.week_start >= month_start)
        conditions.append(WeeklyReport.week_start <= month_end)
    
                                                                  
    sd_str = start_date or date_from
    ed_str = end_date or date_to
    if sd_str:
        try:
            conditions.append(WeeklyReport.week_start >= date.fromisoformat(sd_str))
        except ValueError:
            pass
    if ed_str:
        try:
            conditions.append(WeeklyReport.week_start <= date.fromisoformat(ed_str))
        except ValueError:
            pass

    if recruiter_id:
        conditions.append(Vacancy.recruiter_id.in_(recruiter_id))
    if project_id:
        conditions.append(Vacancy.project_id.in_(project_id))
                                                                             
    if vacancy_search:
        conditions.append(
            (Vacancy.position_name.ilike(f"%{vacancy_search}%")) |
            (Vacancy.vacancy_id.ilike(f"%{vacancy_search}%"))
        )
    if search_vacancy_id:
        conditions.append(Vacancy.vacancy_id.ilike(f"%{search_vacancy_id}%"))
    if search_vacancy_name:
        conditions.append(Vacancy.position_name.ilike(f"%{search_vacancy_name}%"))
    if search_candidate:
        conditions.append(Vacancy.candidate_name.ilike(f"%{search_candidate}%"))

                                                         
    agg_q = (
        select(
            Vacancy.id.label('vacancy_db_id'),
            Vacancy.vacancy_id.label('vacancy_ext_id'),
            Vacancy.position_name.label('vacancy_name'),
            func.sum(WeeklyReport.resumes_sent).label('total_resumes_sent'),
            func.sum(WeeklyReport.candidates_agreed).label('total_candidates_agreed'),
            func.sum(WeeklyReport.interviews_planned).label('total_interviews_planned'),
            func.sum(WeeklyReport.interviews_conducted).label('total_interviews_conducted'),
            func.sum(WeeklyReport.offer_made).label('total_offer_made'),
            func.min(WeeklyReport.created_at).label('first_report_date'),
            func.max(WeeklyReport.updated_at).label('last_updated'),
            func.min(WeeklyReport.year).label('min_year'),
            func.max(WeeklyReport.year).label('max_year'),
            func.count(WeeklyReport.id).label('report_count'),
        )
        .join(Vacancy, WeeklyReport.vacancy_id == Vacancy.id)
    )
    
    if conditions:
        agg_q = agg_q.where(and_(*conditions))
    
    agg_q = agg_q.group_by(Vacancy.id, Vacancy.vacancy_id, Vacancy.position_name)
    
                        
    count_subq = agg_q.subquery()
    count_q = select(func.count()).select_from(count_subq)
    total = (await db.execute(count_q)).scalar()
    
                                         
                          
    SORT_MAP = {
        'vacancy_ext_id':             Vacancy.vacancy_id,
        'vacancy_name':               Vacancy.position_name,
        'open_date':                  Vacancy.open_date,
        'close_date':                 Vacancy.close_date,
        'quantity':                   Vacancy.quantity,
        'salary_gross':               Vacancy.salary_gross,
        'work_duration_days':         Vacancy.id,               
        'total_resumes_sent':         func.sum(WeeklyReport.resumes_sent),
        'total_candidates_agreed':    func.sum(WeeklyReport.candidates_agreed),
        'total_interviews_conducted': func.sum(WeeklyReport.interviews_conducted),
        'total_interviews_planned':   func.sum(WeeklyReport.interviews_planned),
        'total_offer_made':           func.sum(WeeklyReport.offer_made),
        'report_count':               func.count(WeeklyReport.id),
        'first_report_date':          func.min(WeeklyReport.created_at),
        'last_updated':               func.max(WeeklyReport.updated_at),
    }
    sort_col = SORT_MAP.get(sort_field, Vacancy.id)
    if sort_order == 'asc':
        agg_q = agg_q.order_by(sort_col.asc())
    else:
        agg_q = agg_q.order_by(sort_col.desc())
    agg_q = agg_q.offset(skip).limit(limit)
    
    rows = (await db.execute(agg_q)).all()
    
                                           
    vacancy_ids = [r.vacancy_db_id for r in rows]
    _VAC_OPTS = [
        selectinload(Vacancy.recruiter),
        selectinload(Vacancy.project),
        selectinload(Vacancy.admin_manager),
        selectinload(Vacancy.status),
        selectinload(Vacancy.level),
        selectinload(Vacancy.it_role),
        selectinload(Vacancy.city),
        selectinload(Vacancy.source),
        selectinload(Vacancy.internal_transfer),
        selectinload(Vacancy.replacement_type),
        selectinload(Vacancy.employment_type),
        selectinload(Vacancy.feasibility),
        selectinload(Vacancy.block),
    ]
    if vacancy_ids:
        vac_q = (
            select(Vacancy)
            .options(*_VAC_OPTS)
            .where(Vacancy.id.in_(vacancy_ids))
        )
        vac_result = await db.execute(vac_q)
        vac_map = {v.id: v for v in vac_result.scalars().all()}
    else:
        vac_map = {}

    items = []
    for r in rows:
        v = vac_map.get(r.vacancy_db_id)
        items.append({
            "id": r.vacancy_db_id,
            "vacancy_id": r.vacancy_db_id,
            "vacancy_ext_id": r.vacancy_ext_id,
            "vacancy_name": r.vacancy_name,
            "open_date": v.open_date.isoformat() if v and v.open_date else None,
            "close_date": v.close_date.isoformat() if v and v.close_date else None,
            "quantity": v.quantity if v else None,
            "level_name": v.level.value if v and v.level else None,
            "status_name": v.status.value if v and v.status else None,
            "it_role_name": v.it_role.value if v and v.it_role else None,
            "customer": (v.admin_manager.value if v and v.admin_manager else
                        (v.project.value if v and v.project else "-")),
            "recruiter_name": v.recruiter.full_name if v and v.recruiter else None,
            "project_name": v.project.value if v and v.project else None,
            "city_name": v.city.value if v and v.city else (v.city_text if v else None),
            "source_name": v.source.value if v and v.source else None,
            "internal_transfer_name": v.internal_transfer.value if v and v.internal_transfer else None,
            "status_changed_at": v.status_changed_at.isoformat() if v and v.status_changed_at else None,
            "candidate_name": v.candidate_name if v else None,
            "candidate_company": v.candidate_company if v else None,
            "replacement_type_name": v.replacement_type.value if v and v.replacement_type else None,
            "ex_employee_name": v.ex_employee_name if v else None,
            "unit_id": v.unit_id if v else None,
            "employment_type_name": v.employment_type.value if v and v.employment_type else None,
            "feasibility_name": v.feasibility.value if v and v.feasibility else None,
            "iqhr_link": v.iqhr_link if v else None,
            "block_name": v.block.value if v and v.block else None,
            "work_duration_days": v.work_duration_days if v else None,
            "salary_gross": v.salary_gross if v else None,
            "year": f"{r.min_year}" if r.min_year == r.max_year else f"{r.min_year}-{r.max_year}",
            "total_resumes_sent": r.total_resumes_sent or 0,
            "total_candidates_agreed": r.total_candidates_agreed or 0,
            "total_interviews_planned": r.total_interviews_planned or 0,
            "total_interviews_conducted": r.total_interviews_conducted or 0,
            "total_offer_made": r.total_offer_made or 0,
            "first_report_date": r.first_report_date.isoformat() if r.first_report_date else None,
            "last_updated": r.last_updated.isoformat() if r.last_updated else (
                r.first_report_date.isoformat() if r.first_report_date else None
            ),
            "report_count": r.report_count,
        })

    return {"items": items, "total": total}

@router.get("/all/export")
async def export_all_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    year: Optional[int] = Query(None),
    week_number: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    recruiter_id: Optional[List[int]] = Query(None),
    project_id: Optional[List[int]] = Query(None),
    vacancy_search: Optional[str] = Query(None),
    sort_field: Optional[str] = Query(None),
    sort_order: Optional[str] = Query("desc"),
):
\
\
       
                                                      
    conditions = []
                                                                
    if current_user.role == UserRole.RECRUITER:
        from sqlalchemy import or_
        from datetime import date as _date
        from models import VacancyDelegation
        today = _date.today()
        delegated_subq = (
            select(VacancyDelegation.vacancy_id)
            .where(
                VacancyDelegation.delegated_to_id == current_user.id,
                VacancyDelegation.is_active == True,
                VacancyDelegation.start_date <= today,
                VacancyDelegation.end_date >= today,
            )
        )
        conditions.append(
            or_(
                Vacancy.recruiter_id == current_user.id,
                Vacancy.id.in_(delegated_subq),
            )
        )
    if year is not None:
        conditions.append(WeeklyReport.year == year)
    if week_number is not None:
        conditions.append(WeeklyReport.week_number == week_number)
    if month is not None:
        y = year if year else datetime.now().year
        month_start = date(y, month, 1)
        if month == 12:
            month_end = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(y, month + 1, 1) - timedelta(days=1)
        conditions.append(WeeklyReport.week_start >= month_start)
        conditions.append(WeeklyReport.week_start <= month_end)
    sd_str = start_date or date_from
    ed_str = end_date or date_to
    if sd_str:
        try:
            conditions.append(WeeklyReport.week_start >= date.fromisoformat(sd_str))
        except ValueError:
            pass
    if ed_str:
        try:
            conditions.append(WeeklyReport.week_start <= date.fromisoformat(ed_str))
        except ValueError:
            pass
    if recruiter_id:
        conditions.append(Vacancy.recruiter_id.in_(recruiter_id))
    if project_id:
        conditions.append(Vacancy.project_id.in_(project_id))
                                                                
    if vacancy_search:
        conditions.append(
            (Vacancy.position_name.ilike(f"%{vacancy_search}%")) |
            (Vacancy.vacancy_id.ilike(f"%{vacancy_search}%"))
        )

    agg_q = (
        select(
            Vacancy.id.label('vacancy_db_id'),
            Vacancy.vacancy_id.label('vacancy_ext_id'),
            Vacancy.position_name.label('vacancy_name'),
            func.sum(WeeklyReport.resumes_sent).label('total_resumes_sent'),
            func.sum(WeeklyReport.candidates_agreed).label('total_candidates_agreed'),
            func.sum(WeeklyReport.interviews_planned).label('total_interviews_planned'),
            func.sum(WeeklyReport.interviews_conducted).label('total_interviews_conducted'),
            func.sum(WeeklyReport.offer_made).label('total_offer_made'),
            func.min(WeeklyReport.created_at).label('first_report_date'),
            func.max(WeeklyReport.updated_at).label('last_updated'),
            func.min(WeeklyReport.year).label('min_year'),
            func.max(WeeklyReport.year).label('max_year'),
        )
        .join(Vacancy, WeeklyReport.vacancy_id == Vacancy.id)
    )
    if conditions:
        agg_q = agg_q.where(and_(*conditions))
    agg_q = agg_q.group_by(Vacancy.id, Vacancy.vacancy_id, Vacancy.position_name)
                           
    SORT_MAP_EXP = {
        'vacancy_ext_id':             Vacancy.vacancy_id,
        'vacancy_name':               Vacancy.position_name,
        'open_date':                  Vacancy.open_date,
        'close_date':                 Vacancy.close_date,
        'quantity':                   Vacancy.quantity,
        'salary_gross':               Vacancy.salary_gross,
        'total_resumes_sent':         func.sum(WeeklyReport.resumes_sent),
        'total_candidates_agreed':    func.sum(WeeklyReport.candidates_agreed),
        'total_interviews_conducted': func.sum(WeeklyReport.interviews_conducted),
        'total_interviews_planned':   func.sum(WeeklyReport.interviews_planned),
        'total_offer_made':           func.sum(WeeklyReport.offer_made),
        'report_count':               func.count(WeeklyReport.id),
    }
    sort_col_exp = SORT_MAP_EXP.get(sort_field, Vacancy.id)
    if sort_order == 'asc':
        agg_q = agg_q.order_by(sort_col_exp.asc())
    else:
        agg_q = agg_q.order_by(sort_col_exp.desc())

    rows = (await db.execute(agg_q)).all()

    _VAC_OPTS_EXPORT = [
        selectinload(Vacancy.recruiter),
        selectinload(Vacancy.project),
        selectinload(Vacancy.admin_manager),
        selectinload(Vacancy.status),
        selectinload(Vacancy.level),
        selectinload(Vacancy.it_role),
        selectinload(Vacancy.city),
        selectinload(Vacancy.source),
        selectinload(Vacancy.internal_transfer),
        selectinload(Vacancy.replacement_type),
        selectinload(Vacancy.employment_type),
        selectinload(Vacancy.feasibility),
        selectinload(Vacancy.block),
    ]
    vacancy_ids = [r.vacancy_db_id for r in rows]
    vac_map = {}
    if vacancy_ids:
        vac_q = (
            select(Vacancy)
            .options(*_VAC_OPTS_EXPORT)
            .where(Vacancy.id.in_(vacancy_ids))
        )
        vac_result = await db.execute(vac_q)
        vac_map = {v.id: v for v in vac_result.scalars().all()}

    excel_rows = []
    for r in rows:
        v = vac_map.get(r.vacancy_db_id)
        excel_rows.append({
            "ID вакансии": r.vacancy_ext_id or "",
            "Дата открытия": str(v.open_date) if v and v.open_date else "",
            "Кол-во": v.quantity if v else "",
            "Уровень": v.level.value if v and v.level else "",
            "Вакансия": r.vacancy_name or "",
            "Статус": v.status.value if v and v.status else "",
            "ИТ Роль": v.it_role.value if v and v.it_role else "",
            "Заказчик": (v.admin_manager.value if v and v.admin_manager else
                        (v.project.value if v and v.project else "")),
            "Проект": v.project.value if v and v.project else "",
            "Рекрутер": v.recruiter.full_name if v and v.recruiter else "",
            "Передано заказчику": r.total_resumes_sent or 0,
            "Резюме одобрено": r.total_candidates_agreed or 0,
            "Соб. факт": r.total_interviews_conducted or 0,
            "Соб. план": r.total_interviews_planned or 0,
            "Оффер сделан": r.total_offer_made or 0,
            "Город": v.city.value if v and v.city else (v.city_text or ""),
            "Источник найма": v.source.value if v and v.source else "",
            "Внутр. перевод": v.internal_transfer.value if v and v.internal_transfer else "",
            "Дата изм. статуса": str(v.status_changed_at) if v and v.status_changed_at else "",
            "Дата закрытия": str(v.close_date) if v and v.close_date else "",
            "ФИО кандидата": v.candidate_name or "",
            "Компания кандидата": v.candidate_company or "",
            "Новая/Замена": v.replacement_type.value if v and v.replacement_type else "",
            "ФИО бывшего сотр.": v.ex_employee_name or "",
            "ID ШЕ": v.unit_id or "",
            "Вид занятости": v.employment_type.value if v and v.employment_type else "",
            "ТЭО": v.feasibility.value if v and v.feasibility else "",
            "Блок": v.block.value if v and v.block else "",
            "Срок работы (дней)": v.work_duration_days if v and v.work_duration_days is not None else "",
            "Зарплата Gross": v.salary_gross or "",
            "Год": f"{r.min_year}" if r.min_year == r.max_year else f"{r.min_year}-{r.max_year}",
            "Дата создания": r.first_report_date.strftime("%d.%m.%Y %H:%M") if r.first_report_date else "",
            "Дата обновления": r.last_updated.strftime("%d.%m.%Y %H:%M") if r.last_updated else "",
        })

    df = pd.DataFrame(excel_rows)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="Отчеты", index=False)
        if len(excel_rows) > 0:
            wb = writer.book
            ws = writer.sheets["Отчеты"]
                                                                      
            ws.autofilter(0, 0, len(excel_rows), len(df.columns) - 1)
                                       
            hdr_fmt = wb.add_format({
                'bold': True, 'bg_color': '#F5F5F5', 'border': 1,
                'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
            })
            num_fmt  = wb.add_format({'num_format': '#,##0'})
            date_fmt = wb.add_format({'num_format': 'dd.mm.yy'})
            for idx, col in enumerate(df.columns):
                                
                max_len = max(df[col].astype(str).map(len).max() if len(df) > 0 else 0, len(col)) + 2
                ws.set_column(idx, idx, min(max_len, 40))
                                      
                ws.write(0, idx, col, hdr_fmt)
                                      
            ws.freeze_panes(1, 0)
    output.seek(0)

    filename = f"reports_export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.get("/{report_id}", response_model=WeeklyReportResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
                                     
    result = await db.execute(
        select(WeeklyReport)
        .options(selectinload(WeeklyReport.vacancy))
        .where(WeeklyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отчет не найден")
    
    if current_user.role == UserRole.RECRUITER and report.vacancy.recruiter_id != current_user.id:
        delegation_svc = DelegationService(db)
        if not await delegation_svc.has_delegated_access(report.vacancy.id, current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому отчету")
    
    return report

@router.patch("/{report_id}", response_model=WeeklyReportResponse)
async def update_report(
    report_id: int,
    report_data: WeeklyReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
                                                                       
    result = await db.execute(
        select(WeeklyReport)
        .options(selectinload(WeeklyReport.vacancy))
        .where(WeeklyReport.id == report_id)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отчет не найден")

    if current_user.role == UserRole.RECRUITER and report.vacancy.recruiter_id != current_user.id:
        delegation_svc = DelegationService(db)
        if not await delegation_svc.has_delegated_access(report.vacancy.id, current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому отчету")

    update_data = report_data.model_dump(exclude_unset=True)

    _old_metrics = {
        "resumes_sent":         report.resumes_sent,
        "candidates_agreed":    report.candidates_agreed,
        "interviews_planned":   report.interviews_planned,
        "interviews_conducted": report.interviews_conducted,
        "offer_made":           report.offer_made,
    }

    for field, value in update_data.items():
        setattr(report, field, value)

    await db.commit()
    await db.refresh(report)

                                    
    try:
        from services.vacancy_history_service import VacancyHistoryService
        _hist2 = VacancyHistoryService(db)
        _new_metrics = {
            "resumes_sent":         report.resumes_sent,
            "candidates_agreed":    report.candidates_agreed,
            "interviews_planned":   report.interviews_planned,
            "interviews_conducted": report.interviews_conducted,
            "offer_made":           report.offer_made,
        }
        await _hist2.record_report_updated(
            vacancy_id=report.vacancy_id,
            vacancy_name=report.vacancy.position_name if report.vacancy else f"Вакансия #{report.vacancy_id}",
            week_number=report.week_number,
            year=report.year,
            old_metrics=_old_metrics,
            new_metrics=_new_metrics,
            user=current_user,
        )
        await db.commit()
    except Exception:
        import logging, traceback
        logging.getLogger(__name__).warning(
            "history REPORT update failed:\n%s", traceback.format_exc()
        )

    return report

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
                                
    result = await db.execute(
        select(WeeklyReport)
        .options(selectinload(WeeklyReport.vacancy))
        .where(WeeklyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отчет не найден")
    
    if current_user.role == UserRole.RECRUITER and report.vacancy.recruiter_id != current_user.id:
        delegation_svc = DelegationService(db)
        if not await delegation_svc.has_delegated_access(report.vacancy.id, current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому отчету")
    
    await db.delete(report)
    await db.commit()