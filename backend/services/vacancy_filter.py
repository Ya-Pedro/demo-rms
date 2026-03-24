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
   
from __future__ import annotations

from datetime import date, datetime, timezone
import os

def _today() -> date:
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(os.environ.get("APP_TIMEZONE", "Europe/Moscow"))
        return datetime.now(tz).date()
    except Exception:
        from datetime import timedelta
        return (datetime.now(timezone.utc) + timedelta(hours=3)).date()
from typing import List, Optional

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Query

from models import Vacancy, UserRole, User, VacancyDelegation

                                                                                
                      
                                                                                

def apply_vacancy_filters(
    query,
    current_user: User,
    *,
                                               
    status_id: Optional[List[int]] = None,
    level_id: Optional[List[int]] = None,
    it_role_id: Optional[List[int]] = None,
    project_id: Optional[List[int]] = None,
    admin_manager_id: Optional[List[int]] = None,
    team_lead_id: Optional[List[int]] = None,
    city_id: Optional[List[int]] = None,
    source_id: Optional[List[int]] = None,
    block_id: Optional[List[int]] = None,
    employment_type_id: Optional[List[int]] = None,
    feasibility_id: Optional[List[int]] = None,
    replacement_type_id: Optional[List[int]] = None,
    internal_transfer_id: Optional[List[int]] = None,
    recruiter_id: Optional[List[int]] = None,
                                
    search: Optional[str] = None,
    search_vacancy_id: Optional[str] = None,
    search_position_name: Optional[str] = None,
    search_candidate_name: Optional[str] = None,
    search_candidate_company: Optional[str] = None,
    search_ex_employee_name: Optional[str] = None,
    search_unit_id: Optional[str] = None,
    search_iqhr_link: Optional[str] = None,
    search_salary_gross: Optional[str] = None,
                            
    search_quantity: Optional[str] = None,
                                                                              
    search_open_date: Optional[str] = None,
    search_close_date: Optional[str] = None,
    search_status_changed_at: Optional[str] = None,
                                                            
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    date_range_field: str = "open_date",                                                     
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
       
    conditions = []

                                                                               
    if current_user.role == UserRole.RECRUITER:
        today = _today()
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

                                                                               
    _dict_filters = {
        "status_id": (Vacancy.status_id, status_id),
        "level_id": (Vacancy.level_id, level_id),
        "it_role_id": (Vacancy.it_role_id, it_role_id),
        "project_id": (Vacancy.project_id, project_id),
        "admin_manager_id": (Vacancy.admin_manager_id, admin_manager_id),
        "team_lead_id": (Vacancy.team_lead_id, team_lead_id),
        "city_id": (Vacancy.city_id, city_id),
        "source_id": (Vacancy.source_id, source_id),
        "block_id": (Vacancy.block_id, block_id),
        "employment_type_id": (Vacancy.employment_type_id, employment_type_id),
        "feasibility_id": (Vacancy.feasibility_id, feasibility_id),
        "replacement_type_id": (Vacancy.replacement_type_id, replacement_type_id),
        "internal_transfer_id": (Vacancy.internal_transfer_id, internal_transfer_id),
        "recruiter_id": (Vacancy.recruiter_id, recruiter_id),
    }
    for _name, (col, values) in _dict_filters.items():
        if values:
            conditions.append(col.in_(values))

                                                                                
    _text_filters = {
        "search_vacancy_id": (Vacancy.vacancy_id, search_vacancy_id),
        "search_position_name": (Vacancy.position_name, search_position_name),
        "search_candidate_name": (Vacancy.candidate_name, search_candidate_name),
        "search_candidate_company": (Vacancy.candidate_company, search_candidate_company),
        "search_ex_employee_name": (Vacancy.ex_employee_name, search_ex_employee_name),
        "search_unit_id": (Vacancy.unit_id, search_unit_id),
        "search_iqhr_link": (Vacancy.iqhr_link, search_iqhr_link),
        "search_salary_gross": (Vacancy.salary_gross, search_salary_gross),
    }
    for _name, (col, val) in _text_filters.items():
        if val:
            conditions.append(col.ilike(f"%{val}%"))

                                                                                
    if search_quantity is not None:
        try:
            conditions.append(Vacancy.quantity == int(search_quantity))
        except (ValueError, TypeError):
            pass

                                                                               
    _date_point_filters = {
        "search_open_date": (Vacancy.open_date, search_open_date),
        "search_close_date": (Vacancy.close_date, search_close_date),
        "search_status_changed_at": (Vacancy.status_changed_at, search_status_changed_at),
    }
    for _name, (col, val) in _date_point_filters.items():
        if not val:
            continue
        parsed = _parse_date(val)
        if parsed:
            conditions.append(col == parsed)

                                                                               
    if date_from or date_to:
        range_col = {
            "open_date": Vacancy.open_date,
            "close_date": Vacancy.close_date,
            "status_changed_at": Vacancy.status_changed_at,
        }.get(date_range_field, Vacancy.open_date)

        if date_from:
            conditions.append(range_col >= date_from)
        if date_to:
            conditions.append(range_col <= date_to)

                                                                                
    if search:
        s = f"%{search}%"
        conditions.append(
            (Vacancy.position_name.ilike(s))
            | (Vacancy.candidate_name.ilike(s))
            | (Vacancy.vacancy_id.ilike(s))
            | (Vacancy.candidate_company.ilike(s))
        )

    if conditions:
        query = query.where(and_(*conditions))

    return query, conditions

                                                                                
                          
                                                                                

def _parse_date(val: str) -> Optional[date]:
\
\
\
\
\
\
       
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"):
        try:
            return datetime.strptime(val.strip(), fmt).date()
        except ValueError:
            continue
    return None