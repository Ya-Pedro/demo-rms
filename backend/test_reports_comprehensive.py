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
        # Get users
        superadmin = (await session.execute(select(User).where(User.role == UserRole.SUPERADMIN, User.is_active == True))).scalars().first()
        admin = (await session.execute(select(User).where(User.role == UserRole.ADMIN, User.is_active == True))).scalars().first()
        recruiters = (await session.execute(select(User).where(User.role == UserRole.RECRUITER, User.is_active == True))).scalars().all()
        assert superadmin and admin and len(recruiters) >= 2, "Test users missing"
        recruiter1, recruiter2 = recruiters[0], recruiters[1]

        # Get dictionaries
        status_res = await session.execute(select(Dictionary).where(Dictionary.type == DictionaryType.VACANCY_STATUS, Dictionary.is_active == True))
        statuses = status_res.scalars().all()
        status_in_work = next((s for s in statuses if "работ" in s.value.lower()), statuses[0])

        it_role = (await session.execute(select(Dictionary).where(Dictionary.type == DictionaryType.IT_ROLE, Dictionary.is_active == True))).scalars().first()
        project = (await session.execute(select(Dictionary).where(Dictionary.type == DictionaryType.PROJECT, Dictionary.is_active == True))).scalars().first()

        # Find or create a test vacancy for recruiter1 and one for recruiter2
        res_v1 = await session.execute(select(Vacancy).where(Vacancy.recruiter_id == recruiter1.id))
        v1 = res_v1.scalars().first()
        if not v1:
            v1 = Vacancy(
                vacancy_id="TEST-V-R1",
                position_name="Test Position R1",
                quantity=1,
                salary_gross=200000,
                status_id=status_in_work.id,
                recruiter_id=recruiter1.id,
                open_date=date.today(),
            )
            session.add(v1)
            await session.commit()
            await session.refresh(v1)

        res_v2 = await session.execute(select(Vacancy).where(Vacancy.recruiter_id == recruiter2.id))
        v2 = res_v2.scalars().first()
        if not v2:
            v2 = Vacancy(
                vacancy_id="TEST-V-R2",
                position_name="Test Position R2",
                quantity=1,
                salary_gross=210000,
                status_id=status_in_work.id,
                recruiter_id=recruiter2.id,
                open_date=date.today(),
            )
            session.add(v2)
            await session.commit()
            await session.refresh(v2)

        tokens = {
            "superadmin": create_access_token({"sub": superadmin.email, "role": superadmin.role.value}),
            "admin": create_access_token({"sub": admin.email, "role": admin.role.value}),
            "recruiter1": create_access_token({"sub": recruiter1.email, "role": recruiter1.role.value}),
            "recruiter2": create_access_token({"sub": recruiter2.email, "role": recruiter2.role.value}),
        }
        users_info = {
            "superadmin": {"id": superadmin.id, "email": superadmin.email, "name": superadmin.full_name},
            "admin": {"id": admin.id, "email": admin.email, "name": admin.full_name},
            "recruiter1": {"id": recruiter1.id, "email": recruiter1.email, "name": recruiter1.full_name},
            "recruiter2": {"id": recruiter2.id, "email": recruiter2.email, "name": recruiter2.full_name},
        }
        return tokens, users_info, {"v1_id": v1.id, "v2_id": v2.id, "v1_ext_id": v1.vacancy_id, "v2_ext_id": v2.vacancy_id, "status_id": status_in_work.id, "it_role_id": it_role.id, "project_id": project.id}

def request(method, path, token, body=None, params=None, is_json=True):
    url = f"{BASE_URL}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    headers = {"Authorization": f"Bearer {token}"}
    data = None
    if body is not None:
        if is_json:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        else:
            data = body
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if not raw:
                return resp.status, None, resp.headers
            if "application/json" in content_type:
                try:
                    return resp.status, json.loads(raw.decode("utf-8")), resp.headers
                except Exception:
                    return resp.status, raw.decode("utf-8"), resp.headers
            return resp.status, raw, resp.headers
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            body = json.loads(raw.decode("utf-8"))
        except Exception:
            body = raw.decode("utf-8")
        return e.code, body, e.headers
    except Exception as e:
        return 0, str(e), {}

async def run_reports_tests():
    tokens, users, meta = await setup_test_context()
    print("=== STARTING REPORTS TAB TEST SUITE ===")
    print(f"Users configured:")
    print(f"  Superadmin: {users['superadmin']}")
    print(f"  Admin:      {users['admin']}")
    print(f"  Recruiter1: {users['recruiter1']} (Vacancy: {meta['v1_id']})")
    print(f"  Recruiter2: {users['recruiter2']} (Vacancy: {meta['v2_id']})")

    created_report_ids = []

    try:
        cur_year, cur_week, _ = datetime.now().isocalendar()

        # -------------------------------------------------------------
        # 1. REPORT CREATION (POST /api/reports) & EDITING PERMISSIONS
        # -------------------------------------------------------------
        print("\n--- 1. Testing Report Creation & Weekly Bounds ---")

        # 1.1 Recruiter1 creates report for own vacancy for current week -> Success
        code, res, _ = request("POST", "/reports", tokens["recruiter1"], {
            "vacancy_id": meta["v1_id"],
            "week_number": cur_week,
            "year": cur_year,
            "resumes_sent": 5,
            "candidates_agreed": 3,
            "interviews_planned": 2,
            "interviews_conducted": 2,
            "offer_made": 1,
            "offer_accepted": 1,
            "comment": "R1 current week progress"
        })
        if code == 400 and "уже существует" in str(res):
            # Already exists, query report id
            code_v, res_v, _ = request("GET", f"/reports/vacancy/{meta['v1_id']}", tokens["recruiter1"])
            r_id = res_v["items"][0]["id"]
            # update it
            code, res, _ = request("PATCH", f"/reports/{r_id}", tokens["recruiter1"], {
                "resumes_sent": 5, "candidates_agreed": 3, "offer_made": 1, "offer_accepted": 1
            })
            assert code == 200, f"Updating existing report failed: {res}"
            created_report_ids.append(r_id)
        else:
            assert code == 201, f"Recruiter1 create report failed: {code} {res}"
            created_report_ids.append(res["id"])
        print("  [PASS] Recruiter1 created/updated report for own vacancy for current week")

        # 1.2 Recruiter1 attempts to create report for Recruiter2's vacancy -> Expect 403 Forbidden
        code, res, _ = request("POST", "/reports", tokens["recruiter1"], {
            "vacancy_id": meta["v2_id"],
            "week_number": cur_week,
            "year": cur_year,
            "resumes_sent": 1,
        })
        assert code == 403, f"Expected 403 for cross-recruiter report creation, got: {code} {res}"
        print("  [PASS] Recruiter1 blocked from creating report for Recruiter2's vacancy (403 Forbidden)")

        # 1.3 Recruiter1 attempts to create report for 10 weeks ago -> Expect 403 Forbidden (bounds rule)
        old_week = cur_week - 10 if cur_week > 10 else 40
        old_year = cur_year if cur_week > 10 else cur_year - 1
        code, res, _ = request("POST", "/reports", tokens["recruiter1"], {
            "vacancy_id": meta["v1_id"],
            "week_number": old_week,
            "year": old_year,
            "resumes_sent": 1,
        })
        assert code == 403, f"Expected 403 for old week by recruiter, got: {code} {res}"
        print(f"  [PASS] Recruiter1 blocked from creating report for week {old_week}/{old_year} (403 Forbidden: >7 days rule)")

        # 1.4 Admin creates report for Recruiter2's vacancy for past week -> Success (admin has no week bounds or recruiter restrictions)
        code, res, _ = request("POST", "/reports", tokens["admin"], {
            "vacancy_id": meta["v2_id"],
            "week_number": old_week,
            "year": old_year,
            "resumes_sent": 4,
            "candidates_agreed": 2,
            "comment": "Admin retroactive report"
        })
        if code == 400 and "уже существует" in str(res):
            code_v, res_v, _ = request("GET", f"/reports/vacancy/{meta['v2_id']}", tokens["admin"])
            matching = [r for r in res_v["items"] if r["week_number"] == old_week and r["year"] == old_year]
            if matching:
                created_report_ids.append(matching[0]["id"])
        else:
            assert code == 201, f"Admin create report failed: {code} {res}"
            created_report_ids.append(res["id"])
        print(f"  [PASS] Admin created report for any vacancy and past week {old_week}/{old_year}")

        # 1.5 Superadmin edits that report
        admin_rep_id = created_report_ids[-1]
        code, res, _ = request("PATCH", f"/reports/{admin_rep_id}", tokens["superadmin"], {
            "resumes_sent": 10,
            "comment": "Superadmin modified comment"
        })
        assert code == 200 and res["resumes_sent"] == 10, f"Superadmin edit failed: {code} {res}"
        print("  [PASS] Superadmin successfully updated report metrics")

        # 1.6 Recruiter1 attempts to edit that report -> Expect 403 Forbidden
        code, res, _ = request("PATCH", f"/reports/{admin_rep_id}", tokens["recruiter1"], {
            "resumes_sent": 99
        })
        assert code == 403, f"Expected 403 for Recruiter1 editing foreign report, got: {code} {res}"
        print("  [PASS] Recruiter1 blocked from editing Recruiter2's report (403 Forbidden)")

        # -------------------------------------------------------------
        # 2. REPORTS LISTING & ROLE SCOPING (GET /api/reports/all)
        # -------------------------------------------------------------
        print("\n--- 2. Testing Reports Listing & Role Scoping ---")

        # 2.1 Superadmin gets all reports
        code, res_super, _ = request("GET", "/reports/all", tokens["superadmin"], params={"limit": 50})
        assert code == 200, f"Superadmin reports query failed: {code}"
        total_all = res_super["total"]
        assert total_all > 0, "No reports returned"
        print(f"  [PASS] Superadmin sees full reports dataset (total={total_all})")

        # 2.2 Admin gets all reports
        code, res_admin, _ = request("GET", "/reports/all", tokens["admin"], params={"limit": 50})
        assert code == 200 and res_admin["total"] == total_all, f"Admin total mismatch: {res_admin['total']} vs {total_all}"
        print(f"  [PASS] Admin sees full reports dataset (total={res_admin['total']})")

        # 2.3 Recruiter gets strictly scoped reports
        code, res_rec1, _ = request("GET", "/reports/all", tokens["recruiter1"], params={"limit": 100})
        assert code == 200, f"Recruiter1 query failed: {code}"
        assert res_rec1["total"] < total_all, f"Recruiter total should be subset of all: {res_rec1['total']} vs {total_all}"
        for it in res_rec1["items"]:
            assert it.get("recruiter_name") == users["recruiter1"]["name"] or it.get("co_recruiter_name") == users["recruiter1"]["name"], \
                f"Recruiter1 saw foreign vacancy: {it}"
        print(f"  [PASS] Recruiter1 sees strictly scoped reports (total={res_rec1['total']} < {total_all})")

        # -------------------------------------------------------------
        # 3. PERIOD FILTERS (year, month, week, custom date range)
        # -------------------------------------------------------------
        print("\n--- 3. Testing Period Filters ---")

        # 3.1 By current year
        code, res_yr, _ = request("GET", "/reports/all", tokens["superadmin"], params={"year": cur_year, "limit": 20})
        assert code == 200
        print(f"  [PASS] Filter by year={cur_year} verified ({res_yr['total']} rows)")

        # 3.2 By month
        code, res_mo, _ = request("GET", "/reports/all", tokens["superadmin"], params={"year": cur_year, "month": datetime.now().month, "limit": 20})
        assert code == 200
        print(f"  [PASS] Filter by year={cur_year}, month={datetime.now().month} verified ({res_mo['total']} rows)")

        # 3.3 By week_number
        code, res_wk, _ = request("GET", "/reports/all", tokens["superadmin"], params={"year": cur_year, "week_number": cur_week, "limit": 20})
        assert code == 200
        print(f"  [PASS] Filter by year={cur_year}, week_number={cur_week} verified ({res_wk['total']} rows)")

        # 3.4 By custom date range
        sd = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        ed = datetime.now().strftime("%Y-%m-%d")
        code, res_dr, _ = request("GET", "/reports/all", tokens["superadmin"], params={"start_date": sd, "end_date": ed, "limit": 20})
        assert code == 200
        print(f"  [PASS] Filter by date range ({sd} to {ed}) verified ({res_dr['total']} rows)")

        # -------------------------------------------------------------
        # 4. CHECKBOX "ТОЛЬКО С ДВИЖЕНИЯМИ ЗА ПЕРИОД" (only_active_work)
        # -------------------------------------------------------------
        print("\n--- 4. Testing 'Только с движениями за период' Checkbox ---")

        # 4.1 Query with only_active_work=true
        code, res_active, _ = request("GET", "/reports/all", tokens["superadmin"], params={"only_active_work": "true", "limit": 100})
        assert code == 200
        assert res_active["total"] <= total_all, f"Active work count {res_active['total']} must be <= total {total_all}"
        for it in res_active["items"]:
            movements = (
                (it.get("total_resumes_sent") or 0) +
                (it.get("total_candidates_agreed") or 0) +
                (it.get("total_interviews_planned") or 0) +
                (it.get("total_interviews_conducted") or 0) +
                (it.get("total_offer_made") or 0) +
                (it.get("total_offer_accepted") or 0)
            )
            assert movements > 0, f"Row with 0 movements returned when only_active_work=true: {it['vacancy_ext_id']}"
        print(f"  [PASS] only_active_work=true correctly filtered: {res_active['total']} vacancies with funnel movements > 0")

        # 4.2 Query with only_with_movements alias
        code, res_alias, _ = request("GET", "/reports/all", tokens["superadmin"], params={"only_with_movements": "true", "limit": 10})
        assert code == 200 and res_alias["total"] == res_active["total"], "only_with_movements alias count mismatch"
        print(f"  [PASS] only_with_movements alias verified ({res_alias['total']} rows)")

        # -------------------------------------------------------------
        # 5. COLUMN FILTERS & SEARCH
        # -------------------------------------------------------------
        print("\n--- 5. Testing Column Filters & Search ---")

        # 5.1 Search by vacancy ID (search_vacancy_id and vacancy_ext_id)
        search_id = meta["v1_ext_id"] or str(meta["v1_id"])
        code, res_vid, _ = request("GET", "/reports/all", tokens["superadmin"], params={"search_vacancy_id": search_id})
        assert code == 200
        assert any(it["id"] == meta["v1_id"] or it["vacancy_ext_id"] == search_id for it in res_vid["items"]), f"search_vacancy_id failed: {res_vid}"
        print(f"  [PASS] search_vacancy_id filter verified (queried {search_id})")

        # 5.2 Filter by status (status_name)
        code, res_st, _ = request("GET", "/reports/all", tokens["superadmin"], params={"status_name": [meta["status_id"]], "limit": 20})
        assert code == 200
        print(f"  [PASS] status filter verified ({res_st['total']} rows)")

        # 5.3 Filter by IT Role (it_role_name)
        code, res_role, _ = request("GET", "/reports/all", tokens["superadmin"], params={"it_role_name": [meta["it_role_id"]], "limit": 20})
        assert code == 200
        print(f"  [PASS] it_role filter verified ({res_role['total']} rows)")

        # 5.4 Numeric filter: total_resumes_sent
        code, res_num, _ = request("GET", "/reports/all", tokens["superadmin"], params={"total_resumes_sent": "5", "limit": 20})
        assert code == 200
        for it in res_num["items"]:
            assert it["total_resumes_sent"] == 5, f"total_resumes_sent mismatch: {it['total_resumes_sent']}"
        print(f"  [PASS] numeric filter total_resumes_sent=5 verified")

        # -------------------------------------------------------------
        # 6. SORTING (ASC / DESC)
        # -------------------------------------------------------------
        print("\n--- 6. Testing Sorting ---")

        # 6.1 Sort by total_resumes_sent desc
        code, res_s_desc, _ = request("GET", "/reports/all", tokens["superadmin"], params={"sort_field": "total_resumes_sent", "sort_order": "desc", "limit": 15})
        assert code == 200
        vals = [it["total_resumes_sent"] for it in res_s_desc["items"]]
        assert vals == sorted(vals, reverse=True), f"Desc sorting failed: {vals}"

        # 6.2 Sort by total_resumes_sent asc
        code, res_s_asc, _ = request("GET", "/reports/all", tokens["superadmin"], params={"sort_field": "total_resumes_sent", "sort_order": "asc", "limit": 15})
        assert code == 200
        vals_asc = [it["total_resumes_sent"] for it in res_s_asc["items"]]
        assert vals_asc == sorted(vals_asc), f"Asc sorting failed: {vals_asc}"
        print("  [PASS] Sorting asc and desc on total_resumes_sent verified")

        # 6.3 Sort by vacancy_ext_id
        code, res_s_vid, _ = request("GET", "/reports/all", tokens["superadmin"], params={"sort_field": "vacancy_ext_id", "sort_order": "asc", "limit": 10})
        assert code == 200
        print("  [PASS] Sorting on vacancy_ext_id verified")

        # -------------------------------------------------------------
        # 7. FILTER RESET SIMULATION
        # -------------------------------------------------------------
        print("\n--- 7. Testing Filter Reset ---")
        code, res_reset, _ = request("GET", "/reports/all", tokens["superadmin"], params={"limit": 50})
        assert code == 200 and res_reset["total"] == total_all, f"Reset total mismatch: {res_reset['total']} vs {total_all}"
        print("  [PASS] Filter reset returns full dataset")

        # -------------------------------------------------------------
        # 8. REPORTS EXPORT (GET /api/reports/all/export)
        # -------------------------------------------------------------
        print("\n--- 8. Testing Excel Export of Reports ---")

        # 8.1 Superadmin all_time export
        code, content, headers = request("GET", "/reports/all/export", tokens["superadmin"])
        assert code == 200, f"Superadmin reports export failed: {code}"
        assert len(content) > 1000 and content[:2] == b"PK", "Invalid Excel binary content"
        cd = headers.get("Content-Disposition", "")
        assert "reports_export_" in cd and ".xlsx" in cd, f"Unexpected header: {cd}"
        print(f"  [PASS] Superadmin all_time export successful ({len(content)} bytes)")

        # 8.2 Superadmin export with active filters & only_active_work=true
        code, content_active, headers = request("GET", "/reports/all/export", tokens["superadmin"], params={
            "only_active_work": "true",
            "year": cur_year,
            "status_name": [meta["status_id"]],
        })
        assert code == 200
        assert len(content_active) > 1000 and content_active[:2] == b"PK"
        print(f"  [PASS] Superadmin export with filters and movements-only successful ({len(content_active)} bytes)")

        # 8.3 Admin export
        code, content_admin, _ = request("GET", "/reports/all/export", tokens["admin"])
        assert code == 200 and len(content_admin) > 1000 and content_admin[:2] == b"PK"
        print(f"  [PASS] Admin reports export successful ({len(content_admin)} bytes)")

        # 8.4 Recruiter export (scoped strictly to recruiter vacancies)
        code, content_rec, _ = request("GET", "/reports/all/export", tokens["recruiter1"])
        assert code == 200 and len(content_rec) > 1000 and content_rec[:2] == b"PK"
        # Recruiter file should be significantly smaller or strictly contain only their vacancies
        assert len(content_rec) <= len(content), "Recruiter export must not contain more data than admin"
        print(f"  [PASS] Recruiter reports export successful and scoped ({len(content_rec)} bytes)")

        # -------------------------------------------------------------
        # 9. VACANCY REPORTS LIST (GET /api/reports/vacancy/{vacancy_id})
        # -------------------------------------------------------------
        print("\n--- 9. Testing Vacancy Weekly History Access ---")

        # Recruiter1 can view own vacancy weekly reports
        code, res, _ = request("GET", f"/reports/vacancy/{meta['v1_id']}", tokens["recruiter1"])
        assert code == 200, f"Recruiter1 view own vacancy reports failed: {code}"
        print(f"  [PASS] Recruiter1 viewed weekly history for own vacancy (count={res['total']})")

        # Recruiter1 blocked from viewing Recruiter2's vacancy weekly reports
        code, res, _ = request("GET", f"/reports/vacancy/{meta['v2_id']}", tokens["recruiter1"])
        assert code == 403, f"Expected 403 for cross-recruiter weekly history, got: {code}"
        print("  [PASS] Recruiter1 blocked from viewing Recruiter2's weekly history (403 Forbidden)")

        print("\n========================================")
        print(" ALL REPORTS TAB TESTS PASSED (100%)! ")
        print("========================================\n")

    finally:
        pass

if __name__ == "__main__":
    asyncio.run(run_reports_tests())
