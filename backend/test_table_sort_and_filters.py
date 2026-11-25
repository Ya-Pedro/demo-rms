import asyncio
import os
from io import BytesIO
from datetime import date

os.environ["RMS_ALLOW_DEFAULT_SECRET"] = "1"
os.environ["ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

try:
    import pytest
    asyncio_mark = pytest.mark.asyncio
except ImportError:
    def asyncio_mark(fn):
        return fn

import httpx
import openpyxl
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from database import Base, get_db
from models import User, UserRole, Dictionary, DictionaryType, Vacancy, WeeklyReport
from auth import create_access_token, get_password_hash
from server import app, rms_key_builder


async def _setup_sort_filter_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    @event.listens_for(engine.sync_engine, "connect")
    def _register_utf8_lower(dbapi_conn, _conn_record):
        dbapi_conn.create_function("lower", 1, lambda s: s.lower() if isinstance(s, str) else s)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with SessionLocal() as db:
        pwd = get_password_hash("TestPass123!")
        sa = User(email="sa@test.ru", hashed_password=pwd, full_name="Super Admin", role=UserRole.SUPERADMIN, is_active=True)
        adm = User(email="adm@test.ru", hashed_password=pwd, full_name="Admin User", role=UserRole.ADMIN, is_active=True)
        rec = User(email="rec@test.ru", hashed_password=pwd, full_name="Recruiter User", role=UserRole.RECRUITER, is_active=True)
        db.add_all([sa, adm, rec])

        st_open = Dictionary(type=DictionaryType.VACANCY_STATUS, value="Открыта")
        st_cancel = Dictionary(type=DictionaryType.VACANCY_STATUS, value="Отмена")
        st_hold = Dictionary(type=DictionaryType.VACANCY_STATUS, value="Hold")
        role_android = Dictionary(type=DictionaryType.IT_ROLE, value="Android разработчик")
        role_angular = Dictionary(type=DictionaryType.IT_ROLE, value="angular разработчик")
        role_sys = Dictionary(type=DictionaryType.IT_ROLE, value="системный администратор")
        role_lawyer = Dictionary(type=DictionaryType.IT_ROLE, value="Юрист")
        feas_dict = Dictionary(type=DictionaryType.FEASIBILITY, value="Аврора ТЭО")
        city_dict = Dictionary(type=DictionaryType.CITY, value="Москва")
        tl_dict = Dictionary(type=DictionaryType.TEAM_LEAD, value="Лид Из Справочника")

        db.add_all([st_open, st_cancel, st_hold, role_android, role_angular, role_sys, role_lawyer, feas_dict, city_dict, tl_dict])
        await db.flush()

        # 1: empty role, empty candidate (None), empty feasibility, empty quantity (None)
        v_empty = Vacancy(
            vacancy_id="100", position_name="Вакансия Без Роли", status_id=st_open.id,
            it_role_id=None, candidate_name=None, feasibility_id=None, feasibility_text=None,
            open_date=None, salary_gross=None, quantity=None, offer_rejection_reason=None,
        )
        # 2: empty role, blank-string candidate, feasibility_text ONLY (not empty!)
        v_feas_text = Vacancy(
            vacancy_id="200", position_name="Вакансия С Текстом ТЭО", status_id=st_open.id,
            it_role_id=None, candidate_name="   ", feasibility_id=None, feasibility_text="Брутфорс ТЭО",
            city_text="Казань", team_lead_text="Текстовый Лид",
            open_date=date(2026, 11, 10), salary_gross=150000, quantity=1.0,
            offer_rejection_reason="Уровень дохода",
        )
        # 3: angular (lowercase!), feasibility dict, city dict, tl dict
        v_angular = Vacancy(
            vacancy_id="300", position_name="Angular Dev", status_id=st_open.id,
            it_role_id=role_angular.id, candidate_name="борис Кандидат",
            feasibility_id=feas_dict.id, city_id=city_dict.id, team_lead_id=tl_dict.id,
            open_date=date(2026, 11, 5), salary_gross=250000, quantity=1.0,
            offer_rejection_reason="Контроффер",
        )
        # 4: системный администратор (lowercase Cyrillic!), empty vid ""
        v_sys = Vacancy(
            vacancy_id="", position_name="SysAdmin", status_id=st_open.id,
            it_role_id=role_sys.id, candidate_name="Артем Кандидат",
            open_date=date(2026, 11, 1), salary_gross=100000, quantity=1.0,
            offer_rejection_reason="   ",
        )
        # 5: Юрист + Android
        v_lawyer = Vacancy(
            vacancy_id="500", position_name="Юрист По ИТ", status_id=st_open.id,
            it_role_id=role_lawyer.id, candidate_name="яков Кандидат",
            open_date=date(2026, 11, 15), salary_gross=300000, quantity=2.0,
            offer_rejection_reason="Уровень дохода, Локация",
        )
        v_android = Vacancy(
            vacancy_id="400", position_name="Android Dev", status_id=st_open.id,
            it_role_id=role_android.id, candidate_name="",
            open_date=date(2026, 11, 12), salary_gross=200000, quantity=1.0,
            offer_rejection_reason=None,
        )

        db.add_all([v_empty, v_feas_text, v_angular, v_sys, v_lawyer, v_android])
        await db.flush()

        # Weekly reports for 2025/2026 on some vacancies (v_empty & v_feas_text have NO reports -> year=None)
        db.add_all([
            WeeklyReport(vacancy_id=v_lawyer.id, week_number=45, year=2026, week_start=date(2026, 11, 2), resumes_sent=5),
            WeeklyReport(vacancy_id=v_android.id, week_number=10, year=2025, week_start=date(2025, 3, 3), resumes_sent=2),
            WeeklyReport(vacancy_id=v_angular.id, week_number=46, year=2026, week_start=date(2026, 11, 9), resumes_sent=1),
        ])
        await db.commit()

        ids = {
            "feas_dict": feas_dict.id,
            "st_open": st_open.id,
            "st_cancel": st_cancel.id,
            "st_hold": st_hold.id,
            "rec_id": rec.id,
        }

    FastAPICache.init(InMemoryBackend(), prefix="test-sort-filter", key_builder=rms_key_builder)
    token_sa = create_access_token({"sub": "sa@test.ru", "role": "superadmin"})
    token_adm = create_access_token({"sub": "adm@test.ru", "role": "admin"})
    token_rec = create_access_token({"sub": "rec@test.ru", "role": "recruiter"})
    ids["hdr_adm"] = {"Authorization": f"Bearer {token_adm}"}
    ids["hdr_rec"] = {"Authorization": f"Bearer {token_rec}"}
    return engine, ids, {"Authorization": f"Bearer {token_sa}"}


@asyncio_mark
async def test_sorting_empty_minimal_and_column_filters():
    engine, ids, headers = await _setup_sort_filter_db()
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # --- 1. VACANCIES TAB: IT ROLE ASC & DESC (empty FIRST on ASC, LAST on DESC, case-insensitive) ---
            r_vac_asc = await client.get("/api/vacancies", params={"sort_field": "it_role_id", "sort_order": "asc"}, headers=headers)
            assert r_vac_asc.status_code == 200
            roles_asc = [v["it_role"]["value"] if v["it_role"] else None for v in r_vac_asc.json()["items"]]
            assert roles_asc[:2] == [None, None], f"Empty roles must be FIRST on ASC, got {roles_asc}"
            # Non-empty roles case-insensitive: Android, angular, системный..., Юрист
            assert roles_asc[2:] == [
                "Android разработчик", "angular разработчик", "системный администратор", "Юрист"
            ], f"Expected case-insensitive alphabetical roles on ASC, got {roles_asc[2:]}"

            r_vac_desc = await client.get("/api/vacancies", params={"sort_field": "it_role_id", "sort_order": "desc"}, headers=headers)
            assert r_vac_desc.status_code == 200
            roles_desc = [v["it_role"]["value"] if v["it_role"] else None for v in r_vac_desc.json()["items"]]
            assert roles_desc[-2:] == [None, None], f"Empty roles must be LAST on DESC, got {roles_desc}"
            assert roles_desc[:4] == [
                "Юрист", "системный администратор", "angular разработчик", "Android разработчик"
            ], f"Expected reverse alphabetical roles on DESC, got {roles_desc[:4]}"

            # --- 2. REPORTS TAB & EXPORT: IT ROLE ASC & DESC ---
            r_rep_asc = await client.get("/api/reports/all", params={"sort_field": "it_role_name", "sort_order": "asc"}, headers=headers)
            assert r_rep_asc.status_code == 200
            rep_roles_asc = [it["it_role_name"] for it in r_rep_asc.json()["items"]]
            assert rep_roles_asc == [
                None, None, "Android разработчик", "angular разработчик", "системный администратор", "Юрист"
            ], f"Reports ASC mismatch: {rep_roles_asc}"

            r_rep_desc = await client.get("/api/reports/all", params={"sort_field": "it_role_name", "sort_order": "desc"}, headers=headers)
            assert r_rep_desc.status_code == 200
            rep_roles_desc = [it["it_role_name"] for it in r_rep_desc.json()["items"]]
            assert rep_roles_desc == [
                "Юрист", "системный администратор", "angular разработчик", "Android разработчик", None, None
            ], f"Reports DESC mismatch: {rep_roles_desc}"

            # Reports Excel export obeys identical empty-first/last sort
            r_rep_xl = await client.get("/api/reports/all/export", params={"sort_field": "it_role_name", "sort_order": "asc"}, headers=headers)
            assert r_rep_xl.status_code == 200
            wb_rep = openpyxl.load_workbook(BytesIO(r_rep_xl.content))
            ws_rep = wb_rep["Отчеты"]
            hdrs = [ws_rep.cell(1, c).value for c in range(1, ws_rep.max_column + 1)]
            role_col = hdrs.index("ИТ роль") + 1
            xl_roles = [ws_rep.cell(r, role_col).value for r in range(2, ws_rep.max_row + 1)]
            assert xl_roles == [None, None, "Android разработчик", "angular разработчик", "системный администратор", "Юрист"]

            # --- 3. TEXT WHITESPACE & NULL GROUPED AS MINIMAL (candidate_name) ---
            r_cand_asc = await client.get("/api/vacancies", params={"sort_field": "candidate_name", "sort_order": "asc"}, headers=headers)
            cands_asc = [(v["candidate_name"] or "").strip() for v in r_cand_asc.json()["items"]]
            assert cands_asc[:3] == ["", "", ""], f"All None/''/'   ' must come FIRST on ASC: {cands_asc}"
            assert cands_asc[3:] == ["Артем Кандидат", "борис Кандидат", "яков Кандидат"]

            r_cand_desc = await client.get("/api/vacancies", params={"sort_field": "candidate_name", "sort_order": "desc"}, headers=headers)
            cands_desc = [(v["candidate_name"] or "").strip() for v in r_cand_desc.json()["items"]]
            assert cands_desc[-3:] == ["", "", ""], f"All None/''/'   ' must come LAST on DESC: {cands_desc}"
            assert cands_desc[:3] == ["яков Кандидат", "борис Кандидат", "Артем Кандидат"]

            # --- 4. HYBRID FEASIBILITY SORT (feasibility_id + feasibility_text combined) ---
            r_feas_asc = await client.get("/api/vacancies", params={"sort_field": "feasibility_id", "sort_order": "asc"}, headers=headers)
            feas_asc = [v["feasibility_name"] for v in r_feas_asc.json()["items"]]
            # 4 truly empty rows FIRST, then "Аврора ТЭО" (dict), then "Брутфорс ТЭО" (text)
            assert feas_asc[:4] == [None, None, None, None], f"Empty feasibility must come first: {feas_asc}"
            assert feas_asc[4:] == ["Аврора ТЭО", "Брутфорс ТЭО"], f"Hybrid dict+text feasibility order broken: {feas_asc}"

            r_rep_feas = await client.get("/api/reports/all", params={"sort_field": "feasibility_name", "sort_order": "desc"}, headers=headers)
            assert [it["feasibility_name"] for it in r_rep_feas.json()["items"]][:2] == ["Брутфорс ТЭО", "Аврора ТЭО"]

            # --- 5. DATES, NUMBERS, VACANCY_ID & REPORT YEAR SORTING ---
            r_date_asc = await client.get("/api/vacancies", params={"sort_field": "open_date", "sort_order": "asc"}, headers=headers)
            assert r_date_asc.json()["items"][0]["open_date"] is None
            r_sal_asc = await client.get("/api/vacancies", params={"sort_field": "salary_gross", "sort_order": "asc"}, headers=headers)
            assert r_sal_asc.json()["items"][0]["salary_gross"] is None
            r_vid_asc = await client.get("/api/vacancies", params={"sort_field": "vacancy_id", "sort_order": "asc"}, headers=headers)
            assert (r_vid_asc.json()["items"][0]["vacancy_id"] or "").strip() == ""
            r_vid_desc = await client.get("/api/vacancies", params={"sort_field": "vacancy_id", "sort_order": "desc"}, headers=headers)
            assert (r_vid_desc.json()["items"][-1]["vacancy_id"] or "").strip() == ""

            # Year sort on Reports (rows without reports have min_year=None -> FIRST on ASC, LAST on DESC)
            r_yr_asc = await client.get("/api/reports/all", params={"sort_field": "year", "sort_order": "asc"}, headers=headers)
            yrs_asc = [it["year"] for it in r_yr_asc.json()["items"]]
            assert yrs_asc[:3] == ["None", "None", "None"] and yrs_asc[3:] == ["2025", "2026", "2026"]

            # Smart Vacancy Export sorting matches
            r_sm_xl = await client.post("/api/export/vacancies/smart", json={
                "period": "all_time", "sort_field": "it_role_id", "sort_order": "asc", "apply_filters": False
            }, headers=headers)
            assert r_sm_xl.status_code == 200
            wb_sm = openpyxl.load_workbook(BytesIO(r_sm_xl.content))
            ws_sm = wb_sm["Вакансии"]
            sm_hdrs = [ws_sm.cell(1, c).value for c in range(1, ws_sm.max_column + 1)]
            sm_rcol = sm_hdrs.index("ИТ роль") + 1
            assert [ws_sm.cell(r, sm_rcol).value for r in range(2, ws_sm.max_row + 1)] == [
                None, None, "Android разработчик", "angular разработчик", "системный администратор", "Юрист"
            ]

            # --- 6. COLUMN FILTERS CHECK (offer_rejection_reason multi-select, hybrid ТЭО, __empty__) ---
            # Multi-select offer_rejection_reason + __empty__ on Vacancies & Reports
            r_rej_multi = await client.get("/api/vacancies", params={
                "offer_rejection_reason": ["Уровень дохода", "Контроффер"]
            }, headers=headers)
            assert r_rej_multi.json()["total"] == 3  # v_feas_text, v_angular, v_lawyer

            r_rej_rep_empty = await client.get("/api/reports/all", params={
                "offer_rejection_reason": ["__empty__"]
            }, headers=headers)
            assert r_rej_rep_empty.json()["total"] == 3  # None, "   ", None

            # feasibility_id=[0] excludes v_feas_text (has feasibility_text!)
            r_feas_empty = await client.get("/api/vacancies", params={"feasibility_id": [0]}, headers=headers)
            assert r_feas_empty.json()["total"] == 4

            # Reports feasibility_name searches BOTH text & dictionary, and __empty__ finds only truly empty
            assert (await client.get("/api/reports/all", params={"feasibility_name": "Аврора"}, headers=headers)).json()["total"] == 1
            assert (await client.get("/api/reports/all", params={"feasibility_name": "Брутфорс"}, headers=headers)).json()["total"] == 1
            assert (await client.get("/api/reports/all", params={"feasibility_name": "__empty__"}, headers=headers)).json()["total"] == 4

            # Hybrid city/team_lead text search finds dict entries too
            assert (await client.get("/api/vacancies", params={"search_city_text": "Москва"}, headers=headers)).json()["total"] == 1
            assert (await client.get("/api/vacancies", params={"search_team_lead_text": "Справочника"}, headers=headers)).json()["total"] == 1

            # Text & numeric __empty__ filters across all modes & exact quantity
            assert (await client.get("/api/vacancies", params={"search_candidate_name": "__empty__"}, headers=headers)).json()["total"] == 3
            assert (await client.get("/api/vacancies", params={"search_salary_gross": "__empty__"}, headers=headers)).json()["total"] == 1
            assert (await client.get("/api/vacancies", params={"search_work_duration_days": "__empty__"}, headers=headers)).json()["total"] == 1
            assert (await client.get("/api/reports/all", params={"total_resumes_sent": "__empty__"}, headers=headers)).json()["total"] == 3
            assert (await client.get("/api/vacancies", params={"search_quantity": "2"}, headers=headers)).json()["total"] == 1

            # search_vacancy_id works in /api/reports/all/export too
            r_exp_vid = await client.get("/api/reports/all/export", params={"search_vacancy_id": "500"}, headers=headers)
            wb_ev = openpyxl.load_workbook(BytesIO(r_exp_vid.content))
            assert wb_ev["Отчеты"].max_row == 2  # header + 1 matching row

            # --- 7. ADMIN/SUPERADMIN STATUS_CHANGED_AT EDIT, RBAC, AND IMPORT PREVIEW WARNING ---
            # Create an undated Cancelled vacancy as Admin (explicit None)
            r_cr = await client.post("/api/vacancies", json={
                "position_name": "Октябрьская отмена без даты",
                "status_id": ids["st_cancel"],
                "open_date": "2026-09-20",
                "status_changed_at": None,
                "recruiter_id": ids["rec_id"],
            }, headers=ids["hdr_adm"])
            assert r_cr.status_code == 201
            undated_vac = r_cr.json()
            # Ensure cleared via PATCH as admin (in case create auto-filled date.today())
            r_clr = await client.patch(f"/api/vacancies/{undated_vac['id']}", json={
                "status_changed_at": None,
            }, headers=ids["hdr_adm"])
            assert r_clr.status_code == 200 and r_clr.json()["status_changed_at"] is None

            # Before filling October date: October metrics have 0 Cancelled
            r_oct_before = await client.get("/api/dashboards/metrics", params={
                "start_date": "2026-10-01", "end_date": "2026-10-31"
            }, headers=headers)
            assert r_oct_before.json()["chart2_open_closed"]["cancel"] == 0

            # Admin fills October status_changed_at without changing status_id
            r_fix_oct = await client.patch(f"/api/vacancies/{undated_vac['id']}", json={
                "status_id": ids["st_cancel"],
                "status_changed_at": "2026-10-15",
            }, headers=ids["hdr_adm"])
            assert r_fix_oct.status_code == 200
            assert r_fix_oct.json()["status_changed_at"] == "2026-10-15"

            # Dashboard cache cleared automatically & October now reflects cancel == 1!
            r_oct_after = await client.get("/api/dashboards/metrics", params={
                "start_date": "2026-10-01", "end_date": "2026-10-31"
            }, headers=headers)
            assert r_oct_after.json()["chart2_open_closed"]["cancel"] == 1

            # Superadmin changes status AND sets explicit past date -> keeps explicit date
            r_sa_chg = await client.patch(f"/api/vacancies/{undated_vac['id']}", json={
                "status_id": ids["st_open"],
                "status_changed_at": "2026-10-20",
            }, headers=headers)
            assert r_sa_chg.status_code == 200
            assert r_sa_chg.json()["status_changed_at"] == "2026-10-20"

            # Recruiter CANNOT manually change status_changed_at on create or update
            r_rec_cr = await client.post("/api/vacancies", json={
                "position_name": "Рекрутерская вакансия",
                "status_id": ids["st_open"],
                "status_changed_at": "2026-10-01",
            }, headers=ids["hdr_rec"])
            assert r_rec_cr.status_code == 201
            rec_vac = r_rec_cr.json()
            assert rec_vac["status_changed_at"] == date.today().isoformat()

            r_rec_patch = await client.patch(f"/api/vacancies/{rec_vac['id']}", json={
                "status_changed_at": "2026-10-05",
            }, headers=ids["hdr_rec"])
            assert r_rec_patch.status_code == 200
            assert r_rec_patch.json()["status_changed_at"] == date.today().isoformat()

            r_rec_chg_st = await client.patch(f"/api/vacancies/{rec_vac['id']}", json={
                "status_id": ids["st_hold"],
                "status_changed_at": "2026-10-05",
            }, headers=ids["hdr_rec"])
            assert r_rec_chg_st.status_code == 200
            assert r_rec_chg_st.json()["status_changed_at"] == date.today().isoformat()

            # Excel /import/preview highlights missing status_changed_at on Отмена/Hold, ignores existing DB dated row
            wb_imp = openpyxl.Workbook()
            ws_imp = wb_imp.active
            ws_imp.append(["ID вакансии", "Вакансия", "Статус вакансии", "Дата изм. статуса"])
            ws_imp.append(["NEW_CANCEL", "Отмена без даты", "Отмена", ""])
            ws_imp.append(["NEW_HOLD", "Холд с прочерком", "Hold", "-"])
            ws_imp.append([undated_vac["vacancy_id"], "Уже с датой в БД", "Отмена", ""])
            imp_buf = BytesIO()
            wb_imp.save(imp_buf)
            imp_buf.seek(0)
            r_prev = await client.post(
                "/api/vacancies/import/preview",
                files={"file": ("test.xlsx", imp_buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                headers=headers,
            )
            assert r_prev.status_code == 200
            prev_data = r_prev.json()
            assert len(prev_data["missing_status_dates"]) == 2
            assert {m["vacancy_id"] for m in prev_data["missing_status_dates"]} == {"NEW_CANCEL", "NEW_HOLD"}

            print("ALL SORTING, COLUMN FILTER & STATUS DATE TESTS PASSED (100%)!")

    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_sorting_empty_minimal_and_column_filters())
