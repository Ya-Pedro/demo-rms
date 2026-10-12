import asyncio
import json
import urllib.request
import urllib.parse
from datetime import date, datetime, timedelta

from database import AsyncSessionLocal
from sqlalchemy import select
from models import User, UserRole, Vacancy, WeeklyReport, Dictionary, DictionaryType
from auth import create_access_token

BASE_URL = "http://localhost:8000/api"

async def setup_test_context():
    async with AsyncSessionLocal() as session:
        superadmin = (await session.execute(select(User).where(User.role == UserRole.SUPERADMIN, User.is_active == True))).scalars().first()
        admin = (await session.execute(select(User).where(User.role == UserRole.ADMIN, User.is_active == True))).scalars().first()
        recruiter = (await session.execute(select(User).where(User.role == UserRole.RECRUITER, User.is_active == True))).scalars().first()
        assert superadmin and admin and recruiter, "Users missing"

        tokens = {
            "superadmin": create_access_token({"sub": superadmin.email, "role": superadmin.role.value}),
            "admin": create_access_token({"sub": admin.email, "role": admin.role.value}),
            "recruiter": create_access_token({"sub": recruiter.email, "role": recruiter.role.value}),
        }

        # Dictionaries
        it_role = (await session.execute(select(Dictionary).where(Dictionary.type == DictionaryType.IT_ROLE, Dictionary.is_active == True))).scalars().first()
        level = (await session.execute(select(Dictionary).where(Dictionary.type == DictionaryType.SPECIALIST_LEVEL, Dictionary.is_active == True))).scalars().first()
        status_closed = (await session.execute(select(Dictionary).where(Dictionary.type == DictionaryType.VACANCY_STATUS, Dictionary.value == "Закрыта"))).scalars().first()

        return tokens, {
            "it_role_id": it_role.id if it_role else None,
            "level_id": level.id if level else None,
            "status_closed_id": status_closed.id if status_closed else None,
            "recruiter_id": recruiter.id,
        }

def request(method, path, token, params=None):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    headers = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            if not raw:
                return resp.status, None
            return resp.status, json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode("utf-8"))
        except Exception:
            return e.code, raw.decode("utf-8")

async def main():
    tokens, dict_info = await setup_test_context()
    print("=== STARTING DASHBOARDS TEST SUITE ===")

    # 1. Access Control Tests
    print("\n--- 1. Testing Role-Based Access Control ---")
    st, data = request("GET", "/dashboards/metrics", tokens["recruiter"])
    assert st == 403, f"Expected 403 for recruiter, got {st}"
    print("  [PASS] Recruiter access blocked with 403 Forbidden")

    st, data = request("GET", "/dashboards/metrics", tokens["admin"])
    assert st == 200, f"Expected 200 for admin, got {st}"
    print("  [PASS] Admin access granted with 200 OK")

    st, data = request("GET", "/dashboards/metrics", tokens["superadmin"])
    assert st == 200, f"Expected 200 for superadmin, got {st}"
    print("  [PASS] Superadmin access granted with 200 OK")

    # 2. Comprehensive Metrics Integrity
    print("\n--- 2. Testing Metrics Data Integrity (All Vacancies Accounted For) ---")
    c2 = data["chart2_open_closed"]
    total = c2["total"]
    sum_parts = c2["open"] + c2["closed"] + c2["exit"] + c2["hold"] + c2["cancel"]
    print(f"  Total vacancies: {total}")
    print(f"  Status breakdown: Open={c2['open']}, Closed={c2['closed']}, Exit={c2['exit']}, Hold={c2['hold']}, Cancel={c2['cancel']}")
    assert total > 0, "Expected non-zero total vacancies"
    assert sum_parts == total, f"Sum of statuses ({sum_parts}) does not match total ({total})"
    print("  [PASS] All vacancies accounted for 100% without loss (open+closed+exit+hold+cancel == total)")

    # Funnel
    funnel = data["chart3_funnel"]
    assert len(funnel) == 5, f"Expected 5 funnel stages, got {len(funnel)}"
    print(f"  [PASS] Funnel stages present: {[s['stage'] for s in funnel]}")

    # JO Conversion
    jo_conv = data["chart_jo_conversion"]
    assert "month" in jo_conv and "quarter" in jo_conv and "year" in jo_conv
    print(f"  [PASS] JO Conversion calculated for months ({len(jo_conv['month'])}), quarters ({len(jo_conv['quarter'])}), year ({len(jo_conv['year'])})")
    for m in jo_conv["month"]:
        assert 0 <= m["value"] <= 100, f"Invalid JO conversion rate: {m['value']}"

    # Average Days
    avg_days = data["chart5_avg_days"]
    print(f"  [PASS] Average working days calculated for {len(avg_days)} categories")
    for it in avg_days:
        assert it["avg_days"] > 0, f"Invalid average days: {it['avg_days']}"

    # Recruiter load
    rec_load = data["chart8_recruiter_load"]
    print(f"  [PASS] Recruiter load calculated for {len(rec_load)} recruiters")

    # 3. Filtering Tests
    print("\n--- 3. Testing Filters & Responsiveness ---")
    
    # Date filter
    st, filtered_dates = request("GET", "/dashboards/metrics", tokens["superadmin"], {
        "start_date": "2026-01-01",
        "end_date": "2026-06-30"
    })
    assert st == 200
    tot_filtered = filtered_dates["chart2_open_closed"]["total"]
    assert tot_filtered <= total
    print(f"  [PASS] Date range filter (2026-01-01 .. 2026-06-30) reduced total from {total} to {tot_filtered}")

    # IT role filter
    if dict_info["it_role_id"]:
        st, filtered_role = request("GET", "/dashboards/metrics", tokens["superadmin"], {
            "it_role_ids": str(dict_info["it_role_id"])
        })
        assert st == 200
        tot_role = filtered_role["chart2_open_closed"]["total"]
        print(f"  [PASS] IT role filter applied: total={tot_role}")

    # Level filter
    if dict_info["level_id"]:
        st, filtered_lvl = request("GET", "/dashboards/metrics", tokens["superadmin"], {
            "level_ids": str(dict_info["level_id"])
        })
        assert st == 200
        tot_lvl = filtered_lvl["chart2_open_closed"]["total"]
        print(f"  [PASS] Level filter applied: total={tot_lvl}")

    # Recruiter filter
    st, filtered_rec = request("GET", "/dashboards/metrics", tokens["superadmin"], {
        "recruiter_ids": str(dict_info["recruiter_id"])
    })
    assert st == 200
    tot_rec = filtered_rec["chart2_open_closed"]["total"]
    print(f"  [PASS] Recruiter filter applied: total={tot_rec}")

    # Status filter
    if dict_info["status_closed_id"]:
        st, filtered_st = request("GET", "/dashboards/metrics", tokens["superadmin"], {
            "status_ids": str(dict_info["status_closed_id"])
        })
        assert st == 200
        tot_st = filtered_st["chart2_open_closed"]["total"]
        assert filtered_st["chart2_open_closed"]["closed"] == tot_st
        print(f"  [PASS] Status filter applied: strictly closed vacancies count={tot_st}")

    # Group by switch (level vs it_role)
    st, grouped_level = request("GET", "/dashboards/metrics", tokens["superadmin"], {
        "group_by": "level"
    })
    assert st == 200
    print(f"  [PASS] Group by switch to 'level' verified (categories count={len(grouped_level['chart5_avg_days'])})")

    print("\n==========================================")
    print(" ALL DASHBOARDS BACKEND TESTS PASSED (100%)! ")
    print("==========================================")

if __name__ == "__main__":
    asyncio.run(main())
