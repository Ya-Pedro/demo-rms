\
\
\
\
\
\
   
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case, Integer, cast, String
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
from services.vacancy_filter import apply_vacancy_filters, _is_empty_kw, _empty_text_cond
from services.repositories.vacancy_repository import order_expr
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
    
                         
    # Existing report check
    existing_q = select(WeeklyReport).where(
        WeeklyReport.vacancy_id == report_data.vacancy_id,
        WeeklyReport.week_number == report_data.week_number,
        WeeklyReport.year == report_data.year,
    )
    if current_user.role == UserRole.RECRUITER:
        existing_q = existing_q.where(
            or_(
                WeeklyReport.user_id == current_user.id,
                and_(WeeklyReport.user_id.is_(None), vacancy.recruiter_id == current_user.id),
            )
        )
    existing = await db.execute(existing_q)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Отчет за неделю {report_data.week_number} уже существует. Используйте редактирование."
        )
    
    week_start = _get_week_start(report_data.year, report_data.week_number)
    
    report_dict = report_data.model_dump()
    report_dict['week_start'] = week_start
    report_dict['report_date'] = datetime.now()
    report_dict['user_id'] = current_user.id
    
    new_report = WeeklyReport(**report_dict)
    db.add(new_report)

    # If offer_rejection_reason or comment provided, update vacancy-level as well
    if getattr(report_data, 'offer_rejection_reason', None):
        vacancy.offer_rejection_reason = report_data.offer_rejection_reason
    if getattr(report_data, 'comment', None):
        vacancy.comment = report_data.comment

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
            offer_rejection_reason=getattr(report_data, 'offer_rejection_reason', None),
            comment=getattr(report_data, 'comment', None),
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

_REPORT_VACANCY_LOAD_OPTIONS = [
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


def _apply_reports_sorting(agg_q, sort_field: Optional[str], sort_order: Optional[str], dialect_name: str = "postgresql"):
    """Единая сортировка сводного отчёта для таблицы и Excel-экспорта."""
    if not sort_field:
        return agg_q.order_by(Vacancy.id.desc())

    def _dict_val(fk_col):
        return select(Dictionary.value).where(Dictionary.id == fk_col).scalar_subquery()

    def _user_val(fk_col):
        return select(User.full_name).where(User.id == fk_col).scalar_subquery()

    def _hybrid_expr(primary_col, secondary_col):
        return func.coalesce(func.nullif(func.trim(primary_col), ""), func.nullif(func.trim(secondary_col), ""))

    # (expr, mode): mode in ('text', 'raw', 'zero', 'vid', 'year')
    sort_specs = {
        'vacancy_ext_id':             (Vacancy.vacancy_id, 'vid'),
        'vacancy_name':               (Vacancy.position_name, 'text'),
        'open_date':                  (Vacancy.open_date, 'raw'),
        'close_date':                 (Vacancy.close_date, 'raw'),
        'quantity':                   (Vacancy.quantity, 'raw'),
        'salary_gross':               (Vacancy.salary_gross, 'raw'),
        'work_duration_days':         (func.coalesce(Vacancy.close_date, func.current_date()) - Vacancy.open_date - func.coalesce(Vacancy.hold_days, 0), 'raw'),
        'total_resumes_sent':         (func.coalesce(func.sum(WeeklyReport.resumes_sent), 0), 'zero'),
        'total_candidates_agreed':    (func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0), 'zero'),
        'total_interviews_conducted': (func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0), 'zero'),
        'total_interviews_planned':   (func.coalesce(func.sum(WeeklyReport.interviews_planned), 0), 'zero'),
        'total_offer_made':           (func.coalesce(func.sum(WeeklyReport.offer_made), 0), 'zero'),
        'total_offer_accepted':       (func.coalesce(func.sum(WeeklyReport.offer_accepted), 0), 'zero'),
        'report_count':               (func.count(WeeklyReport.id), 'zero'),
        'year':                       (func.min(WeeklyReport.year), 'year'),
        'first_report_date':          (func.min(WeeklyReport.created_at), 'raw'),
        'last_updated':               (func.coalesce(func.max(WeeklyReport.updated_at), func.min(WeeklyReport.created_at)), 'raw'),
        'level_name':                 (_dict_val(Vacancy.level_id), 'text'),
        'status_name':                (_dict_val(Vacancy.status_id), 'text'),
        'it_role_name':               (_dict_val(Vacancy.it_role_id), 'text'),
        'customer':                   (_dict_val(Vacancy.admin_manager_id), 'text'),
        'team_lead_name':             (_hybrid_expr(_dict_val(Vacancy.team_lead_id), Vacancy.team_lead_text), 'text'),
        'project_name':               (_dict_val(Vacancy.project_id), 'text'),
        'city_name':                  (_hybrid_expr(_dict_val(Vacancy.city_id), Vacancy.city_text), 'text'),
        'source_name':                (_dict_val(Vacancy.source_id), 'text'),
        'internal_transfer_name':     (_dict_val(Vacancy.internal_transfer_id), 'text'),
        'recommender_name':           (Vacancy.recommender_name, 'text'),
        'status_changed_at':          (Vacancy.status_changed_at, 'raw'),
        'candidate_name':             (Vacancy.candidate_name, 'text'),
        'comment':                    (Vacancy.comment, 'text'),
        'candidate_company':          (Vacancy.candidate_company, 'text'),
        'replacement_type_name':      (_dict_val(Vacancy.replacement_type_id), 'text'),
        'ex_employee_name':           (Vacancy.ex_employee_name, 'text'),
        'unit_id':                    (Vacancy.unit_id, 'text'),
        'employment_type_name':       (_dict_val(Vacancy.employment_type_id), 'text'),
        'feasibility_name':           (_hybrid_expr(Vacancy.feasibility_text, _dict_val(Vacancy.feasibility_id)), 'text'),
        'iqhr_link':                  (Vacancy.iqhr_link, 'text'),
        'offer_rejection_reason':     (Vacancy.offer_rejection_reason, 'text'),
        'recruiter_name':             (_user_val(Vacancy.recruiter_id), 'text'),
        'co_recruiter_name':          (_user_val(Vacancy.co_recruiter_id), 'text'),
        'block_name':                 (_dict_val(Vacancy.block_id), 'text'),
    }

    fields = sort_field.split(',')
    orders = sort_order.split(',') if sort_order else []
    for i, f in enumerate(fields):
        spec = sort_specs.get(f.strip())
        if not spec:
            continue
        expr, mode = spec
        order_dir = orders[i].strip().lower() if i < len(orders) else 'desc'
        if order_dir not in ('asc', 'desc'):
            order_dir = 'desc'

        if mode == 'vid':
            clean_vid = func.nullif(func.trim(expr), '')
            has_val = case((clean_vid.is_(None), None), else_=1)
            agg_q = agg_q.order_by(order_expr(has_val, order_dir))
            if dialect_name == 'postgresql':
                num_expr = func.cast(
                    func.nullif(func.regexp_replace(clean_vid, r'\D', '', 'g'), ''),
                    Integer,
                )
                agg_q = agg_q.order_by(order_expr(num_expr, order_dir))
            agg_q = agg_q.order_by(order_expr(clean_vid, order_dir, is_text=True))
        elif mode == 'year':
            agg_q = agg_q.order_by(
                order_expr(func.min(WeeklyReport.year), order_dir),
                order_expr(func.max(WeeklyReport.year), order_dir),
            )
        elif mode == 'zero':
            agg_q = agg_q.order_by(expr.asc() if order_dir == 'asc' else expr.desc())
        elif mode == 'text':
            agg_q = agg_q.order_by(order_expr(expr, order_dir, is_text=True))
        else:
            agg_q = agg_q.order_by(order_expr(expr, order_dir, is_text=False))

    return agg_q.order_by(Vacancy.id.desc())


async def _build_reports_agg_query(
    db: AsyncSession,
    request: Request,
    current_user: User,
    *,
    year: Optional[int] = None,
    week_number: Optional[int] = None,
    month: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    recruiter_id: Optional[List[int]] = None,
    project_id: Optional[List[int]] = None,
    vacancy_search: Optional[str] = None,
    search_vacancy_id: Optional[str] = None,
    search_vacancy_name: Optional[str] = None,
    search_recruiter: Optional[str] = None,
    search_candidate: Optional[str] = None,
):
    conditions = []
    qp = request.query_params

    def get_list(key: str):
        vals = qp.getlist(key)
        if not vals:
            return None
        res = [int(v) for v in vals if v.lstrip('-').isdigit()]
        return res if res else None

    def get_str(key: str):
        v = qp.get(key)
        return v if v else None

    rec_vals = qp.getlist('recruiter_name')
    rec_ids = [int(v) for v in rec_vals if v.lstrip('-').isdigit()] or None
    rec_str = next((v for v in rec_vals if not v.lstrip('-').isdigit() and v.strip()), None) or get_str('search_recruiter') or search_recruiter

    co_rec_vals = qp.getlist('co_recruiter_name')
    co_rec_ids = [int(v) for v in co_rec_vals if v.lstrip('-').isdigit()] or None
    co_rec_str = next((v for v in co_rec_vals if not v.lstrip('-').isdigit() and v.strip()), None) or get_str('search_co_recruiter')

    rej_vals = qp.getlist('offer_rejection_reason') or None

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
        search_recommender_name=get_str('recommender_name') or get_str('search_recommender_name'),
        search_team_lead_text=get_str('team_lead_name'),
        search_city_text=get_str('city_name'),
        search_candidate_company=get_str('candidate_company'),
        search_ex_employee_name=get_str('ex_employee_name'),
        search_unit_id=get_str('unit_id'),
        search_iqhr_link=get_str('iqhr_link'),
        search_comment=get_str('comment'),
        offer_rejection_reason=rej_vals,
        search_offer_rejection_reason=get_str('search_offer_rejection_reason'),
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
        p_start = date(y, month, 1)
        p_end = date(y + 1, 1, 1) - timedelta(days=1) if month == 12 else date(y, month + 1, 1) - timedelta(days=1)
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

    eff_search_vid = search_vacancy_id or get_str('search_vacancy_id')
    if eff_search_vid:
        s_vid = str(eff_search_vid).strip()
        if _is_empty_kw(s_vid):
            conditions.append(_empty_text_cond(Vacancy.vacancy_id))
        elif "," in s_vid:
            ids = [x.strip() for x in s_vid.split(",") if x.strip()]
            conditions.append(or_(
                Vacancy.vacancy_id.in_(ids),
                and_(Vacancy.vacancy_id.is_(None), cast(Vacancy.id, String).in_(ids)),
            ))
        else:
            conditions.append(or_(
                Vacancy.vacancy_id.ilike(s_vid),
                and_(Vacancy.vacancy_id.is_(None), cast(Vacancy.id, String) == s_vid),
            ))

    eff_search_vname = search_vacancy_name or get_str('search_vacancy_name')
    if eff_search_vname:
        conditions.append(Vacancy.position_name.ilike(f"%{eff_search_vname}%"))

    eff_search_cand = search_candidate or get_str('search_candidate')
    if eff_search_cand:
        conditions.append(Vacancy.candidate_name.ilike(f"%{eff_search_cand}%"))

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

    having_specs = [
        ('total_resumes_sent',         func.coalesce(func.sum(WeeklyReport.resumes_sent), 0)),
        ('total_candidates_agreed',    func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0)),
        ('total_interviews_planned',   func.coalesce(func.sum(WeeklyReport.interviews_planned), 0)),
        ('total_interviews_conducted', func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0)),
        ('total_offer_made',           func.coalesce(func.sum(WeeklyReport.offer_made), 0)),
        ('total_offer_accepted',       func.coalesce(func.sum(WeeklyReport.offer_accepted), 0)),
        ('report_count',               func.count(WeeklyReport.id)),
    ]
    having_conditions = []
    for hkey, hexpr in having_specs:
        hval = get_str(hkey)
        if not hval:
            continue
        if _is_empty_kw(hval):
            having_conditions.append(hexpr == 0)
        elif hval.isdigit():
            having_conditions.append(hexpr == int(hval))

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

    return agg_q


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
       
                                                
    agg_q = await _build_reports_agg_query(
        db=db,
        request=request,
        current_user=current_user,
        year=year,
        week_number=week_number,
        month=month,
        start_date=start_date,
        end_date=end_date,
        date_from=date_from,
        date_to=date_to,
        recruiter_id=recruiter_id,
        project_id=project_id,
        vacancy_search=vacancy_search,
        search_vacancy_id=search_vacancy_id,
        search_vacancy_name=search_vacancy_name,
        search_recruiter=search_recruiter,
        search_candidate=search_candidate,
    )

    count_subq = agg_q.subquery()
    count_q = select(func.count()).select_from(count_subq)
    total = (await db.execute(count_q)).scalar()

    dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
    dialect_str = dialect_name.name if dialect_name else "postgresql"
    agg_q = _apply_reports_sorting(agg_q, sort_field=sort_field, sort_order=sort_order, dialect_name=dialect_str)
    agg_q = agg_q.offset(skip).limit(limit)

    rows = (await db.execute(agg_q)).all()

    vacancy_ids = [r.vacancy_db_id for r in rows]
    if vacancy_ids:
        vac_q = (
            select(Vacancy)
            .options(*_REPORT_VACANCY_LOAD_OPTIONS)
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
            "recommender_name": v.recommender_name if v else None,
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
    search_vacancy_id: Optional[str] = Query(None),
    search_vacancy_name: Optional[str] = Query(None),
    search_candidate: Optional[str] = Query(None),
):
    agg_q = await _build_reports_agg_query(
        db=db,
        request=request,
        current_user=current_user,
        year=year,
        week_number=week_number,
        month=month,
        start_date=start_date,
        end_date=end_date,
        date_from=date_from,
        date_to=date_to,
        recruiter_id=recruiter_id,
        project_id=project_id,
        vacancy_search=vacancy_search,
        search_vacancy_id=search_vacancy_id,
        search_vacancy_name=search_vacancy_name,
        search_candidate=search_candidate,
    )

    dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
    dialect_str = dialect_name.name if dialect_name else "postgresql"
    agg_q = _apply_reports_sorting(agg_q, sort_field=sort_field, sort_order=sort_order, dialect_name=dialect_str)

    rows = (await db.execute(agg_q)).all()

    vacancy_ids = [r.vacancy_db_id for r in rows]
    vac_map = {}
    if vacancy_ids:
        vac_q = (
            select(Vacancy)
            .options(*_REPORT_VACANCY_LOAD_OPTIONS)
            .where(Vacancy.id.in_(vacancy_ids))
        )
        vac_result = await db.execute(vac_q)
        vac_map = {v.id: v for v in vac_result.scalars().all()}

    excel_rows = []
    for r in rows:
        v = vac_map.get(r.vacancy_db_id)
        excel_rows.append({
            "ID вакансии": r.vacancy_ext_id or "",
            "Дата открытия": v.open_date.strftime("%d.%m.%Y") if v and v.open_date else "",
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
            "ФИО рекомендателя": v.recommender_name or "" if v else "",
            "Дата изм. статуса": v.status_changed_at.strftime("%d.%m.%Y") if v and v.status_changed_at else "",
            "Дата закрытия": v.close_date.strftime("%d.%m.%Y") if v and v.close_date else "",
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

    _old_reason = report.offer_rejection_reason
    _old_comment = report.comment

    if report.user_id is None:
        report.user_id = current_user.id

    for field, value in update_data.items():
        setattr(report, field, value)

    # If offer_rejection_reason or comment was updated, reflect on vacancy level as well
    if "offer_rejection_reason" in update_data and report.vacancy:
        report.vacancy.offer_rejection_reason = report.offer_rejection_reason
    if "comment" in update_data and report.vacancy:
        report.vacancy.comment = report.comment

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
            old_offer_rejection_reason=_old_reason,
            new_offer_rejection_reason=report.offer_rejection_reason,
            old_comment=_old_comment,
            new_comment=report.comment,
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
    await db.delete(report)
    await db.commit()
    await FastAPICache.clear(namespace="dashboards")
    return None