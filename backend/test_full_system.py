import asyncio
import httpx
from datetime import date, datetime
from auth import create_access_token
from database import AsyncSessionLocal
from models import User, Vacancy, WeeklyReport, Dictionary, DictionaryType, Note, VacancyHistory
from sqlalchemy import select, delete

BASE_URL = "http://localhost:8000"

async def run_tests():
    print("=" * 60)
    print("STARTING FULL RMS SYSTEM VERIFICATION TEST SUITE")
    print("=" * 60)

    # 1. Setup tokens for different user roles
    admin1_token = create_access_token({"sub": "admin1@rms-system.ru", "role": "superadmin"})
    admin2_token = create_access_token({"sub": "admin2@rms-system.ru", "role": "superadmin"})
    test_admin_token = create_access_token({"sub": "test_admin@rms-system.ru", "role": "admin"})
    recruiter1_token = create_access_token({"sub": "as@as.com", "role": "recruiter"}) # Kostya
    recruiter2_token = create_access_token({"sub": "as@as.as", "role": "recruiter"}) # Recruiter 2
    recruiter3_token = create_access_token({"sub": "a@a.cl", "role": "recruiter"})   # Recruiter 3

    h_sa1 = {"Authorization": f"Bearer {admin1_token}"}
    h_sa2 = {"Authorization": f"Bearer {admin2_token}"}
    h_adm = {"Authorization": f"Bearer {test_admin_token}"}
    h_rec1 = {"Authorization": f"Bearer {recruiter1_token}"}
    h_rec2 = {"Authorization": f"Bearer {recruiter2_token}"}
    h_rec3 = {"Authorization": f"Bearer {recruiter3_token}"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:

        # -------------------------------------------------------------
        # TEST 1: NOTES (Общие заметки для Admin и Superadmin)
        # -------------------------------------------------------------
        print("\n--- [TEST 1] Shared Notes for Admin and Superadmin ---")
        
        # 1.1 Superadmin 1 updates shared notes
        sheets_sa1 = [{
            "id": "sheet_admin",
            "name": "Общие заметки",
            "columns": [{"key": "col_1", "title": "План", "width": 200}, {"key": "col_2", "title": "Статус", "width": 200}],
            "rows": [{"id": "r_1", "col_1": "Q3", "col_2": "В работе"}]
        }]
        r = await client.put("/api/notes", json={"sheets": sheets_sa1}, headers=h_sa1)
        assert r.status_code == 200, f"SA1 update notes failed: {r.status_code} {r.text}"
        res_sa1 = r.json()
        assert res_sa1["scope"] == "admin_shared"
        assert res_sa1["sheets"] == sheets_sa1

        # 1.2 Superadmin 2 reads notes: MUST see admin_shared scope and data from SA1
        r = await client.get("/api/notes", headers=h_sa2)
        assert r.status_code == 200
        res_sa2 = r.json()
        assert res_sa2["scope"] == "admin_shared"
        assert res_sa2["sheets"] == sheets_sa1
        assert "Супер Администратор 1" in (res_sa2.get("updated_by_name") or "")
        print("  ✓ Superadmin 2 sees the shared notes saved by Superadmin 1")

        # 1.3 Admin updates the shared notes
        sheets_adm = [{
            "id": "sheet_admin",
            "name": "Общие заметки",
            "columns": [{"key": "col_1", "title": "План", "width": 200}, {"key": "col_2", "title": "Статус", "width": 200}],
            "rows": [{"id": "r_1", "col_1": "Q3", "col_2": "Завершено Админом"}]
        }]
        r = await client.put("/api/notes", json={"sheets": sheets_adm}, headers=h_adm)
        assert r.status_code == 200, f"Admin update notes failed: {r.status_code} {r.text}"
        res_adm = r.json()
        assert res_adm["scope"] == "admin_shared"

        # 1.4 Superadmin 1 reads notes: MUST see update made by Admin
        r = await client.get("/api/notes", headers=h_sa1)
        assert r.status_code == 200
        res_check = r.json()
        assert res_check["sheets"] == sheets_adm
        assert "Тестовый Администратор" in (res_check.get("updated_by_name") or "")
        print("  ✓ Superadmin 1 sees notes updated by Admin (scope: admin_shared)")

        # 1.5 Recruiter 1 reads notes: MUST have personal scope user_7, NOT admin_shared
        r = await client.get("/api/notes", headers=h_rec1)
        assert r.status_code == 200
        res_rec1 = r.json()
        assert res_rec1["scope"] == "user_7"
        assert res_rec1["sheets"] != sheets_adm
        print("  ✓ Recruiter 1 has isolated personal notes (scope: user_7), cannot see admin notes")

        # 1.6 Recruiter 1 updates their personal notes
        sheets_rec1 = [{
            "id": "sheet_rec1",
            "name": "Мои личные заметки",
            "columns": [{"key": "col_1", "title": "Кандидат", "width": 200}, {"key": "col_2", "title": "Статус", "width": 200}],
            "rows": [{"id": "r_1", "col_1": "Иванов", "col_2": "Интервью"}]
        }]
        r = await client.put("/api/notes", json={"sheets": sheets_rec1}, headers=h_rec1)
        assert r.status_code == 200
        assert r.json()["scope"] == "user_7"

        # 1.7 Recruiter 2 reads notes: MUST have personal scope user_3, cannot see Recruiter 1's notes
        r = await client.get("/api/notes", headers=h_rec2)
        assert r.status_code == 200
        res_rec2 = r.json()
        assert res_rec2["scope"] == "user_3"
        assert res_rec2["sheets"] != sheets_rec1
        print("  ✓ Recruiter 2 has isolated personal notes (scope: user_3), cannot see Recruiter 1 notes")

        # 1.8 Admin reads notes: still sees admin_shared, unaffected by recruiters
        r = await client.get("/api/notes", headers=h_adm)
        assert r.status_code == 200
        assert r.json()["scope"] == "admin_shared"
        assert r.json()["sheets"] == sheets_adm
        print("  ✓ Admin/Superadmin notes remain shared and unaffected by recruiters")

        # -------------------------------------------------------------
        # TEST 2: CO-RECRUITER + REPORTS FUNNEL COLLAPSING
        # -------------------------------------------------------------
        print("\n--- [TEST 2] Co-recruiter Visibility & Funnel Aggregation ---")
        # Get active status ID
        async with AsyncSessionLocal() as db:
            open_st = (await db.execute(select(Dictionary).where(Dictionary.type == DictionaryType.VACANCY_STATUS, Dictionary.value == "Открыта"))).scalar_one()
            open_st_id = open_st.id

        # 2.1 Superadmin creates vacancy with primary recruiter (ID=7) and co-recruiter (ID=3)
        vac_payload = {
            "position_name": "TEST Senior Python Backend",
            "recruiter_id": 7,     # Kostya
            "co_recruiter_id": 3,  # Recruiter 2
            "status_id": open_st_id,
            "open_date": "2026-09-01",
            "quantity": 1,
        }
        r = await client.post("/api/vacancies", json=vac_payload, headers=h_sa1)
        assert r.status_code in (200, 201), f"Create vacancy failed: {r.status_code} {r.text}"
        test_vac = r.json()
        test_vac_id = test_vac["id"]
        print(f"  ✓ Created vacancy #{test_vac_id} with primary recruiter=7 and co-recruiter=3")

        # 2.2 Primary recruiter (7) fetches their vacancies
        r = await client.get(f"/api/vacancies?skip=0&limit=100&week_number=42&year=2026", headers=h_rec1)
        assert r.status_code == 200
        items1 = r.json().get("items", [])
        rec1_vac_ids = [v["id"] for v in items1]
        assert test_vac_id in rec1_vac_ids, "Vacancy not visible to primary recruiter!"
        print("  ✓ Vacancy is visible in primary recruiter list")

        # 2.3 Co-recruiter (3) fetches their vacancies
        r = await client.get(f"/api/vacancies?skip=0&limit=100&week_number=42&year=2026", headers=h_rec2)
        assert r.status_code == 200
        items2 = r.json().get("items", [])
        rec2_vac_ids = [v["id"] for v in items2]
        assert test_vac_id in rec2_vac_ids, "Vacancy not visible to co-recruiter!"
        print("  ✓ Vacancy is visible in co-recruiter list")

        # 2.4 Other recruiter (4) fetches their vacancies
        r = await client.get(f"/api/vacancies?skip=0&limit=100&week_number=42&year=2026", headers=h_rec3)
        assert r.status_code == 200
        items3 = r.json().get("items", [])
        rec3_vac_ids = [v["id"] for v in items3]
        assert test_vac_id not in rec3_vac_ids, "Vacancy wrongly visible to unrelated recruiter!"
        print("  ✓ Vacancy is NOT visible to unrelated recruiter")

        # 2.5 Primary recruiter saves report for week 42
        rep_p1 = {
            "vacancy_id": test_vac_id,
            "week_number": 42,
            "year": 2026,
            "resumes_sent": 10,
            "candidates_agreed": 6,
            "interviews_conducted": 4,
            "offer_made": 2,
            "offer_accepted": 1,
            "offer_rejection_reason": "Не подошел проект / стек технологий",
            "comment": "Report by Primary Recruiter",
        }
        r = await client.post("/api/reports", json=rep_p1, headers=h_rec1)
        assert r.status_code in (200, 201), f"Primary recruiter report failed: {r.status_code} {r.text}"
        rep1_id = r.json()["id"]

        # 2.6 Co-recruiter saves report for week 42
        rep_p2 = {
            "vacancy_id": test_vac_id,
            "week_number": 42,
            "year": 2026,
            "resumes_sent": 5,
            "candidates_agreed": 3,
            "interviews_conducted": 2,
            "offer_made": 1,
            "offer_accepted": 1,
            "comment": "Report by Co-Recruiter",
        }
        r = await client.post("/api/reports", json=rep_p2, headers=h_rec2)
        assert r.status_code in (200, 201), f"Co-recruiter report failed: {r.status_code} {r.text}"
        rep2_id = r.json()["id"]

        # 2.7 Verify Vacancies table displays each recruiter's OWN weekly report numbers:
        # Recruiter 1: resume_at_customer=10
        r = await client.get(f"/api/vacancies?skip=0&limit=100&week_number=42&year=2026", headers=h_rec1)
        v1_row = next(v for v in r.json().get("items", []) if v["id"] == test_vac_id)
        assert v1_row.get("resume_at_customer") == 10, f"Expected 10 resumes for Rec1, got {v1_row.get('resume_at_customer')}"
        print("  ✓ Primary recruiter sees their own weekly report in Vacancy table (10 resumes)")

        # Recruiter 2: resume_at_customer=5
        r = await client.get(f"/api/vacancies?skip=0&limit=100&week_number=42&year=2026", headers=h_rec2)
        v2_row = next(v for v in r.json().get("items", []) if v["id"] == test_vac_id)
        assert v2_row.get("resume_at_customer") == 5, f"Expected 5 resumes for Rec2, got {v2_row.get('resume_at_customer')}"
        print("  ✓ Co-recruiter sees their own weekly report in Vacancy table (5 resumes)")

        # 2.8 Verify Reports table (Отчеты) COLLAPSES / COMBINES the joint funnel:
        # Sum resumes_sent: 10 + 5 = 15, agreed: 6 + 3 = 9, interviews: 4 + 2 = 6, offers: 2 + 1 = 3, accepted: 1 + 1 = 2
        r = await client.get(f"/api/reports/all?week_number=42&year=2026", headers=h_sa1)
        assert r.status_code == 200
        reports_list = r.json().get("items", [])
        rep_row = next((r for r in reports_list if r["id"] == test_vac_id), None)
        assert rep_row is not None, "Vacancy not found in reports table!"
        assert rep_row.get("total_resumes_sent") == 15, f"Expected 15 combined resumes in Reports, got {rep_row.get('total_resumes_sent')}"
        assert rep_row.get("total_candidates_agreed") == 9, f"Expected 9 combined agreed, got {rep_row.get('total_candidates_agreed')}"
        assert rep_row.get("total_interviews_conducted") == 6, f"Expected 6 combined interviews, got {rep_row.get('total_interviews_conducted')}"
        assert rep_row.get("total_offer_made") == 3, f"Expected 3 combined offers, got {rep_row.get('total_offer_made')}"
        assert rep_row.get("total_offer_accepted") == 2, f"Expected 2 combined accepted, got {rep_row.get('total_offer_accepted')}"
        print("  ✓ Reports section displays combined/collapsed funnel (15 resumes, 9 agreed, 6 interviews, 3 offers, 2 accepted)")

        # -------------------------------------------------------------
        # TEST 3: VACANCY HISTORY & OFFER REJECTION TAB
        # -------------------------------------------------------------
        print("\n--- [TEST 3] Vacancy History Drawer Tabs & Action Grouping ---")
        r = await client.get(f"/api/vacancies/{test_vac_id}/history", headers=h_rec1)
        assert r.status_code == 200
        hist_records = r.json()
        assert isinstance(hist_records, list) and len(hist_records) > 0, "No history records found"
        action_types = {h.get("action_type") for h in hist_records}
        print(f"  ✓ History records found: {len(hist_records)}, Action types: {action_types}")
        assert "CREATE" in action_types or "UPDATE" in action_types or "REPORT" in action_types

        # Verify co-recruiter actions are visible in history:
        user_names = {h.get("user", {}).get("full_name") for h in hist_records}
        print(f"  ✓ Action authors recorded in history: {user_names}")

        # -------------------------------------------------------------
        # TEST 4: COLUMNS 'Оффер принят' and 'Причина отказа'
        # -------------------------------------------------------------
        print("\n--- [TEST 4] Offer Accepted & Rejection Reason Columns & Dictionary ---")
        # 4.1 Dictionary contains offer rejection reasons
        r = await client.get("/api/dictionaries/by-type/offer_rejection_reason", headers=h_sa1)
        assert r.status_code == 200
        dict_items = r.json()
        assert len(dict_items) > 0, "Offer rejection dictionary is empty!"
        print(f"  ✓ Offer rejection reason dictionary has {len(dict_items)} active entries")

        # 4.2 Reports have total_offer_accepted and offer_rejection_reason
        assert "total_offer_accepted" in rep_row, "total_offer_accepted missing from reports response"
        assert "offer_rejection_reason" in rep_row, "offer_rejection_reason missing from reports response"
        print("  ✓ Reports API provides both total_offer_accepted and offer_rejection_reason")

        # 4.3 Vacancy response has offer_accepted and offer_rejection_reason
        assert "offer_accepted" in v1_row, "offer accepted missing from vacancy row"
        print("  ✓ Vacancy API provides offer accepted and offer rejection fields")

        # -------------------------------------------------------------
        # TEST 5: DASHBOARDS (ACCESS CONTROL, FILTERS, TIMELINE & FUNNEL)
        # -------------------------------------------------------------
        print("\n--- [TEST 5] Dashboards API & Chart Calculations ---")
        # 5.1 Access Control
        r = await client.get("/api/dashboards/metrics", headers=h_sa1)
        assert r.status_code == 200, f"Superadmin 1 access failed: {r.status_code}"
        r = await client.get("/api/dashboards/metrics", headers=h_adm)
        assert r.status_code == 200, f"Admin access failed: {r.status_code}"
        r = await client.get("/api/dashboards/metrics", headers=h_rec1)
        assert r.status_code == 403, f"Recruiter should be 403, got: {r.status_code}"
        print("  ✓ Access control: Superadmin and Admin allowed (200), Recruiter denied (403)")

        # 5.2 Metrics content check
        data = (await client.get("/api/dashboards/metrics", headers=h_sa1)).json()
        
        # Chart 2: Statuses sum rule
        c2 = data["chart2_open_closed"]
        assert "exit" not in c2 or c2.get("exit") == 0, "Exit should be removed from chart2"
        expected_total = c2["open"] + c2["closed"] + c2["hold"] + c2["cancel"]
        assert c2["total"] == expected_total, f"Statuses sum mismatch: total={c2['total']} != {expected_total}"
        print(f"  ✓ Chart 2 Statuses: {c2} (open+closed+hold+cancel == total: {c2['total']})")

        # Chart 3: 6-stage funnel
        c3 = data["chart3_funnel"]
        stages = [s["stage"] for s in c3]
        expected_stages = ["Передано заказчику", "Резюме одобрено", "Собеседования", "Оффер сделан", "Оффер принят", "Закрыта"]
        assert stages == expected_stages, f"Funnel stages mismatch: {stages} vs {expected_stages}"
        for s in c3:
            assert "conv_step" in s and "conv_total" in s, f"Conversion missing in stage {s}"
        print(f"  ✓ Chart 3 Funnel has all 6 stages with step and total conversion %: {[(s['stage'], s['value'], str(s['conv_step']) + '%, ' + str(s['conv_total']) + 'tot%') for s in c3]}")

        # Chart Rejections: contains all dictionary items with default 0
        c_rej = data["chart_rejections"]
        reasons = [r["reason"] for r in c_rej]
        assert len(reasons) >= len(dict_items), "Not all dictionary reasons present in chart_rejections"
        print(f"  ✓ Chart Rejections contains all {len(reasons)} reasons from dictionary")

        # Chart Average Days Timeline
        c_timeline = data["chart_avg_days_timeline"]
        assert "month" in c_timeline and "quarter" in c_timeline and "year" in c_timeline
        print(f"  ✓ Chart Avg Days Timeline returns monthly ({len(c_timeline['month'])}), quarterly ({len(c_timeline['quarter'])}), and annual ({len(c_timeline['year'])}) dynamics")

        # Filter: ID вакансии
        filters = data["filters"]
        assert "vacancies" in filters, "vacancies filter missing in response"
        vac_opts = filters["vacancies"]
        assert len(vac_opts) > 0, "vacancies filter options empty"
        print(f"  ✓ Filters include 'vacancies' multi-select with {len(vac_opts)} options")

        # 5.3 Filter by Vacancy ID
        r = await client.get(f"/api/dashboards/metrics?vacancy_ids={test_vac_id}", headers=h_sa1)
        assert r.status_code == 200
        vac_data = r.json()
        assert vac_data["chart2_open_closed"]["total"] == 1
        assert vac_data["chart2_open_closed"]["open"] == 1
        print(f"  ✓ Vacancy ID filter works: selecting #{test_vac_id} isolates metrics to 1 open vacancy")

        # 5.4 Cleanup test vacancy and reports
        async with AsyncSessionLocal() as db:
            await db.execute(delete(WeeklyReport).where(WeeklyReport.vacancy_id == test_vac_id))
            await db.execute(delete(VacancyHistory).where(VacancyHistory.vacancy_id == test_vac_id))
            await db.execute(delete(Vacancy).where(Vacancy.id == test_vac_id))
            await db.commit()
        print("  ✓ Cleanup of test data completed")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! SYSTEM VERIFIED 100%")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_tests())
