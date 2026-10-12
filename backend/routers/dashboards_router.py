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
   
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date as _date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Vacancy, WeeklyReport, Dictionary, DictionaryType, User, UserRole, VacancyHistory
from auth import get_current_user
from services.working_days_service import calculate_net_working_days
from fastapi_cache.decorator import cache

router = APIRouter(prefix="/dashboards", tags=["Дашборды"])

async def _dict_map(db: AsyncSession, dtype: DictionaryType) -> dict:
    rows = (await db.execute(
        select(Dictionary.id, Dictionary.value).where(Dictionary.type == dtype)
    )).all()
    return {r.id: r.value for r in rows}

def _parse_ids(raw: Optional[str]) -> Optional[list[int]]:
                                           
    if not raw:
        return None
    try:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    except ValueError:
        return None

@router.get("/metrics")
@cache(expire=30, namespace="dashboards")
async def get_dashboard_metrics(
    start_date:         Optional[str] = Query(None),
    end_date:           Optional[str] = Query(None),
    it_role_ids:        Optional[str] = Query(None),
    level_ids:          Optional[str] = Query(None),
    admin_manager_ids:  Optional[str] = Query(None),
    project_ids:        Optional[str] = Query(None),
    recruiter_ids:      Optional[str] = Query(None),
    block_ids:          Optional[str] = Query(None),
    status_ids:         Optional[str] = Query(None),
    group_by:           str           = Query("it_role"),
                                                            
    block_id:           Optional[int] = Query(None),
    project_id:         Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPERADMIN):
        raise HTTPException(
            status_code=403,
            detail="Доступ к дашбордам разрешен только администраторам и супер-администраторам",
        )

    dt_start: Optional[_date] = None
    dt_end:   Optional[_date] = None
    try:
        if start_date: dt_start = _date.fromisoformat(start_date)
        if end_date:   dt_end   = _date.fromisoformat(end_date)
    except ValueError:
        pass

    f_it_roles   = _parse_ids(it_role_ids)
    f_levels     = _parse_ids(level_ids)
    f_admin_mgrs = _parse_ids(admin_manager_ids)
    f_projects   = _parse_ids(project_ids)
    f_recruiters = _parse_ids(recruiter_ids)
    f_blocks     = _parse_ids(block_ids)
    f_statuses   = _parse_ids(status_ids)

    if block_id   and not f_blocks:   f_blocks   = [block_id]
    if project_id and not f_projects: f_projects = [project_id]

    status_map    = await _dict_map(db, DictionaryType.VACANCY_STATUS)
    source_map    = await _dict_map(db, DictionaryType.SOURCE)
    block_map     = await _dict_map(db, DictionaryType.BLOCK)
    project_map   = await _dict_map(db, DictionaryType.PROJECT)
    it_role_map   = await _dict_map(db, DictionaryType.IT_ROLE)
    level_map     = await _dict_map(db, DictionaryType.SPECIALIST_LEVEL)
    admin_mgr_map = await _dict_map(db, DictionaryType.ADMIN_MANAGER)
    replacement_map = await _dict_map(db, DictionaryType.REPLACEMENT_TYPE)
    employment_map  = await _dict_map(db, DictionaryType.EMPLOYMENT_TYPE)

    # 3.2. Разбираем статусы
    closed_ids = {k for k, v in status_map.items() if v == "Закрыта"}
    exit_ids   = {k for k, v in status_map.items() if v == "Выход"}
    hold_ids   = {k for k, v in status_map.items() if v == "Hold"}
    cancel_ids = {k for k, v in status_map.items() if v == "Отмена"}
    open_ids   = {k for k, v in status_map.items()
                  if v not in ("Закрыта", "Выход", "Отмена", "Hold")}

    # 3.3. Тянем вакансии (только нужные поля)
    all_vacs = (await db.execute(
        select(
            Vacancy.id, Vacancy.status_id, Vacancy.source_id,
            Vacancy.block_id, Vacancy.project_id,
            Vacancy.it_role_id, Vacancy.level_id,
            Vacancy.admin_manager_id, Vacancy.recruiter_id,
            Vacancy.co_recruiter_id,
            Vacancy.candidate_company,
            Vacancy.open_date, Vacancy.close_date,
            Vacancy.status_changed_at,
            Vacancy.replacement_type_id, Vacancy.employment_type_id,
            Vacancy.salary_gross, Vacancy.quantity,
            Vacancy.offer_rejection_reason,
            Vacancy.offer_accepted_cnt,
        )
    )).all()

    def date_matches(v) -> bool:
        if v.quantity == 0.001:
            return False
        if not dt_start and not dt_end:
            return True

        # Исключаем вакансии с датой открытия позже периода
        if dt_end and v.open_date and v.open_date > dt_end:
            return False

        st_name = status_map.get(v.status_id)

        # Закрыта: колонка "Дата закрытия" за выбранный период
        if st_name == "Закрыта":
            if not v.close_date:
                return False
            if dt_start and v.close_date < dt_start:
                return False
            if dt_end and v.close_date > dt_end:
                return False
            return True

        # Отмена: статус по "Дата изменения статуса" за период фильтра (включая пустые)
        if st_name == "Отмена":
            if v.status_changed_at is None:
                return True
            if dt_start and v.status_changed_at < dt_start:
                return False
            if dt_end and v.status_changed_at > dt_end:
                return False
            return True

        # Hold: статус по "Дата изменения статуса" за выбранный год фильтра (включая пустые)
        if st_name == "Hold":
            if v.status_changed_at is None:
                return True
            filter_year = (dt_end or dt_start).year
            if v.status_changed_at.year != filter_year:
                return False
            return True

        # Активные статусы (открыта, проверка сб, согласование фин условий, оффер, подготовка документов, выход)
        return True

    def matches_filters(v, exclude_field: Optional[str] = None) -> bool:
        if not date_matches(v):
            return False
        if exclude_field != "it_role" and f_it_roles and v.it_role_id not in f_it_roles:
            return False
        if exclude_field != "level" and f_levels and v.level_id not in f_levels:
            return False
        if exclude_field != "admin_manager" and f_admin_mgrs and v.admin_manager_id not in f_admin_mgrs:
            return False
        if exclude_field != "project" and f_projects and v.project_id not in f_projects:
            return False
        if exclude_field != "recruiter" and f_recruiters:
            rec_match = (v.recruiter_id in f_recruiters) or (v.co_recruiter_id and v.co_recruiter_id in f_recruiters)
            if not rec_match:
                return False
        if exclude_field != "block" and f_blocks and v.block_id not in f_blocks:
            return False
        if exclude_field != "status" and f_statuses and v.status_id not in f_statuses:
            return False
        return True

    vacs = [v for v in all_vacs if matches_filters(v)]

    report_query = select(
        WeeklyReport.vacancy_id,
        WeeklyReport.resumes_sent,
        WeeklyReport.candidates_agreed,
        WeeklyReport.interviews_planned,
        WeeklyReport.interviews_conducted,
        WeeklyReport.offer_made,
        WeeklyReport.week_start,
    )
    all_reports = (await db.execute(report_query)).all()

    reports_by_vac: dict = defaultdict(list)
    for r in all_reports:
        reports_by_vac[r.vacancy_id].append(r)

                                                                               
                                                                           
    final_vac_ids = {
        v.id for v in vacs
        if v.status_id in (closed_ids | exit_ids)
        and v.open_date and v.close_date
    }

    history_by_vac: dict[int, list] = defaultdict(list)
    if final_vac_ids:
        hist_rows = (await db.execute(
            select(
                VacancyHistory.vacancy_id,
                VacancyHistory.action_type,
                VacancyHistory.changes,
                VacancyHistory.created_at,
            ).where(
                VacancyHistory.vacancy_id.in_(final_vac_ids),
                VacancyHistory.action_type == "UPDATE",
            ).order_by(VacancyHistory.created_at)
        )).all()
        for r in hist_rows:
            history_by_vac[r.vacancy_id].append(r)

                                                                                 
    src_cnt: Counter = Counter()
    for v in vacs:
        if v.status_id in closed_ids:
            label = source_map.get(v.source_id, "Не указан") if v.source_id else "Не указан"
            src_cnt[label] += 1
    total1 = sum(src_cnt.values()) or 1
    chart1 = sorted(
        [{"name": k, "value": cnt, "pct": round(cnt / total1 * 100, 1)}
         for k, cnt in src_cnt.items()],
        key=lambda x: -x["value"],
    )

                                                                                
    chart2 = {
        "total":  len(vacs),
        "open":   sum(1 for v in vacs if v.status_id not in (closed_ids | exit_ids | hold_ids | cancel_ids)),
        "closed": sum(1 for v in vacs if v.status_id in closed_ids),
        "exit":   sum(1 for v in vacs if v.status_id in exit_ids),
        "hold":   sum(1 for v in vacs if v.status_id in hold_ids),
        "cancel": sum(1 for v in vacs if v.status_id in cancel_ids),
    }

                                                                                
    vac_ids3 = {v.id for v in vacs}
    funnel: dict = defaultdict(int)
    for v_id in vac_ids3:
        for r in reports_by_vac.get(v_id, []):
            funnel["resumes_sent"]         += r.resumes_sent         or 0
            funnel["candidates_agreed"]    += r.candidates_agreed    or 0
            funnel["interviews_planned"]   += r.interviews_planned   or 0
            funnel["interviews_conducted"] += r.interviews_conducted or 0
            funnel["offer_made"]           += r.offer_made           or 0
    chart3 = [
        {"stage": "Передано заказчику",  "value": funnel["resumes_sent"]},
        {"stage": "Резюме одобрено",      "value": funnel["candidates_agreed"]},
        {"stage": "Собеседования план",   "value": funnel["interviews_planned"]},
        {"stage": "Собеседования факт",   "value": funnel["interviews_conducted"]},
        {"stage": "Оффер сделан",         "value": funnel["offer_made"]},
    ]

                                                                                
    comp_cnt: Counter = Counter()
    for v in vacs:
        if v.status_id in closed_ids and v.candidate_company and v.candidate_company.strip():
            comp_cnt[v.candidate_company.strip()] += 1
    chart4 = [{"company": k, "value": cnt} for k, cnt in comp_cnt.most_common(15)]

                                                                               
                                 
                                                                  
                                                         
                                                                  
    use_map    = it_role_map if group_by == "it_role" else level_map
    group_attr = "it_role_id" if group_by == "it_role" else "level_id"

    durations: dict = defaultdict(list)
    for v in vacs:
        if v.status_id not in (closed_ids | exit_ids):
            continue
        if not v.close_date or not v.open_date:
            continue

        days = calculate_net_working_days(
            open_date=v.open_date,
            close_date=v.close_date,
            history_records=history_by_vac.get(v.id, []),
            status_map=status_map,
        )
        if days <= 0:
            continue

        gid   = getattr(v, group_attr)
        label = use_map.get(gid, "Не указано") if gid else "Не указано"
        durations[label].append(days)

    chart5 = sorted(
        [
            {"label": lbl, "avg_days": round(sum(vals) / len(vals), 1), "count": len(vals)}
            for lbl, vals in durations.items() if vals
        ],
        key=lambda x: -x["avg_days"],
    )

                                                                                
    st_cnt: Counter = Counter()
    for v in vacs:
        label = status_map.get(v.status_id, "Не указан") if v.status_id else "Не указан"
        st_cnt[label] += 1
    chart6 = sorted(
        [{"status": k, "value": cnt} for k, cnt in st_cnt.items()],
        key=lambda x: -x["value"],
    )

                                                                                
                                                          
    jo_closed    = sum(1 for v in vacs if v.status_id in (closed_ids | exit_ids))
    offers_total = sum(
        r.offer_made or 0
        for v in vacs
        for r in reports_by_vac.get(v.id, [])
    )
    jo_rate = round(jo_closed / offers_total * 100, 1) if offers_total else 0
    chart7  = {
        "closed":       jo_closed,
        "offers_total": offers_total,
        "jo_rate":      jo_rate,
    }

                                                                                
    recruiter_rows = (await db.execute(
        select(User.id, User.full_name).where(User.is_active == True)
    )).all()
    recruiters_opts = sorted(
        [{"id": r.id, "value": r.full_name} for r in recruiter_rows],
        key=lambda x: x["value"]
    )

                                                                               
    recruiter_load: dict = defaultdict(int)
    for v in vacs:
        if v.recruiter_id:
            name = next(
                (r["value"] for r in recruiters_opts if r["id"] == v.recruiter_id),
                f"ID {v.recruiter_id}"
            )
            recruiter_load[name] += 1
    chart8 = sorted(
        [{"recruiter": name, "value": cnt} for name, cnt in recruiter_load.items()],
        key=lambda x: -x["value"],
    )

    lvl_cnt: Counter = Counter()
    for v in vacs:
        label = level_map.get(v.level_id, "Не указан") if v.level_id else "Не указан"
        lvl_cnt[label] += 1
    chart_levels = sorted([{"level": k, "value": cnt} for k, cnt in lvl_cnt.items()], key=lambda x: -x["value"])

    rep_cnt: Counter = Counter()
    for v in vacs:
        label = replacement_map.get(v.replacement_type_id, "Не указан") if v.replacement_type_id else "Не указан"
        rep_cnt[label] += 1
    total_rep = sum(rep_cnt.values()) or 1
    chart_replacement = sorted([{"name": k, "value": cnt, "pct": round(cnt/total_rep*100,1)} for k, cnt in rep_cnt.items()], key=lambda x: -x["value"])

    emp_cnt: Counter = Counter()
    for v in vacs:
        label = employment_map.get(v.employment_type_id, "Не указан") if v.employment_type_id else "Не указан"
        emp_cnt[label] += 1
    total_emp = sum(emp_cnt.values()) or 1
    chart_employment = sorted([{"name": k, "value": cnt, "pct": round(cnt/total_emp*100,1)} for k, cnt in emp_cnt.items()], key=lambda x: -x["value"])

    import statistics
    sals = [v.salary_gross for v in vacs if v.salary_gross and v.salary_gross > 0]
    if sals:
        sals.sort()
        try:
            q = statistics.quantiles(sals, n=4)
            p25, p50, p75 = q[0], q[1], q[2]
        except AttributeError:
            n = len(sals)
            p25, p50, p75 = sals[n // 4], sals[n // 2], sals[(n * 3) // 4]
    else:
        p25, p50, p75 = 0, 0, 0
    chart_salaries = {"p25": round(p25), "p50": round(p50), "p75": round(p75)}

    # Причины отказа
    rejection_cnt: Counter = Counter()
    for v in vacs:
        if v.offer_rejection_reason and v.offer_rejection_reason.strip():
            rejection_cnt[v.offer_rejection_reason.strip()] += 1
    chart_rejections = sorted(
        [{"reason": k, "value": cnt} for k, cnt in rejection_cnt.items()],
        key=lambda x: -x["value"],
    )

    # Конверсия принятия JO (кумулятивная по месяцам, кварталам, году)
    target_year = (dt_end or dt_start).year if (dt_end or dt_start) else _date.today().year
    closed_vacs_pool = [v for v in all_vacs if matches_filters(v, "status") and v.status_id in closed_ids and v.close_date]
    year_closed_vacs = [v for v in closed_vacs_pool if v.close_date.year == target_year]

    vac_offers = {}
    for v in year_closed_vacs:
        reps = reports_by_vac.get(v.id, [])
        off = sum(r.offer_made or 0 for r in reps)
        if off == 0:
            off = max(v.offer_accepted_cnt or 0, v.quantity or 1)
        vac_offers[v.id] = off

    if dt_end and dt_end.year == target_year:
        max_m = dt_end.month
    else:
        months_in_data = [v.close_date.month for v in year_closed_vacs]
        max_m = max(months_in_data) if months_in_data else (_date.today().month if target_year == _date.today().year else 12)
    max_m = max(1, min(12, max_m))

    MONTH_NAMES = [
        ("Янв", "январь"), ("Фев", "февраль"), ("Мар", "март"),
        ("Апр", "апрель"), ("Май", "май"), ("Июн", "июнь"),
        ("Июл", "июль"), ("Авг", "август"), ("Сен", "сентябрь"),
        ("Окт", "октябрь"), ("Ноя", "ноябрь"), ("Дек", "декабрь")
    ]

    month_items = []
    for m in range(1, max_m + 1):
        cum_vacs = [v for v in year_closed_vacs if v.close_date.month <= m]
        cum_closed = sum(v.quantity or 1 for v in cum_vacs)
        cum_off = sum(vac_offers.get(v.id, 0) for v in cum_vacs)
        rate = round(cum_closed / cum_off * 100, 1) if cum_off > 0 else (100.0 if cum_closed > 0 else 0.0)
        month_items.append({
            "label": MONTH_NAMES[m - 1][0],
            "name": MONTH_NAMES[m - 1][1],
            "closed": cum_closed,
            "offers": cum_off,
            "value": rate,
        })

    Q_NAMES = ["Q1 (янв–мар)", "Q2 (апр–июн)", "Q3 (июл–сен)", "Q4 (окт–дек)"]
    quarter_items = []
    for q in range(1, 5):
        q_start_m = (q - 1) * 3 + 1
        if max_m < q_start_m:
            break
        q_end_m = min(q * 3, max_m)
        cum_vacs = [v for v in year_closed_vacs if v.close_date.month <= q_end_m]
        cum_closed = sum(v.quantity or 1 for v in cum_vacs)
        cum_off = sum(vac_offers.get(v.id, 0) for v in cum_vacs)
        rate = round(cum_closed / cum_off * 100, 1) if cum_off > 0 else (100.0 if cum_closed > 0 else 0.0)
        quarter_items.append({
            "label": f"Q{q}",
            "name": Q_NAMES[q - 1],
            "closed": cum_closed,
            "offers": cum_off,
            "value": rate,
        })

    cum_vacs_yr = [v for v in year_closed_vacs if v.close_date.month <= max_m]
    cum_closed_yr = sum(v.quantity or 1 for v in cum_vacs_yr)
    cum_off_yr = sum(vac_offers.get(v.id, 0) for v in cum_vacs_yr)
    rate_yr = round(cum_closed_yr / cum_off_yr * 100, 1) if cum_off_yr > 0 else (100.0 if cum_closed_yr > 0 else 0.0)
    year_items = [{
        "label": f"{target_year}",
        "name": f"{target_year} год",
        "closed": cum_closed_yr,
        "offers": cum_off_yr,
        "value": rate_yr,
    }]

    chart_jo_conversion = {
        "month": month_items,
        "quarter": quarter_items,
        "year": year_items,
    }

    # Взаимозависимые фильтры, зависимые от даты и остальных выбранных фильтров
    def _opts(m: dict, allowed_ids: Optional[set] = None):
        if allowed_ids is not None:
            return sorted([{"id": k, "value": v} for k, v in m.items() if k in allowed_ids], key=lambda x: x["value"])
        return sorted([{"id": k, "value": v} for k, v in m.items()], key=lambda x: x["value"])

    avail_blocks     = {v.block_id for v in all_vacs if v.block_id and matches_filters(v, "block")}
    avail_projects   = {v.project_id for v in all_vacs if v.project_id and matches_filters(v, "project")}
    avail_it_roles   = {v.it_role_id for v in all_vacs if v.it_role_id and matches_filters(v, "it_role")}
    avail_levels     = {v.level_id for v in all_vacs if v.level_id and matches_filters(v, "level")}
    avail_admin_mgrs = {v.admin_manager_id for v in all_vacs if v.admin_manager_id and matches_filters(v, "admin_manager")}
    avail_recruiters = {
        v.recruiter_id for v in all_vacs if v.recruiter_id and matches_filters(v, "recruiter")
    } | {
        v.co_recruiter_id for v in all_vacs if v.co_recruiter_id and matches_filters(v, "recruiter")
    }
    avail_statuses   = {v.status_id for v in all_vacs if v.status_id and matches_filters(v, "status")}

    filter_blocks         = _opts(block_map, avail_blocks)
    filter_projects       = _opts(project_map, avail_projects)
    filter_it_roles       = _opts(it_role_map, avail_it_roles)
    filter_levels         = _opts(level_map, avail_levels)
    filter_admin_managers = _opts(admin_mgr_map, avail_admin_mgrs)
    filter_recruiters     = [r for r in recruiters_opts if r["id"] in avail_recruiters]
    filter_statuses       = _opts(status_map, avail_statuses)

    return {
        "chart1_source":         chart1,
        "chart2_open_closed":    chart2,
        "chart3_funnel":         chart3,
        "chart4_companies":      chart4,
        "chart5_avg_days":       chart5,
        "chart6_statuses":       chart6,
        "chart7_jo_rate":        chart7,
        "chart8_recruiter_load": chart8,
        "chart_levels":          chart_levels,
        "chart_replacement":     chart_replacement,
        "chart_employment":      chart_employment,
        "chart_salaries":        chart_salaries,
        "chart_rejections":      chart_rejections,
        "chart_jo_conversion":   chart_jo_conversion,
        "filters": {
            "blocks":         filter_blocks,
            "projects":       filter_projects,
            "it_roles":       filter_it_roles,
            "levels":         filter_levels,
            "admin_managers": filter_admin_managers,
            "recruiters":     filter_recruiters,
            "statuses":       filter_statuses,
        },
    }