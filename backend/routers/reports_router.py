\
\
\
\
\
\
   
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case, Integer
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime, date, timedelta
from io import BytesIO
import logging

import pandas as pd
from fastapi_cache import FastAPICache

from database import get_db
from models import User, Vacancy, WeeklyReport, UserRole, Dictionary, DictionaryType
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

def is_week_editable_for_recruiter(week_number: int, year: int) -> bool:
    """Recruiter can only edit/create reports for current week and previous week."""
    now = datetime.now()
    cur_year, cur_week, _ = now.isocalendar()
    week_start = _get_week_start(year, week_number)
    cur_week_start = _get_week_start(cur_year, cur_week)
    diff_days = (cur_week_start - week_start).days
    return diff_days <= 7

async def _get_inactive_status_ids(db: AsyncSession) -> list[int]:
    result = await db.execute(
        select(Dictionary.id).where(
            Dictionary.type == DictionaryType.VACANCY_STATUS,
            Dictionary.value.in_(["Закрыта", "Отмена", "Hold"]),
        )
    )
    return list(result.scalars().all())

@router.post("", response_model=WeeklyReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    report_data: WeeklyReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.RECRUITER and not is_week_editable_for_recruiter(report_data.week_number, report_data.year):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Рекрутер может редактировать отчеты только за текущую и предыдущую недели"
        )

    result = await db.execute(
        select(Vacancy).where(Vacancy.id == report_data.vacancy_id)
    )
    vacancy = result.scalar_one_or_none()
    
    if not vacancy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")
    
    if current_user.role == UserRole.RECRUITER and vacancy.recruiter_id != current_user.id and vacancy.co_recruiter_id != current_user.id:
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
                "offer_accepted":       getattr(report_data, 'offer_accepted', 0),
            },
            user=current_user,
        )
        await db.commit()
        await FastAPICache.clear(namespace="dashboards")
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
    
    if current_user.role == UserRole.RECRUITER and vacancy.recruiter_id != current_user.id and vacancy.co_recruiter_id != current_user.id:
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
    request: Request,
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
    
    from services.vacancy_filter import apply_vacancy_filters
    qp = request.query_params
    
    def get_list(key: str):
        vals = qp.getlist(key)
        if not vals:
            return None
        res = []
        for v in vals:
            if v.lstrip('-').isdigit():
                res.append(int(v))
        return res if res else None
        
    def get_str(key: str):
        v = qp.get(key)
        return v if v else None
        
    rec_vals = qp.getlist('recruiter_name')
    rec_ids = [int(v) for v in rec_vals if v.lstrip('-').isdigit()] or None
    rec_str = next((v for v in rec_vals if not v.lstrip('-').isdigit() and v.strip()), None) or get_str('search_recruiter')

    co_rec_vals = qp.getlist('co_recruiter_name')
    co_rec_ids = [int(v) for v in co_rec_vals if v.lstrip('-').isdigit()] or None
    co_rec_str = next((v for v in co_rec_vals if not v.lstrip('-').isdigit() and v.strip()), None) or get_str('search_co_recruiter')

    _, vacancy_conditions = apply_vacancy_filters(
        query=select(Vacancy),
        current_user=current_user,
        status_id=get_list('status_name') or get_list('status_id'),
        level_id=get_list('level_name') or get_list('level_id'),
        it_role_id=get_list('it_role_name') or get_list('it_role_id'),
        project_id=get_list('project_name') or get_list('project_id'),
        admin_manager_id=get_list('customer') or get_list('admin_manager_id'),
        source_id=get_list('source_name') or get_list('source_id'),
        block_id=get_list('block_name') or get_list('block_id'),
        employment_type_id=get_list('employment_type_name') or get_list('employment_type_id'),
        search_feasibility_text=get_str('feasibility_name') or get_str('feasibility_text'),
        replacement_type_id=get_list('replacement_type_name') or get_list('replacement_type_id'),
        internal_transfer_id=get_list('internal_transfer_name') or get_list('internal_transfer_id'),
        recruiter_id=rec_ids,
        co_recruiter_id=co_rec_ids,
        search_recruiter=rec_str,
        search_co_recruiter=co_rec_str,
        
        search_vacancy_id=get_str('vacancy_ext_id'),
        search_position_name=get_str('vacancy_name'),
        search_candidate_name=get_str('candidate_name'),
        search_team_lead_text=get_str('team_lead_name'),
        search_city_text=get_str('city_name'),
        search_candidate_company=get_str('candidate_company'),
        search_ex_employee_name=get_str('ex_employee_name'),
        search_unit_id=get_str('unit_id'),
        search_iqhr_link=get_str('iqhr_link'),
        search_comment=get_str('comment'),
        search_offer_rejection_reason=get_str('offer_rejection_reason'),
        search_quantity=get_str('quantity'),
        search_salary_gross=get_str('salary_gross'),
        search_work_duration_days=get_str('work_duration_days'),
        search_open_date=get_str('open_date') or get_str('search_open_date'),
        search_open_date_from=get_str('open_date_from') or get_str('search_open_date_from'),
        search_open_date_to=get_str('open_date_to') or get_str('search_open_date_to'),
        search_close_date=get_str('close_date') or get_str('search_close_date'),
        search_close_date_from=get_str('close_date_from') or get_str('search_close_date_from'),
        search_close_date_to=get_str('close_date_to') or get_str('search_close_date_to'),
        search_status_changed_at=get_str('status_changed_at') or get_str('search_status_changed_at'),
        search_status_changed_at_from=get_str('status_changed_at_from') or get_str('search_status_changed_at_from'),
        search_status_changed_at_to=get_str('status_changed_at_to') or get_str('search_status_changed_at_to'),
    )
    print(f"DEBUG: get_all_reports query_params={qp}")
    print(f"DEBUG: vacancy_conditions={vacancy_conditions}")
    conditions.extend(vacancy_conditions)
                                                           
    if current_user.role == UserRole.RECRUITER:
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
                Vacancy.co_recruiter_id == current_user.id,
                Vacancy.id.in_(delegated_subq),
            )
        )
    
    p_start = None
    p_end = None

    if week_number is not None:
        y = year if year is not None else datetime.now().year
        p_start = _get_week_start(y, week_number)
        p_end = _get_week_end(y, week_number)
    elif month is not None:
        y = year if year is not None else datetime.now().year
        p_start = date(y, month, 1)
        if month == 12:
            p_end = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            p_end = date(y, month + 1, 1) - timedelta(days=1)
    elif year is not None:
        p_start = date(year, 1, 1)
        p_end = date(year, 12, 31)

    sd_str = start_date or date_from
    ed_str = end_date or date_to
    if isinstance(sd_str, str):
        try:
            sd_d = date.fromisoformat(sd_str)
            p_start = max(p_start, sd_d) if p_start else sd_d
        except (ValueError, TypeError):
            pass
    if isinstance(ed_str, str):
        try:
            ed_d = date.fromisoformat(ed_str)
            p_end = min(p_end, ed_d) if p_end else ed_d
        except (ValueError, TypeError):
            pass

    report_join_conditions = [WeeklyReport.vacancy_id == Vacancy.id]
    if week_number is not None:
        y = year if year is not None else datetime.now().year
        report_join_conditions.append(WeeklyReport.week_number == week_number)
        report_join_conditions.append(WeeklyReport.year == y)
    elif p_start and p_end:
        report_join_conditions.append(WeeklyReport.week_start >= p_start)
        report_join_conditions.append(WeeklyReport.week_start <= p_end)
    elif p_start:
        report_join_conditions.append(WeeklyReport.week_start >= p_start)
    elif p_end:
        report_join_conditions.append(WeeklyReport.week_start <= p_end)

    explicit_status = get_list('status_name')
    if not explicit_status:
        inactive_ids = await _get_inactive_status_ids(db)
        if inactive_ids and (p_start or p_end):
            status_or_conditions = []
            active_cond = Vacancy.status_id.not_in(inactive_ids)
            if p_end:
                active_cond = and_(active_cond, or_(Vacancy.open_date <= p_end, Vacancy.open_date.is_(None)))
            status_or_conditions.append(active_cond)

            if p_start and p_end:
                status_or_conditions.append(
                    and_(
                        Vacancy.status_id.in_(inactive_ids),
                        or_(
                            and_(Vacancy.close_date >= p_start, Vacancy.close_date <= p_end),
                            and_(Vacancy.status_changed_at >= p_start, Vacancy.status_changed_at <= p_end),
                        )
                    )
                )
            elif p_start:
                status_or_conditions.append(
                    and_(
                        Vacancy.status_id.in_(inactive_ids),
                        or_(
                            Vacancy.close_date >= p_start,
                            Vacancy.status_changed_at >= p_start,
                        )
                    )
                )
            elif p_end:
                status_or_conditions.append(
                    and_(
                        Vacancy.status_id.in_(inactive_ids),
                        or_(
                            Vacancy.close_date <= p_end,
                            Vacancy.status_changed_at <= p_end,
                        )
                    )
                )
            conditions.append(or_(*status_or_conditions))
        elif p_end:
            conditions.append(or_(Vacancy.open_date <= p_end, Vacancy.open_date.is_(None)))

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
            func.coalesce(func.sum(WeeklyReport.resumes_sent), 0).label('total_resumes_sent'),
            func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0).label('total_candidates_agreed'),
            func.coalesce(func.sum(WeeklyReport.interviews_planned), 0).label('total_interviews_planned'),
            func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0).label('total_interviews_conducted'),
            func.coalesce(func.sum(WeeklyReport.offer_made), 0).label('total_offer_made'),
            func.coalesce(func.sum(WeeklyReport.offer_accepted), 0).label('total_offer_accepted'),
            func.min(WeeklyReport.created_at).label('first_report_date'),
            func.max(WeeklyReport.updated_at).label('last_updated'),
            func.min(WeeklyReport.year).label('min_year'),
            func.max(WeeklyReport.year).label('max_year'),
            func.count(WeeklyReport.id).label('report_count'),
        )
        .select_from(Vacancy)
        .outerjoin(WeeklyReport, and_(*report_join_conditions))
    )

    if conditions:
        agg_q = agg_q.where(and_(*conditions))

    agg_q = agg_q.group_by(Vacancy.id, Vacancy.vacancy_id, Vacancy.position_name)

    having_conditions = []

    search_total_resumes_sent = get_str('total_resumes_sent')
    if search_total_resumes_sent and search_total_resumes_sent.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.resumes_sent), 0) == int(search_total_resumes_sent))

    search_total_candidates_agreed = get_str('total_candidates_agreed')
    if search_total_candidates_agreed and search_total_candidates_agreed.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0) == int(search_total_candidates_agreed))

    search_total_interviews_planned = get_str('total_interviews_planned')
    if search_total_interviews_planned and search_total_interviews_planned.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.interviews_planned), 0) == int(search_total_interviews_planned))

    search_total_interviews_conducted = get_str('total_interviews_conducted')
    if search_total_interviews_conducted and search_total_interviews_conducted.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0) == int(search_total_interviews_conducted))

    search_total_offer_made = get_str('total_offer_made')
    if search_total_offer_made and search_total_offer_made.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.offer_made), 0) == int(search_total_offer_made))

    search_total_offer_accepted = get_str('total_offer_accepted')
    if search_total_offer_accepted and search_total_offer_accepted.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.offer_accepted), 0) == int(search_total_offer_accepted))

    search_report_count = get_str('report_count')
    if search_report_count and search_report_count.isdigit():
        having_conditions.append(func.count(WeeklyReport.id) == int(search_report_count))

    search_only_active_work = get_str('only_active_work') or get_str('only_with_movements')
    if search_only_active_work in ('true', '1', 'True'):
        having_conditions.append(
            (
                func.coalesce(func.sum(WeeklyReport.resumes_sent), 0) +
                func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0) +
                func.coalesce(func.sum(WeeklyReport.interviews_planned), 0) +
                func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0) +
                func.coalesce(func.sum(WeeklyReport.offer_made), 0) +
                func.coalesce(func.sum(WeeklyReport.offer_accepted), 0)
            ) > 0
        )

    if having_conditions:
        agg_q = agg_q.having(and_(*having_conditions))
    
                        
    count_subq = agg_q.subquery()
    count_q = select(func.count()).select_from(count_subq)
    total = (await db.execute(count_q)).scalar()
    print(f"DEBUG: get_all_reports total={total}")
    
                                         
                          
    num_vacancy_id = func.coalesce(
        func.cast(func.nullif(func.regexp_replace(Vacancy.vacancy_id, r'\D', '', 'g'), ''), Integer),
        Vacancy.id
    )

    SORT_MAP = {
        'vacancy_ext_id':             num_vacancy_id,
        'vacancy_name':               Vacancy.position_name,
        'open_date':                  Vacancy.open_date,
        'close_date':                 Vacancy.close_date,
        'quantity':                   Vacancy.quantity,
        'salary_gross':               Vacancy.salary_gross,
        'work_duration_days':         func.coalesce(Vacancy.close_date, func.current_date()) - Vacancy.open_date - func.coalesce(Vacancy.hold_days, 0),
        'total_resumes_sent':         func.coalesce(func.sum(WeeklyReport.resumes_sent), 0),
        'total_candidates_agreed':    func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0),
        'total_interviews_conducted': func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0),
        'total_interviews_planned':   func.coalesce(func.sum(WeeklyReport.interviews_planned), 0),
        'total_offer_made':           func.coalesce(func.sum(WeeklyReport.offer_made), 0),
        'total_offer_accepted':       func.coalesce(func.sum(WeeklyReport.offer_accepted), 0),
        'report_count':               func.count(WeeklyReport.id),
        'first_report_date':          func.min(WeeklyReport.created_at),
        'last_updated':               func.max(WeeklyReport.updated_at),
        'level_name':                 select(Dictionary.value).where(Dictionary.id == Vacancy.level_id).scalar_subquery(),
        'status_name':                select(Dictionary.value).where(Dictionary.id == Vacancy.status_id).scalar_subquery(),
        'it_role_name':               select(Dictionary.value).where(Dictionary.id == Vacancy.it_role_id).scalar_subquery(),
        'customer':                   select(Dictionary.value).where(Dictionary.id == Vacancy.admin_manager_id).scalar_subquery(),
        'team_lead_name':             Vacancy.team_lead_text,
        'project_name':               select(Dictionary.value).where(Dictionary.id == Vacancy.project_id).scalar_subquery(),
        'city_name':                  Vacancy.city_text,
        'source_name':                select(Dictionary.value).where(Dictionary.id == Vacancy.source_id).scalar_subquery(),
        'internal_transfer_name':     select(Dictionary.value).where(Dictionary.id == Vacancy.internal_transfer_id).scalar_subquery(),
        'status_changed_at':          Vacancy.status_changed_at,
        'candidate_name':             Vacancy.candidate_name,
        'comment':                    Vacancy.comment,
        'candidate_company':          Vacancy.candidate_company,
        'replacement_type_name':      select(Dictionary.value).where(Dictionary.id == Vacancy.replacement_type_id).scalar_subquery(),
        'ex_employee_name':           Vacancy.ex_employee_name,
        'unit_id':                    Vacancy.unit_id,
        'employment_type_name':       select(Dictionary.value).where(Dictionary.id == Vacancy.employment_type_id).scalar_subquery(),
        'feasibility_name':           Vacancy.feasibility_text,
        'iqhr_link':                  Vacancy.iqhr_link,
        'offer_rejection_reason':     Vacancy.offer_rejection_reason,
        'recruiter_name':             select(User.full_name).where(User.id == Vacancy.recruiter_id).scalar_subquery(),
        'co_recruiter_name':          select(User.full_name).where(User.id == Vacancy.co_recruiter_id).scalar_subquery(),
        'block_name':                 select(Dictionary.value).where(Dictionary.id == Vacancy.block_id).scalar_subquery(),
    }
    
    if sort_field:
        fields = sort_field.split(',')
        orders = sort_order.split(',') if sort_order else []
        for i, f in enumerate(fields):
            sort_col = SORT_MAP.get(f.strip())
            if sort_col is not None:
                order_dir = orders[i].strip() if i < len(orders) else 'desc'
                if order_dir == 'asc':
                    agg_q = agg_q.order_by(sort_col.asc().nulls_last())
                else:
                    agg_q = agg_q.order_by(sort_col.desc().nulls_last())
        agg_q = agg_q.order_by(Vacancy.id.desc())
    else:
        agg_q = agg_q.order_by(Vacancy.id.desc())

    agg_q = agg_q.offset(skip).limit(limit)
    
    rows = (await db.execute(agg_q)).all()
    
    vacancy_ids = [r.vacancy_db_id for r in rows]
    _VAC_OPTS = [
        selectinload(Vacancy.recruiter),
        selectinload(Vacancy.co_recruiter),
        selectinload(Vacancy.project),
        selectinload(Vacancy.admin_manager),
        selectinload(Vacancy.team_lead),
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
            # customer — только admin_manager (без fallback к project)
            "customer": v.admin_manager.value if v and v.admin_manager else None,
            "admin_manager_name": v.admin_manager.value if v and v.admin_manager else None,
            "team_lead_name": (v.team_lead.value if v.team_lead else (v.team_lead_text or None)) if v else None,
            "recruiter_name": v.recruiter.full_name if v and v.recruiter else None,
            "co_recruiter_name": v.co_recruiter.full_name if v and v.co_recruiter else None,
            "co_recruiter_id": v.co_recruiter_id if v else None,
            "project_name": v.project.value if v and v.project else None,
            "city_name": v.city.value if v and v.city else (v.city_text if v else None),
            "source_name": v.source.value if v and v.source else None,
            "internal_transfer_name": v.internal_transfer.value if v and v.internal_transfer else None,
            "status_changed_at": v.status_changed_at.isoformat() if v and v.status_changed_at else None,
            "candidate_name": v.candidate_name if v else None,
            "comment": v.comment if v else None,
            "candidate_company": v.candidate_company if v else None,
            "replacement_type_name": v.replacement_type.value if v and v.replacement_type else None,
            "ex_employee_name": v.ex_employee_name if v else None,
            "unit_id": v.unit_id if v else None,
            "employment_type_name": v.employment_type.value if v and v.employment_type else None,
            "feasibility_name": (v.feasibility_text or (v.feasibility.value if v.feasibility else None)) if v else None,
            "iqhr_link": v.iqhr_link if v else None,
            "offer_rejection_reason": v.offer_rejection_reason if v else None,
            "block_name": v.block.value if v and v.block else None,
            "work_duration_days": v.work_duration_days if v else None,
            "salary_gross": v.salary_gross if v else None,
            "year": f"{r.min_year}" if r.min_year == r.max_year else f"{r.min_year}-{r.max_year}",
            "total_resumes_sent": r.total_resumes_sent or 0,
            "total_candidates_agreed": r.total_candidates_agreed or 0,
            "total_interviews_planned": r.total_interviews_planned or 0,
            "total_interviews_conducted": r.total_interviews_conducted or 0,
            "total_offer_made": r.total_offer_made or 0,
            "total_offer_accepted": r.total_offer_accepted or 0,
            "first_report_date": r.first_report_date.isoformat() if r.first_report_date else None,
            "last_updated": r.last_updated.isoformat() if r.last_updated else (
                r.first_report_date.isoformat() if r.first_report_date else None
            ),
            "report_count": r.report_count,
        })

    return {"items": items, "total": total}

@router.get("/all/export")
async def export_all_reports(
    request: Request,
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
    from services.vacancy_filter import apply_vacancy_filters
    qp = request.query_params
    
    def get_list(key: str):
        vals = qp.getlist(key)
        if not vals:
            return None
        res = []
        for v in vals:
            if v.lstrip('-').isdigit():
                res.append(int(v))
        return res if res else None
        
    def get_str(key: str):
        v = qp.get(key)
        return v if v else None
        
    rec_vals = qp.getlist('recruiter_name')
    rec_ids = [int(v) for v in rec_vals if v.lstrip('-').isdigit()] or None
    rec_str = next((v for v in rec_vals if not v.lstrip('-').isdigit() and v.strip()), None) or get_str('search_recruiter')

    co_rec_vals = qp.getlist('co_recruiter_name')
    co_rec_ids = [int(v) for v in co_rec_vals if v.lstrip('-').isdigit()] or None
    co_rec_str = next((v for v in co_rec_vals if not v.lstrip('-').isdigit() and v.strip()), None) or get_str('search_co_recruiter')

    _, vacancy_conditions = apply_vacancy_filters(
        query=select(Vacancy),
        current_user=current_user,
        status_id=get_list('status_name') or get_list('status_id'),
        level_id=get_list('level_name') or get_list('level_id'),
        it_role_id=get_list('it_role_name') or get_list('it_role_id'),
        project_id=get_list('project_name') or get_list('project_id'),
        admin_manager_id=get_list('customer') or get_list('admin_manager_id'),
        source_id=get_list('source_name') or get_list('source_id'),
        block_id=get_list('block_name') or get_list('block_id'),
        employment_type_id=get_list('employment_type_name') or get_list('employment_type_id'),
        search_feasibility_text=get_str('feasibility_name') or get_str('feasibility_text'),
        replacement_type_id=get_list('replacement_type_name') or get_list('replacement_type_id'),
        internal_transfer_id=get_list('internal_transfer_name') or get_list('internal_transfer_id'),
        recruiter_id=rec_ids,
        co_recruiter_id=co_rec_ids,
        search_recruiter=rec_str,
        search_co_recruiter=co_rec_str,
        
        search_vacancy_id=get_str('vacancy_ext_id'),
        search_position_name=get_str('vacancy_name'),
        search_candidate_name=get_str('candidate_name'),
        search_team_lead_text=get_str('team_lead_name'),
        search_city_text=get_str('city_name'),
        search_candidate_company=get_str('candidate_company'),
        search_ex_employee_name=get_str('ex_employee_name'),
        search_unit_id=get_str('unit_id'),
        search_iqhr_link=get_str('iqhr_link'),
        search_comment=get_str('comment'),
        search_offer_rejection_reason=get_str('offer_rejection_reason'),
        search_quantity=get_str('quantity'),
        search_salary_gross=get_str('salary_gross'),
        search_work_duration_days=get_str('work_duration_days'),
        search_open_date=get_str('open_date') or get_str('search_open_date'),
        search_open_date_from=get_str('open_date_from') or get_str('search_open_date_from'),
        search_open_date_to=get_str('open_date_to') or get_str('search_open_date_to'),
        search_close_date=get_str('close_date') or get_str('search_close_date'),
        search_close_date_from=get_str('close_date_from') or get_str('search_close_date_from'),
        search_close_date_to=get_str('close_date_to') or get_str('search_close_date_to'),
        search_status_changed_at=get_str('status_changed_at') or get_str('search_status_changed_at'),
        search_status_changed_at_from=get_str('status_changed_at_from') or get_str('search_status_changed_at_from'),
        search_status_changed_at_to=get_str('status_changed_at_to') or get_str('search_status_changed_at_to'),
    )
    conditions.extend(vacancy_conditions)
                                                                
    if current_user.role == UserRole.RECRUITER:
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
                Vacancy.co_recruiter_id == current_user.id,
                Vacancy.id.in_(delegated_subq),
            )
        )
    p_start = None
    p_end = None

    if week_number is not None:
        y = year if year is not None else datetime.now().year
        p_start = _get_week_start(y, week_number)
        p_end = _get_week_end(y, week_number)
    elif month is not None:
        y = year if year is not None else datetime.now().year
        month_start = date(y, month, 1)
        if month == 12:
            month_end = date(y + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(y, month + 1, 1) - timedelta(days=1)
        p_start = month_start
        p_end = month_end
    elif year is not None:
        p_start = date(year, 1, 1)
        p_end = date(year, 12, 31)

    sd_str = start_date or date_from
    ed_str = end_date or date_to
    if isinstance(sd_str, str):
        try:
            sd_d = date.fromisoformat(sd_str)
            p_start = max(p_start, sd_d) if p_start else sd_d
        except (ValueError, TypeError):
            pass
    if isinstance(ed_str, str):
        try:
            ed_d = date.fromisoformat(ed_str)
            p_end = min(p_end, ed_d) if p_end else ed_d
        except (ValueError, TypeError):
            pass

    report_join_conditions = [WeeklyReport.vacancy_id == Vacancy.id]
    if week_number is not None:
        y = year if year is not None else datetime.now().year
        report_join_conditions.append(WeeklyReport.week_number == week_number)
        report_join_conditions.append(WeeklyReport.year == y)
    elif p_start and p_end:
        report_join_conditions.append(WeeklyReport.week_start >= p_start)
        report_join_conditions.append(WeeklyReport.week_start <= p_end)
    elif p_start:
        report_join_conditions.append(WeeklyReport.week_start >= p_start)
    elif p_end:
        report_join_conditions.append(WeeklyReport.week_start <= p_end)

    explicit_status = get_list('status_name')
    if not explicit_status:
        inactive_ids = await _get_inactive_status_ids(db)
        if inactive_ids and (p_start or p_end):
            status_or_conditions = []
            active_cond = Vacancy.status_id.not_in(inactive_ids)
            if p_end:
                active_cond = and_(active_cond, or_(Vacancy.open_date <= p_end, Vacancy.open_date.is_(None)))
            status_or_conditions.append(active_cond)

            if p_start and p_end:
                status_or_conditions.append(
                    and_(
                        Vacancy.status_id.in_(inactive_ids),
                        or_(
                            and_(Vacancy.close_date >= p_start, Vacancy.close_date <= p_end),
                            and_(Vacancy.status_changed_at >= p_start, Vacancy.status_changed_at <= p_end),
                        )
                    )
                )
            elif p_start:
                status_or_conditions.append(
                    and_(
                        Vacancy.status_id.in_(inactive_ids),
                        or_(
                            Vacancy.close_date >= p_start,
                            Vacancy.status_changed_at >= p_start,
                        )
                    )
                )
            elif p_end:
                status_or_conditions.append(
                    and_(
                        Vacancy.status_id.in_(inactive_ids),
                        or_(
                            Vacancy.close_date <= p_end,
                            Vacancy.status_changed_at <= p_end,
                        )
                    )
                )
            conditions.append(or_(*status_or_conditions))
        elif p_end:
            conditions.append(or_(Vacancy.open_date <= p_end, Vacancy.open_date.is_(None)))

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
            func.coalesce(func.sum(WeeklyReport.resumes_sent), 0).label('total_resumes_sent'),
            func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0).label('total_candidates_agreed'),
            func.coalesce(func.sum(WeeklyReport.interviews_planned), 0).label('total_interviews_planned'),
            func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0).label('total_interviews_conducted'),
            func.coalesce(func.sum(WeeklyReport.offer_made), 0).label('total_offer_made'),
            func.coalesce(func.sum(WeeklyReport.offer_accepted), 0).label('total_offer_accepted'),
            func.min(WeeklyReport.created_at).label('first_report_date'),
            func.max(WeeklyReport.updated_at).label('last_updated'),
            func.min(WeeklyReport.year).label('min_year'),
            func.max(WeeklyReport.year).label('max_year'),
            func.count(WeeklyReport.id).label('report_count'),
        )
        .select_from(Vacancy)
        .outerjoin(WeeklyReport, and_(*report_join_conditions))
    )
    if conditions:
        agg_q = agg_q.where(and_(*conditions))
    agg_q = agg_q.group_by(Vacancy.id, Vacancy.vacancy_id, Vacancy.position_name)

    having_conditions = []
    search_total_resumes_sent = get_str('total_resumes_sent')
    if search_total_resumes_sent and search_total_resumes_sent.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.resumes_sent), 0) == int(search_total_resumes_sent))

    search_total_candidates_agreed = get_str('total_candidates_agreed')
    if search_total_candidates_agreed and search_total_candidates_agreed.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0) == int(search_total_candidates_agreed))

    search_total_interviews_planned = get_str('total_interviews_planned')
    if search_total_interviews_planned and search_total_interviews_planned.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.interviews_planned), 0) == int(search_total_interviews_planned))

    search_total_interviews_conducted = get_str('total_interviews_conducted')
    if search_total_interviews_conducted and search_total_interviews_conducted.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0) == int(search_total_interviews_conducted))

    search_total_offer_made = get_str('total_offer_made')
    if search_total_offer_made and search_total_offer_made.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.offer_made), 0) == int(search_total_offer_made))

    search_total_offer_accepted = get_str('total_offer_accepted')
    if search_total_offer_accepted and search_total_offer_accepted.isdigit():
        having_conditions.append(func.coalesce(func.sum(WeeklyReport.offer_accepted), 0) == int(search_total_offer_accepted))

    search_report_count = get_str('report_count')
    if search_report_count and search_report_count.isdigit():
        having_conditions.append(func.count(WeeklyReport.id) == int(search_report_count))

    search_only_active_work = get_str('only_active_work') or get_str('only_with_movements')
    if search_only_active_work in ('true', '1', 'True'):
        having_conditions.append(
            (
                func.coalesce(func.sum(WeeklyReport.resumes_sent), 0) +
                func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0) +
                func.coalesce(func.sum(WeeklyReport.interviews_planned), 0) +
                func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0) +
                func.coalesce(func.sum(WeeklyReport.offer_made), 0) +
                func.coalesce(func.sum(WeeklyReport.offer_accepted), 0)
            ) > 0
        )

    if having_conditions:
        agg_q = agg_q.having(and_(*having_conditions))

    num_vacancy_id_exp = func.coalesce(
        func.cast(func.nullif(func.regexp_replace(Vacancy.vacancy_id, r'\D', '', 'g'), ''), Integer),
        Vacancy.id
    )

    SORT_MAP_EXP = {
        'vacancy_ext_id':             num_vacancy_id_exp,
        'vacancy_name':               Vacancy.position_name,
        'open_date':                  Vacancy.open_date,
        'close_date':                 Vacancy.close_date,
        'quantity':                   Vacancy.quantity,
        'salary_gross':               Vacancy.salary_gross,
        'work_duration_days':         func.coalesce(Vacancy.close_date, func.current_date()) - Vacancy.open_date - func.coalesce(Vacancy.hold_days, 0),
        'total_resumes_sent':         func.coalesce(func.sum(WeeklyReport.resumes_sent), 0),
        'total_candidates_agreed':    func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0),
        'total_interviews_conducted': func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0),
        'total_interviews_planned':   func.coalesce(func.sum(WeeklyReport.interviews_planned), 0),
        'total_offer_made':           func.coalesce(func.sum(WeeklyReport.offer_made), 0),
        'total_offer_accepted':       func.coalesce(func.sum(WeeklyReport.offer_accepted), 0),
        'report_count':               func.count(WeeklyReport.id),
        'first_report_date':          func.min(WeeklyReport.created_at),
        'last_updated':               func.max(WeeklyReport.updated_at),
        'level_name':                 select(Dictionary.value).where(Dictionary.id == Vacancy.level_id).scalar_subquery(),
        'status_name':                select(Dictionary.value).where(Dictionary.id == Vacancy.status_id).scalar_subquery(),
        'it_role_name':               select(Dictionary.value).where(Dictionary.id == Vacancy.it_role_id).scalar_subquery(),
        'customer':                   select(Dictionary.value).where(Dictionary.id == Vacancy.admin_manager_id).scalar_subquery(),
        'team_lead_name':             Vacancy.team_lead_text,
        'project_name':               select(Dictionary.value).where(Dictionary.id == Vacancy.project_id).scalar_subquery(),
        'city_name':                  Vacancy.city_text,
        'source_name':                select(Dictionary.value).where(Dictionary.id == Vacancy.source_id).scalar_subquery(),
        'internal_transfer_name':     select(Dictionary.value).where(Dictionary.id == Vacancy.internal_transfer_id).scalar_subquery(),
        'status_changed_at':          Vacancy.status_changed_at,
        'candidate_name':             Vacancy.candidate_name,
        'comment':                    Vacancy.comment,
        'candidate_company':          Vacancy.candidate_company,
        'replacement_type_name':      select(Dictionary.value).where(Dictionary.id == Vacancy.replacement_type_id).scalar_subquery(),
        'ex_employee_name':           Vacancy.ex_employee_name,
        'unit_id':                    Vacancy.unit_id,
        'employment_type_name':       select(Dictionary.value).where(Dictionary.id == Vacancy.employment_type_id).scalar_subquery(),
        'feasibility_name':           Vacancy.feasibility_text,
        'iqhr_link':                  Vacancy.iqhr_link,
        'offer_rejection_reason':     Vacancy.offer_rejection_reason,
        'recruiter_name':             select(User.full_name).where(User.id == Vacancy.recruiter_id).scalar_subquery(),
        'co_recruiter_name':          select(User.full_name).where(User.id == Vacancy.co_recruiter_id).scalar_subquery(),
        'block_name':                 select(Dictionary.value).where(Dictionary.id == Vacancy.block_id).scalar_subquery(),
    }
    if sort_field:
        fields = sort_field.split(',')
        orders = sort_order.split(',') if sort_order else []
        for i, f in enumerate(fields):
            sort_col = SORT_MAP_EXP.get(f.strip())
            if sort_col is not None:
                order_dir = orders[i].strip() if i < len(orders) else 'desc'
                if order_dir == 'asc':
                    agg_q = agg_q.order_by(sort_col.asc().nulls_last())
                else:
                    agg_q = agg_q.order_by(sort_col.desc().nulls_last())
        agg_q = agg_q.order_by(Vacancy.id.desc())
    else:
        agg_q = agg_q.order_by(Vacancy.id.desc())

    rows = (await db.execute(agg_q)).all()

    _VAC_OPTS_EXPORT = [
        selectinload(Vacancy.recruiter),
        selectinload(Vacancy.co_recruiter),
        selectinload(Vacancy.project),
        selectinload(Vacancy.admin_manager),
        selectinload(Vacancy.team_lead),
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
            "Количество": v.quantity if v else "",
            "Уровень специалиста": v.level.value if v and v.level else "",
            "Вакансия": r.vacancy_name or "",
            "Статус вакансии": v.status.value if v and v.status else "",
            "ИТ роль": v.it_role.value if v and v.it_role else "",
            "Адм. руководитель": v.admin_manager.value if v and v.admin_manager else "",
            "Тимлид": (v.team_lead.value if v.team_lead else (v.team_lead_text or "")) if v else "",
            "Проект": v.project.value if v and v.project else "",
            "Передано заказчику": r.total_resumes_sent or 0,
            "Резюме одобрено": r.total_candidates_agreed or 0,
            "Собеседования факт": r.total_interviews_conducted or 0,
            "Собеседования план": r.total_interviews_planned or 0,
            "Оффер сделан": r.total_offer_made or 0,
            "Оффер принят": r.total_offer_accepted or 0,
            "Причина отказа от Оффера": v.offer_rejection_reason or "" if v else "",
            "Город": (v.city.value if v and v.city else (v.city_text or "")) if v else "",
            "Источник найма": v.source.value if v and v.source else "",
            "Внутренний перевод": v.internal_transfer.value if v and v.internal_transfer else "",
            "Дата изм. статуса": str(v.status_changed_at) if v and v.status_changed_at else "",
            "Дата закрытия": str(v.close_date) if v and v.close_date else "",
            "ФИО кандидата": v.candidate_name or "" if v else "",
            "Комментарий": v.comment or "" if v else "",
            "Компания кандидата": v.candidate_company or "" if v else "",
            "Новая / Замена": v.replacement_type.value if v and v.replacement_type else "",
            "ФИО бывшего сотр.": v.ex_employee_name or "" if v else "",
            "ID ШЕ": v.unit_id or "" if v else "",
            "Вид занятости": v.employment_type.value if v and v.employment_type else "",
            "ТЭО проекта": (v.feasibility_text or (v.feasibility.value if v.feasibility else "")) if v else "",
            "Ссылка IQHR": (v.iqhr_link or "") if v else "",
            "Рекрутер": v.recruiter.full_name if v and v.recruiter else "",
            "Доп. рекрутер": v.co_recruiter.full_name if v and v.co_recruiter else "",
            "Блок": v.block.value if v and v.block else "",
            "Срок работы (дней)": v.work_duration_days if v and v.work_duration_days is not None else "",
            "Зарплата кандидатов Gross": v.salary_gross or "" if v else "",
            "Год": f"{r.min_year}" if r.min_year == r.max_year else (f"{r.min_year}-{r.max_year}" if r.min_year and r.max_year else ""),
            "Кол-во отчётов": r.report_count or 0,
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
    return Response(
        content=output.getvalue(),
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
    
    if current_user.role == UserRole.RECRUITER and report.vacancy.recruiter_id != current_user.id and report.vacancy.co_recruiter_id != current_user.id:
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

    if current_user.role == UserRole.RECRUITER:
        if not is_week_editable_for_recruiter(report.week_number, report.year):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Рекрутер может редактировать отчеты только за текущую и предыдущую недели"
            )
        if report.vacancy.recruiter_id != current_user.id and report.vacancy.co_recruiter_id != current_user.id:
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
        "offer_accepted":       report.offer_accepted,
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
            "offer_accepted":       report.offer_accepted,
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
        await FastAPICache.clear(namespace="dashboards")
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
    
    if current_user.role == UserRole.RECRUITER:
        if not is_week_editable_for_recruiter(report.week_number, report.year):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Рекрутер может удалять отчеты только за текущую и предыдущую недели"
            )
        if report.vacancy.recruiter_id != current_user.id and report.vacancy.co_recruiter_id != current_user.id:
            delegation_svc = DelegationService(db)
            if not await delegation_svc.has_delegated_access(report.vacancy.id, current_user.id):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому отчету")
    
    from fastapi_cache import FastAPICache
    db.delete(report)
    await db.commit()
    await FastAPICache.clear(namespace="dashboards")
    return None