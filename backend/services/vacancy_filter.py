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

from sqlalchemy import and_, or_, select, func, cast, String
from sqlalchemy.orm import Query

from models import Vacancy, UserRole, User, VacancyDelegation, Dictionary

_EMPTY_TEXT_KEYWORDS = {
    "__empty__", "empty", "null", "none", "is_null", "пусто", "не указано", "без указания"
}


def _empty_text_cond(col):
    return or_(col.is_(None), func.trim(col) == "")


def _is_empty_kw(val: str) -> bool:
    return val.strip().lower() in _EMPTY_TEXT_KEYWORDS

                                                                                
                      
                                                                                

def apply_vacancy_filters(
    query,
    current_user: User,
    *,
    status_id: Optional[List[int]] = None,
    exclude_status_id: Optional[List[int]] = None,
    level_id: Optional[List[int]] = None,
    it_role_id: Optional[List[int]] = None,
    project_id: Optional[List[int]] = None,
    admin_manager_id: Optional[List[int]] = None,
    source_id: Optional[List[int]] = None,
    block_id: Optional[List[int]] = None,
    employment_type_id: Optional[List[int]] = None,
    feasibility_id: Optional[List[int]] = None,
    replacement_type_id: Optional[List[int]] = None,
    internal_transfer_id: Optional[List[int]] = None,
    recruiter_id: Optional[List[int]] = None,
    co_recruiter_id: Optional[List[int]] = None,
    city_id: Optional[List[int]] = None,
    team_lead_id: Optional[List[int]] = None,
                                
    search: Optional[str] = None,
    search_vacancy_id: Optional[str] = None,
    search_position_name: Optional[str] = None,
    search_candidate_name: Optional[str] = None,
    search_candidate_company: Optional[str] = None,
    search_ex_employee_name: Optional[str] = None,
    search_unit_id: Optional[str] = None,
    search_iqhr_link: Optional[str] = None,
    search_salary_gross: Optional[str] = None,
    search_city_text: Optional[str] = None,
    search_team_lead_text: Optional[str] = None,
    search_feasibility_text: Optional[str] = None,
    search_offer_rejection_reason: Optional[str] = None,
    offer_rejection_reason: Optional[List[str]] = None,
    search_comment: Optional[str] = None,
    search_recommender_name: Optional[str] = None,
    recommender_name: Optional[str] = None,
    search_recruiter: Optional[str] = None,
    search_co_recruiter: Optional[str] = None,
                            
    search_quantity: Optional[str] = None,
    search_work_duration_days: Optional[str] = None,
    search_resume_at_customer: Optional[str] = None,
    search_resume_approved: Optional[str] = None,
    search_interviews_fact: Optional[str] = None,
    search_interviews_plan: Optional[str] = None,
    search_offer_made: Optional[str] = None,
    search_offer_accepted: Optional[str] = None,
                                                                              
    search_open_date: Optional[str] = None,
    search_close_date: Optional[str] = None,
    search_status_changed_at: Optional[str] = None,
    search_open_date_from: Optional[str] = None,
    search_open_date_to: Optional[str] = None,
    search_close_date_from: Optional[str] = None,
    search_close_date_to: Optional[str] = None,
    search_status_changed_at_from: Optional[str] = None,
    search_status_changed_at_to: Optional[str] = None,
                                                            
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    date_range_field: str = "open_date",
    **kwargs,
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
                Vacancy.co_recruiter_id == current_user.id,
                Vacancy.id.in_(delegated_subq),
            )
        )

                                                                               
    _dict_filters = {
        "status_id": (Vacancy.status_id, status_id),
        "level_id": (Vacancy.level_id, level_id),
        "it_role_id": (Vacancy.it_role_id, it_role_id),
        "project_id": (Vacancy.project_id, project_id),
        "admin_manager_id": (Vacancy.admin_manager_id, admin_manager_id),
        "source_id": (Vacancy.source_id, source_id),
        "block_id": (Vacancy.block_id, block_id),
        "employment_type_id": (Vacancy.employment_type_id, employment_type_id),
        "feasibility_id": (Vacancy.feasibility_id, feasibility_id),
        "replacement_type_id": (Vacancy.replacement_type_id, replacement_type_id),
        "internal_transfer_id": (Vacancy.internal_transfer_id, internal_transfer_id),
        "city_id": (Vacancy.city_id, city_id),
        "team_lead_id": (Vacancy.team_lead_id, team_lead_id),
    }
    _hybrid_text_cols = {
        "feasibility_id": Vacancy.feasibility_text,
        "city_id": Vacancy.city_text,
        "team_lead_id": Vacancy.team_lead_text,
    }
    for _name, (col, values) in _dict_filters.items():
        if values:
            text_fb = _hybrid_text_cols.get(_name)
            if 0 in values:
                # If 0 is in the filter list, filter for truly empty (both FK and fallback text)
                valid_ids = [v for v in values if v != 0]
                empty_cond = (
                    and_(col.is_(None), _empty_text_cond(text_fb))
                    if text_fb is not None else col.is_(None)
                )
                if valid_ids:
                    match_cond = (
                        or_(
                            col.in_(valid_ids),
                            and_(col.is_(None), text_fb.in_(select(Dictionary.value).where(Dictionary.id.in_(valid_ids)))),
                        )
                        if text_fb is not None else col.in_(valid_ids)
                    )
                    conditions.append(or_(match_cond, empty_cond))
                else:
                    conditions.append(empty_cond)
            else:
                if text_fb is not None:
                    conditions.append(or_(
                        col.in_(values),
                        and_(col.is_(None), text_fb.in_(select(Dictionary.value).where(Dictionary.id.in_(values)))),
                    ))
                else:
                    conditions.append(col.in_(values))

    if recruiter_id:
        if 0 in recruiter_id:
            valid_ids = [v for v in recruiter_id if v != 0]
            if valid_ids:
                conditions.append(or_(
                    Vacancy.recruiter_id.in_(valid_ids),
                    Vacancy.co_recruiter_id.in_(valid_ids),
                    and_(Vacancy.recruiter_id.is_(None), Vacancy.co_recruiter_id.is_(None))
                ))
            else:
                conditions.append(and_(Vacancy.recruiter_id.is_(None), Vacancy.co_recruiter_id.is_(None)))
        else:
            conditions.append(or_(Vacancy.recruiter_id.in_(recruiter_id), Vacancy.co_recruiter_id.in_(recruiter_id)))

    if co_recruiter_id:
        if 0 in co_recruiter_id:
            valid_ids = [v for v in co_recruiter_id if v != 0]
            if valid_ids:
                conditions.append(or_(Vacancy.co_recruiter_id.in_(valid_ids), Vacancy.co_recruiter_id.is_(None)))
            else:
                conditions.append(Vacancy.co_recruiter_id.is_(None))
        else:
            conditions.append(Vacancy.co_recruiter_id.in_(co_recruiter_id))

    if search_recruiter:
        rec_subq = select(User.id).where(User.full_name.ilike(f"%{search_recruiter}%"))
        conditions.append(or_(
            Vacancy.recruiter_id.in_(rec_subq),
            Vacancy.co_recruiter_id.in_(rec_subq)
        ))

    if search_co_recruiter:
        co_rec_subq = select(User.id).where(User.full_name.ilike(f"%{search_co_recruiter}%"))
        conditions.append(Vacancy.co_recruiter_id.in_(co_rec_subq))

    if exclude_status_id:
        conditions.append(or_(Vacancy.status_id.not_in(exclude_status_id), Vacancy.status_id.is_(None)))

                                                                                
    if search_vacancy_id:
        s_vid = str(search_vacancy_id).strip()
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

    _hybrid_fk_cols = {
        "search_city_text": Vacancy.city_id,
        "search_team_lead_text": Vacancy.team_lead_id,
        "search_feasibility_text": Vacancy.feasibility_id,
    }
    _text_filters = {
        "search_position_name": (Vacancy.position_name, search_position_name or kwargs.get("position_name")),
        "search_candidate_name": (Vacancy.candidate_name, search_candidate_name or kwargs.get("candidate_name")),
        "search_candidate_company": (Vacancy.candidate_company, search_candidate_company or kwargs.get("candidate_company")),
        "search_ex_employee_name": (Vacancy.ex_employee_name, search_ex_employee_name or kwargs.get("ex_employee_name")),
        "search_unit_id": (Vacancy.unit_id, search_unit_id or kwargs.get("unit_id")),
        "search_iqhr_link": (Vacancy.iqhr_link, search_iqhr_link or kwargs.get("iqhr_link")),
        "search_city_text": (Vacancy.city_text, search_city_text or kwargs.get("city_text")),
        "search_team_lead_text": (Vacancy.team_lead_text, search_team_lead_text or kwargs.get("team_lead_text")),
        "search_feasibility_text": (Vacancy.feasibility_text, search_feasibility_text or kwargs.get("feasibility_text")),
        "search_comment": (Vacancy.comment, search_comment or kwargs.get("comment")),
        "search_recommender_name": (Vacancy.recommender_name, search_recommender_name or recommender_name or kwargs.get("recommender_name")),
    }
    for _name, (col, val) in _text_filters.items():
        if val is not None:
            if isinstance(val, (list, tuple)):
                val = val[0] if val else None
            if val is not None and str(val).strip():
                clean_val = str(val).strip()
                fk_col = _hybrid_fk_cols.get(_name)
                if _is_empty_kw(clean_val):
                    if fk_col is not None:
                        conditions.append(and_(fk_col.is_(None), _empty_text_cond(col)))
                    else:
                        conditions.append(_empty_text_cond(col))
                elif fk_col is not None:
                    dict_match_subq = select(Dictionary.id).where(Dictionary.value.ilike(f"%{clean_val}%"))
                    conditions.append(or_(col.ilike(f"%{clean_val}%"), fk_col.in_(dict_match_subq)))
                else:
                    conditions.append(col.ilike(f"%{clean_val}%"))

    raw_reasons = []
    if offer_rejection_reason:
        raw_reasons.extend(offer_rejection_reason)
    elif kwargs.get("offer_rejection_reason"):
        extra_rej = kwargs.get("offer_rejection_reason")
        if isinstance(extra_rej, (list, tuple)):
            raw_reasons.extend(extra_rej)
        elif extra_rej:
            raw_reasons.append(extra_rej)
    elif search_offer_rejection_reason:
        raw_reasons.append(search_offer_rejection_reason)

    reason_conds = []
    for rv in raw_reasons:
        if rv is None:
            continue
        r_str = str(rv).strip()
        if not r_str:
            continue
        if _is_empty_kw(r_str) or r_str == "0":
            reason_conds.append(_empty_text_cond(Vacancy.offer_rejection_reason))
        else:
            reason_conds.append(Vacancy.offer_rejection_reason.ilike(f"%{r_str}%"))
    if reason_conds:
        conditions.append(or_(*reason_conds))

    _num_specs = [
        (search_quantity, Vacancy.quantity, float, "none"),
        (search_salary_gross, Vacancy.salary_gross, int, "none"),
        (search_work_duration_days, (func.coalesce(Vacancy.close_date, func.current_date()) - Vacancy.open_date - func.coalesce(Vacancy.hold_days, 0)), int, "open_date"),
        (search_resume_at_customer, Vacancy.resume_at_customer, int, "zero"),
        (search_resume_approved, Vacancy.resume_approved, int, "zero"),
        (search_interviews_fact, Vacancy.interviews_fact, int, "zero"),
        (search_interviews_plan, Vacancy.interviews_plan, int, "zero"),
        (search_offer_made, Vacancy.offer_made, int, "zero"),
        (search_offer_accepted, Vacancy.offer_accepted_cnt, int, "zero"),
    ]
    for raw_num, num_col, caster, empty_mode in _num_specs:
        if raw_num is None:
            continue
        num_str = str(raw_num[0] if isinstance(raw_num, (list, tuple)) else raw_num).strip()
        if not num_str:
            continue
        if _is_empty_kw(num_str):
            if empty_mode == "none":
                conditions.append(num_col.is_(None))
            elif empty_mode == "zero":
                conditions.append(or_(num_col == 0, num_col.is_(None)))
            else:
                conditions.append(Vacancy.open_date.is_(None))
            continue
        try:
            conditions.append(num_col == caster(num_str.replace(',', '.')))
        except (ValueError, TypeError):
            pass

                                                                               
    _EMPTY_DATE_KEYWORDS = {
        "empty", "null", "none", "is_null", "пусто", "без даты", "-",
        "__empty__", "not_set", "undefined"
    }

    # Fallback to direct field names if passed via kwargs
    search_open_date = search_open_date or kwargs.get("open_date")
    search_close_date = search_close_date or kwargs.get("close_date")
    search_status_changed_at = search_status_changed_at or kwargs.get("status_changed_at")
    search_open_date_from = search_open_date_from or kwargs.get("open_date_from")
    search_open_date_to = search_open_date_to or kwargs.get("open_date_to")
    search_close_date_from = search_close_date_from or kwargs.get("close_date_from")
    search_close_date_to = search_close_date_to or kwargs.get("close_date_to")
    search_status_changed_at_from = search_status_changed_at_from or kwargs.get("status_changed_at_from")
    search_status_changed_at_to = search_status_changed_at_to or kwargs.get("status_changed_at_to")

    _date_point_filters = {
        "search_open_date": (Vacancy.open_date, search_open_date),
        "search_close_date": (Vacancy.close_date, search_close_date),
        "search_status_changed_at": (Vacancy.status_changed_at, search_status_changed_at),
    }
    for _name, (col, val) in _date_point_filters.items():
        if val is None or val == "":
            continue
        v_str = str(val[0] if isinstance(val, (list, tuple)) else val).strip().lower()
        if v_str in _EMPTY_DATE_KEYWORDS:
            conditions.append(col.is_(None))
            continue
        if v_str in ("not_empty", "not_null", "is_not_null", "не пусто", "заполнено"):
            conditions.append(col.is_not(None))
            continue
        parsed = _parse_date(v_str)
        if parsed:
            conditions.append(col == parsed)

                                                                               
    _date_range_filters = [
        (Vacancy.open_date,         search_open_date_from,         search_open_date_to),
        (Vacancy.close_date,        search_close_date_from,        search_close_date_to),
        (Vacancy.status_changed_at, search_status_changed_at_from, search_status_changed_at_to),
    ]
    for col, val_from, val_to in _date_range_filters:
        vf_str = str(val_from[0] if isinstance(val_from, (list, tuple)) else val_from).strip().lower() if val_from else ""
        vt_str = str(val_to[0] if isinstance(val_to, (list, tuple)) else val_to).strip().lower() if val_to else ""
        if vf_str in _EMPTY_DATE_KEYWORDS or vt_str in _EMPTY_DATE_KEYWORDS:
            conditions.append(col.is_(None))
            continue
        if val_from:
            parsed_from = _parse_date(vf_str)
            if parsed_from:
                conditions.append(col >= parsed_from)
        if val_to:
            parsed_to = _parse_date(vt_str)
            if parsed_to:
                conditions.append(col <= parsed_to)

                                                                               
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
            | (Vacancy.recommender_name.ilike(s))
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