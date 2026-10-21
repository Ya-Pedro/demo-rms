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
    vacancy_ids:        Optional[str] = Query(None),
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
        if dt_start and dt_end and dt_start > dt_end:
            dt_start, dt_end = dt_end, dt_start
    except ValueError:
        pass

    f_it_roles   = _parse_ids(it_role_ids)
    f_levels     = _parse_ids(level_ids)
    f_admin_mgrs = _parse_ids(admin_manager_ids)
    f_projects   = _parse_ids(project_ids)
    f_recruiters = _parse_ids(recruiter_ids)
    f_blocks     = _parse_ids(block_ids)
    f_statuses   = _parse_ids(status_ids)
    f_vac_tokens = set(x.strip() for x in vacancy_ids.split(",") if x.strip()) if vacancy_ids else None

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
            Vacancy.id, Vacancy.vacancy_id, Vacancy.status_id, Vacancy.source_id,
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

    # Загружаем историю вакансий, выходивших из статуса Hold после даты среза dt_end
    hold_exits: dict[int, _date] = {}
    if dt_end:
        hist_hold_rows = (await db.execute(
            select(
                VacancyHistory.vacancy_id,
                VacancyHistory.created_at,
                VacancyHistory.changes,
            ).where(
                VacancyHistory.changes.ilike('%Hold%'),
                VacancyHistory.action_type == "UPDATE",
            )
        )).all()
        import json as _json
        for hr in hist_hold_rows:
            try:
                ch = _json.loads(hr.changes) if isinstance(hr.changes, str) else hr.changes
                st_ch = ch.get("Статус вакансии") or ch.get("status")
                if st_ch and st_ch.get("old") == "Hold":
                    exit_d = hr.created_at.date()
                    if hr.vacancy_id not in hold_exits or exit_d > hold_exits[hr.vacancy_id]:
                        hold_exits[hr.vacancy_id] = exit_d
            except Exception:
                pass

    def get_effective_status(v) -> Optional[str]:
        if v.quantity == 0.001:
            return None
        if dt_end and v.open_date and v.open_date > dt_end:
            return None

        st_name = status_map.get(v.status_id)
        if not dt_start and not dt_end:
            return st_name

        # Если вакансия вышла из Hold позже даты среза dt_end, на момент среза она была в Hold
        if dt_end and v.id in hold_exits:
            exit_d = hold_exits[v.id]
            if exit_d > dt_end:
                return "Hold"

        if st_name == "Закрыта":
            c_date = v.close_date
            if not c_date and v.status_changed_at:
                c_date = v.status_changed_at
            if not c_date:
                return None
            if dt_start and c_date < dt_start:
                return None
            if dt_end and c_date > dt_end:
                return "Открыта"
            return "Закрыта"

        if st_name == "Отмена":
            c_date = v.status_changed_at or v.close_date
            if not c_date:
                if dt_end and v.open_date and v.open_date <= dt_end:
                    return "Открыта"
                return None
            if dt_start and c_date < dt_start:
                return None
            if dt_end and c_date > dt_end:
                return "Открыта"
            return "Отмена"

        if st_name == "Hold":
            h_date = v.status_changed_at
            if dt_end and h_date and h_date > dt_end:
                return "Открыта"
            # На дату среза была в Hold (без ограничения снизу, тянется с 2025 и ранее)
            return "Hold"

        return st_name

    def matches_filters(v, exclude_field: Optional[str] = None) -> bool:
        eff_st = get_effective_status(v)
        if eff_st is None:
            return False
        if exclude_field != "vacancy" and f_vac_tokens:
            matches_vac = (
                str(v.id) in f_vac_tokens or
                (v.vacancy_id and str(v.vacancy_id).strip() in f_vac_tokens)
            )
            if not matches_vac:
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
        if exclude_field != "status" and f_statuses:
            allowed_status_names = {status_map.get(sid) for sid in f_statuses if sid in status_map}
            if eff_st not in allowed_status_names:
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
        WeeklyReport.offer_accepted,
        WeeklyReport.offer_rejection_reason,
        WeeklyReport.week_start,
    )
    all_reports = (await db.execute(report_query)).all()

    reports_by_vac: dict = defaultdict(list)
    for r in all_reports:
        reports_by_vac[r.vacancy_id].append(r)

    # Загружаем историю для всех закрытых вакансий (для корректного расчёта рабочих дней)
    final_vac_ids = {
        v.id for v in all_vacs
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
        if get_effective_status(v) == "Закрыта":
            label = source_map.get(v.source_id, "Не указан") if v.source_id else "Не указан"
            src_cnt[label] += 1
    total1 = sum(src_cnt.values()) or 1
    chart1 = sorted(
        [{"name": k, "value": cnt, "pct": round(cnt / total1 * 100, 1)}
         for k, cnt in src_cnt.items()],
        key=lambda x: -x["value"],
    )

    open_cnt = 0
    closed_cnt = 0
    hold_cnt = 0
    cancel_cnt = 0
    for v in vacs:
        eff = get_effective_status(v)
        if eff == "Закрыта":
            closed_cnt += 1
        elif eff == "Hold":
            hold_cnt += 1
        elif eff == "Отмена":
            cancel_cnt += 1
        else:
            open_cnt += 1

    chart2 = {
        "total":  open_cnt + closed_cnt + hold_cnt + cancel_cnt,
        "open":   open_cnt,
        "closed": closed_cnt,
        "hold":   hold_cnt,
        "cancel": cancel_cnt,
    }

    vac_ids3 = {v.id for v in vacs}
    funnel: dict = defaultdict(int)
    for v_id in vac_ids3:
        for r in reports_by_vac.get(v_id, []):
            funnel["resumes_sent"]         += r.resumes_sent         or 0
            funnel["candidates_agreed"]    += r.candidates_agreed    or 0
            funnel["interviews_conducted"] += r.interviews_conducted or 0
            funnel["offer_made"]           += r.offer_made           or 0
            funnel["offer_accepted"]       += r.offer_accepted       or 0

    closed_in_funnel = sum(1 for v in vacs if get_effective_status(v) == "Закрыта")
    if funnel["offer_accepted"] == 0:
        funnel["offer_accepted"] = sum(v.offer_accepted_cnt or 0 for v in vacs)
        if funnel["offer_accepted"] == 0 and closed_in_funnel > 0:
            funnel["offer_accepted"] = closed_in_funnel

    raw_stages = [
        ("Передано заказчику", funnel["resumes_sent"]),
        ("Резюме одобрено",    funnel["candidates_agreed"]),
        ("Собеседования",      funnel["interviews_conducted"]),
        ("Оффер сделан",       funnel["offer_made"]),
        ("Оффер принят",       funnel["offer_accepted"]),
        ("Закрыта",            closed_in_funnel),
    ]

    first_val = raw_stages[0][1] if raw_stages else 0
    chart3 = []
    for i, (stg_name, val) in enumerate(raw_stages):
        prev_val = raw_stages[i - 1][1] if i > 0 else val
        step_pct = round(val / prev_val * 100, 1) if prev_val > 0 else 0.0
        tot_pct  = round(val / first_val * 100, 1) if first_val > 0 else 0.0
        chart3.append({
            "stage": stg_name,
            "value": val,
            "conv_step": step_pct,
            "conv_total": tot_pct,
        })

    comp_cnt: Counter = Counter()
    for v in vacs:
        if get_effective_status(v) == "Закрыта" and v.candidate_company and v.candidate_company.strip():
            comp_cnt[v.candidate_company.strip()] += 1
    chart4 = [{"company": k, "value": cnt} for k, cnt in comp_cnt.most_common(15)]

    use_map    = it_role_map if group_by == "it_role" else level_map
    group_attr = "it_role_id" if group_by == "it_role" else "level_id"

    durations: dict = defaultdict(list)
    for v in vacs:
        if get_effective_status(v) != "Закрыта":
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
        eff = get_effective_status(v)
        if eff in ("Закрыта", "Hold", "Отмена"):
            st_name = eff
        else:
            cur_st = status_map.get(v.status_id)
            if cur_st in ("Закрыта", "Hold", "Отмена") or not cur_st:
                st_name = "Открыта"
            else:
                st_name = cur_st
        st_cnt[st_name] += 1
    chart6 = sorted(
        [{"status": k, "value": cnt} for k, cnt in st_cnt.items()],
        key=lambda x: -x["value"],
    )

    jo_closed    = sum(1 for v in vacs if get_effective_status(v) == "Закрыта")
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
        if v.co_recruiter_id:
            name_co = next(
                (r["value"] for r in recruiters_opts if r["id"] == v.co_recruiter_id),
                f"ID {v.co_recruiter_id}"
            )
            recruiter_load[name_co] += 1
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
        p50 = statistics.median(sals)
        if len(sals) >= 2:
            try:
                q = statistics.quantiles(sals, n=4)
                p25, p75 = q[0], q[2]
            except Exception:
                n = len(sals)
                p25, p75 = sals[n // 4], sals[(n * 3) // 4]
        else:
            p25, p75 = sals[0], sals[0]
    else:
        p25, p50, p75 = 0, 0, 0
    chart_salaries = {"p25": round(p25), "p50": round(p50), "p75": round(p75), "count": len(sals)}

    # Причины отказа: все причины из справочника со значением 0 по умолчанию
    rejection_reason_map = await _dict_map(db, DictionaryType.OFFER_REJECTION_REASON)
    rejection_cnt: dict[str, int] = {name: 0 for name in rejection_reason_map.values()}
    for v in vacs:
        reasons_from_reports = [
            r.offer_rejection_reason.strip()
            for r in reports_by_vac.get(v.id, [])
            if getattr(r, 'offer_rejection_reason', None) and r.offer_rejection_reason.strip()
        ]
        if reasons_from_reports:
            for rsn in reasons_from_reports:
                rejection_cnt[rsn] = rejection_cnt.get(rsn, 0) + 1
        elif v.offer_rejection_reason and v.offer_rejection_reason.strip():
            rsn = v.offer_rejection_reason.strip()
            rejection_cnt[rsn] = rejection_cnt.get(rsn, 0) + 1

    chart_rejections = sorted(
        [{"reason": k, "value": cnt} for k, cnt in rejection_cnt.items()],
        key=lambda x: -x["value"],
    )

    # Конверсия принятия JO (кумулятивная по месяцам, кварталам, году)
    target_year = (dt_end or dt_start).year if (dt_end or dt_start) else _date.today().year
    closed_vacs_pool = [v for v in all_vacs if matches_filters(v, "status") and get_effective_status(v) == "Закрыта" and v.close_date]
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

    # Динамика среднего срока закрытия вакансий (раб. дни) по месяцам, кварталам, году
    vac_days_map = {}
    for v in closed_vacs_pool:
        if not v.open_date or not v.close_date:
            continue
        d = calculate_net_working_days(
            open_date=v.open_date,
            close_date=v.close_date,
            history_records=history_by_vac.get(v.id, []),
            status_map=status_map,
        )
        if d > 0:
            vac_days_map[v.id] = d

    year_closed_avg = [v for v in closed_vacs_pool if v.close_date.year == target_year and v.id in vac_days_map]

    avg_month_items = []
    for m in range(1, max_m + 1):
        m_vacs = [v for v in year_closed_avg if v.close_date.month == m]
        m_days = [vac_days_map[v.id] for v in m_vacs]
        avg_d = round(sum(m_days) / len(m_days), 1) if m_days else 0
        avg_month_items.append({
            "label": MONTH_NAMES[m - 1][0],
            "name": MONTH_NAMES[m - 1][1].capitalize(),
            "value": avg_d,
            "count": len(m_vacs),
        })

    avg_quarter_items = []
    for q in range(1, 5):
        q_start_m = (q - 1) * 3 + 1
        if max_m < q_start_m:
            break
        q_end_m = min(q * 3, max_m)
        q_vacs = [v for v in year_closed_avg if q_start_m <= v.close_date.month <= q_end_m]
        q_days = [vac_days_map[v.id] for v in q_vacs]
        avg_d = round(sum(q_days) / len(q_days), 1) if q_days else 0
        avg_quarter_items.append({
            "label": f"Q{q}",
            "name": Q_NAMES[q - 1],
            "value": avg_d,
            "count": len(q_vacs),
        })

    yr_vacs = [v for v in year_closed_avg if v.close_date.month <= max_m]
    yr_days = [vac_days_map[v.id] for v in yr_vacs]
    avg_d_yr = round(sum(yr_days) / len(yr_days), 1) if yr_days else 0
    avg_year_items = [{
        "label": f"{target_year}",
        "name": f"{target_year} год",
        "value": avg_d_yr,
        "count": len(yr_vacs),
    }]

    chart_avg_days_timeline = {
        "month": avg_month_items,
        "quarter": avg_quarter_items,
        "year": avg_year_items,
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
    avail_status_names = {get_effective_status(v) for v in all_vacs if matches_filters(v, "status")}
    avail_status_names.discard(None)
    avail_statuses   = {sid for sid, name in status_map.items() if name in avail_status_names}
    filter_blocks         = _opts(block_map, avail_blocks)
    filter_projects       = _opts(project_map, avail_projects)
    filter_it_roles       = _opts(it_role_map, avail_it_roles)
    filter_levels         = _opts(level_map, avail_levels)
    filter_admin_managers = _opts(admin_mgr_map, avail_admin_mgrs)
    filter_recruiters     = [r for r in recruiters_opts if r["id"] in avail_recruiters]
    filter_statuses       = _opts(status_map, avail_statuses)

    vac_items = []
    for v in all_vacs:
        if matches_filters(v, "vacancy"):
            disp_id = str(v.vacancy_id).strip() if (v.vacancy_id and str(v.vacancy_id).strip()) else str(v.id)
            vac_items.append({"id": v.id, "disp": disp_id, "value": f"№{disp_id}"})

    def _vac_sort_key(item):
        try:
            return (0, int(item["disp"]))
        except ValueError:
            return (1, item["disp"])

    filter_vacancies = sorted(vac_items, key=_vac_sort_key)
    filter_vacancies = [{"id": x["id"], "value": x["value"]} for x in filter_vacancies]

    return {
        "chart1_source":           chart1,
        "chart2_open_closed":      chart2,
        "chart3_funnel":           chart3,
        "chart4_companies":        chart4,
        "chart5_avg_days":         chart5,
        "chart6_statuses":         chart6,
        "chart7_jo_rate":          chart7,
        "chart8_recruiter_load":   chart8,
        "chart_levels":            chart_levels,
        "chart_replacement":       chart_replacement,
        "chart_employment":        chart_employment,
        "chart_salaries":          chart_salaries,
        "chart_rejections":        chart_rejections,
        "chart_jo_conversion":     chart_jo_conversion,
        "chart_avg_days_timeline": chart_avg_days_timeline,
        "filters": {
            "blocks":         filter_blocks,
            "projects":       filter_projects,
            "it_roles":       filter_it_roles,
            "levels":         filter_levels,
            "admin_managers": filter_admin_managers,
            "recruiters":     filter_recruiters,
            "statuses":       filter_statuses,
            "vacancies":      filter_vacancies,
        },
    }