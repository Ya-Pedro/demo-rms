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

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Vacancy, WeeklyReport, Dictionary, DictionaryType, User, VacancyHistory
from auth import get_current_user
from services.working_days_service import calculate_net_working_days

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
            Vacancy.candidate_company,
            Vacancy.open_date, Vacancy.close_date,
            Vacancy.replacement_type_id, Vacancy.employment_type_id,
            Vacancy.salary_gross, Vacancy.quantity,
        )
    )).all()

                                                                                
    def passes(v) -> bool:
        if v.quantity == 0.001:
            return False
        if v.open_date:
            if dt_end and v.open_date > dt_end:
                return False
        if dt_start:
            if v.close_date and v.close_date < dt_start:
                return False
        if f_it_roles   and v.it_role_id       not in f_it_roles:   return False
        if f_levels     and v.level_id         not in f_levels:     return False
        if f_admin_mgrs and v.admin_manager_id not in f_admin_mgrs: return False
        if f_projects   and v.project_id       not in f_projects:   return False
        if f_recruiters and v.recruiter_id     not in f_recruiters: return False
        if f_blocks     and v.block_id         not in f_blocks:     return False
        if f_statuses   and v.status_id        not in f_statuses:   return False
        return True

    vacs = [v for v in all_vacs if passes(v)]

                                                                                
    all_reports = (await db.execute(
        select(
            WeeklyReport.vacancy_id,
            WeeklyReport.resumes_sent,
            WeeklyReport.candidates_agreed,
            WeeklyReport.interviews_planned,
            WeeklyReport.interviews_conducted,
            WeeklyReport.offer_made,
        )
    )).all()

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
        "open":   sum(1 for v in vacs if v.status_id in open_ids),
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
        if v.candidate_company and v.candidate_company.strip():
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

    def _opts(m: dict):
        return sorted([{"id": k, "value": v} for k, v in m.items()], key=lambda x: x["value"])

    return {
        "chart1_source":      chart1,
        "chart2_open_closed": chart2,
        "chart3_funnel":      chart3,
        "chart4_companies":   chart4,
        "chart5_avg_days":    chart5,
        "chart6_statuses":    chart6,
        "chart7_jo_rate":     chart7,
        "chart8_recruiter_load": chart8,
        "chart_levels":       chart_levels,
        "chart_replacement":  chart_replacement,
        "chart_employment":   chart_employment,
        "chart_salaries":     chart_salaries,
        "filters": {
            "blocks":         _opts(block_map),
            "projects":       _opts(project_map),
            "it_roles":       _opts(it_role_map),
            "levels":         _opts(level_map),
            "admin_managers": _opts(admin_mgr_map),
            "recruiters":     recruiters_opts,
            "statuses":       _opts(status_map),
        },
    }