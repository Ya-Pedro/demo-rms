import asyncio
import os
import json
from io import BytesIO
from datetime import date, datetime, timedelta, timezone

os.environ["RMS_ALLOW_DEFAULT_SECRET"] = "1"
os.environ["ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

try:
    import pytest
    asyncio_mark = pytest.mark.asyncio
except ImportError:
    def asyncio_mark(fn):
        return fn

import openpyxl
import httpx
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from database import Base, get_db
from models import (
    User, UserRole, Dictionary, DictionaryType,
    Vacancy, WeeklyReport, VacancyDelegation, VacancyHistory,
)
from auth import create_access_token, get_password_hash
from server import app, rms_key_builder


async def _setup_test_app():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    FastAPICache.init(InMemoryBackend(), prefix="test-dash", key_builder=rms_key_builder)

    async with TestSessionLocal() as db:
        pwd = get_password_hash("TestPass123!")
        sa = User(email="sa@test.ru", hashed_password=pwd, full_name="Super Admin", role=UserRole.SUPERADMIN, is_active=True)
        rec1 = User(email="rec1@test.ru", hashed_password=pwd, full_name="Рекрутер Основной", role=UserRole.RECRUITER, is_active=True)
        rec2 = User(email="rec2@test.ru", hashed_password=pwd, full_name="Рекрутер Замещающий", role=UserRole.RECRUITER, is_active=True)
        rec_inactive = User(email="rec_old@test.ru", hashed_password=pwd, full_name="Уволенный Рекрутер", role=UserRole.RECRUITER, is_active=False)
        db.add_all([sa, rec1, rec2, rec_inactive])
        await db.flush()

        # Dictionaries
        st_open = Dictionary(type=DictionaryType.VACANCY_STATUS, value="Открыта")
        st_offer = Dictionary(type=DictionaryType.VACANCY_STATUS, value="Оффер")
        st_sb = Dictionary(type=DictionaryType.VACANCY_STATUS, value="Проверка СБ")
        st_closed = Dictionary(type=DictionaryType.VACANCY_STATUS, value="Закрыта")
        st_hold = Dictionary(type=DictionaryType.VACANCY_STATUS, value="Hold")
        st_cancel = Dictionary(type=DictionaryType.VACANCY_STATUS, value="Отмена")

        blk_digital = Dictionary(type=DictionaryType.BLOCK, value="Блок Диджитал")
        blk_com = Dictionary(type=DictionaryType.BLOCK, value="КомКластер")
        blk_other = Dictionary(type=DictionaryType.BLOCK, value="Прочее")

        role_ds = Dictionary(type=DictionaryType.IT_ROLE, value="Data Scientist")
        role_dev = Dictionary(type=DictionaryType.IT_ROLE, value="Backend Developer")

        lvl_mid = Dictionary(type=DictionaryType.SPECIALIST_LEVEL, value="Мидл")
        lvl_sen = Dictionary(type=DictionaryType.SPECIALIST_LEVEL, value="Сеньор")

        mgr_1 = Dictionary(type=DictionaryType.ADMIN_MANAGER, value="Руководитель А")
        mgr_2 = Dictionary(type=DictionaryType.ADMIN_MANAGER, value="Руководитель Б")

        proj_ai = Dictionary(type=DictionaryType.PROJECT, value="ИИ")
        proj_home = Dictionary(type=DictionaryType.PROJECT, value="Умный Дом")

        src_hh = Dictionary(type=DictionaryType.SOURCE, value="hh.ru")
        rep_new = Dictionary(type=DictionaryType.REPLACEMENT_TYPE, value="Новая")
        emp_staff = Dictionary(type=DictionaryType.EMPLOYMENT_TYPE, value="Штат")
        rej_salary = Dictionary(type=DictionaryType.OFFER_REJECTION_REASON, value="Уровень дохода")
        rej_counter = Dictionary(type=DictionaryType.OFFER_REJECTION_REASON, value="Контроффер")

        db.add_all([
            st_open, st_offer, st_sb, st_closed, st_hold, st_cancel,
            blk_digital, blk_com, blk_other,
            role_ds, role_dev, lvl_mid, lvl_sen, mgr_1, mgr_2,
            proj_ai, proj_home, src_hh, rep_new, emp_staff, rej_salary, rej_counter,
        ])
        await db.flush()

        # --- Scenario reproducing screenshot (Nov 1 - Nov 25, 2026, Digital Block) ---
        # 3 Open + 1 Offer = 4 open active vacancies (including 1 with delegation & co_recruiter!)
        v_open_1 = Vacancy(
            vacancy_id="8046", position_name="Data Scientist", status_id=st_open.id,
            block_id=blk_digital.id, it_role_id=role_ds.id, level_id=lvl_sen.id,
            admin_manager_id=mgr_1.id, project_id=proj_ai.id, recruiter_id=rec1.id,
            co_recruiter_id=rec2.id, replacement_type_id=rep_new.id, employment_type_id=emp_staff.id,
            open_date=date(2026, 11, 9), salary_gross=350000,
        )
        v_offer_1 = Vacancy(
            vacancy_id="8045", position_name="Специалист техподдержки", status_id=st_offer.id,
            block_id=blk_digital.id, it_role_id=role_dev.id, level_id=lvl_mid.id,
            admin_manager_id=mgr_2.id, project_id=proj_home.id, recruiter_id=rec1.id,
            open_date=date(2026, 11, 6), salary_gross=200000,
        )
        v_open_2 = Vacancy(
            vacancy_id="1778", position_name="Специалист по тестированию", status_id=st_open.id,
            block_id=blk_digital.id, it_role_id=role_dev.id, level_id=lvl_mid.id,
            admin_manager_id=mgr_1.id, project_id=proj_home.id, recruiter_id=rec2.id,
            open_date=date(2026, 9, 17),
        )
        v_open_3 = Vacancy(
            vacancy_id="1071", position_name="Веб-дизайнер", status_id=st_open.id,
            block_id=blk_digital.id, it_role_id=role_dev.id, level_id=lvl_mid.id,
            admin_manager_id=mgr_2.id, project_id=proj_ai.id, recruiter_id=rec_inactive.id,
            open_date=date(2026, 1, 19),
        )

        # Undated Cancelled vacancy (THIS CAUSED THE BUG in Digital: 4 -> 5!)
        v_cancel_undated = Vacancy(
            vacancy_id="555", position_name="Старая отмененная", status_id=st_cancel.id,
            block_id=blk_digital.id, it_role_id=role_dev.id, level_id=lvl_mid.id,
            recruiter_id=rec1.id, open_date=date(2026, 5, 1), status_changed_at=None, close_date=None,
        )
        # Old October Cancelled vacancy with date (should NOT appear in Nov)
        v_cancel_oct = Vacancy(
            vacancy_id="556", position_name="Октябрьская отмена", status_id=st_cancel.id,
            block_id=blk_digital.id, recruiter_id=rec1.id,
            open_date=date(2026, 9, 1), status_changed_at=date(2026, 10, 15),
        )

        # 2 Closed in Nov
        v_closed_nov1 = Vacancy(
            vacancy_id="7001", position_name="ML Engineer", status_id=st_closed.id,
            block_id=blk_digital.id, it_role_id=role_ds.id, level_id=lvl_sen.id,
            recruiter_id=rec1.id, source_id=src_hh.id, candidate_company="Яндекс",
            open_date=date(2026, 10, 1), close_date=date(2026, 11, 12), salary_gross=400000,
            offer_rejection_reason="Контроффер",
        )
        # Closed in Dec (must appear as Открыта during Nov 1 - Nov 25, AND in Oct!)
        v_closed_dec = Vacancy(
            vacancy_id="7002", position_name="Закрыта позже", status_id=st_closed.id,
            block_id=blk_com.id, it_role_id=role_dev.id, level_id=lvl_sen.id,
            recruiter_id=rec1.id, source_id=src_hh.id,
            open_date=date(2026, 10, 5), close_date=date(2026, 12, 2),
        )
        # Hold in Digital
        v_hold_dig = Vacancy(
            vacancy_id="6001", position_name="На холде", status_id=st_hold.id,
            block_id=blk_digital.id, recruiter_id=rec1.id,
            open_date=date(2026, 4, 1), status_changed_at=date(2026, 6, 1),
        )
        # Hold only between Nov 5 and Nov 10 (currently Открыта)
        v_hold_interval = Vacancy(
            vacancy_id="6002", position_name="Краткий холд", status_id=st_open.id,
            block_id=blk_com.id, recruiter_id=rec2.id,
            open_date=date(2026, 9, 1),
        )
        # Vacancy whose external vacancy_id collides with v_open_1.id!
        v_collision = Vacancy(
            vacancy_id="1", position_name="Коллизия ID", status_id=st_open.id,
            block_id=blk_other.id, recruiter_id=rec2.id,
            open_date=date(2026, 11, 2),
        )

        db.add_all([
            v_open_1, v_offer_1, v_open_2, v_open_3,
            v_cancel_undated, v_cancel_oct,
            v_closed_nov1, v_closed_dec,
            v_hold_dig, v_hold_interval, v_collision,
        ])
        await db.flush()

        # Co-recruiter only on v_open_1 (NO delegation here — tests co-recruiter separately)
        # Delegations tested on blk_com (1 active Nov1..Nov30, 1 revoked, 1 expired Nov20)
        db.add_all([
            VacancyDelegation(
                vacancy_id=v_hold_interval.id,
                delegated_to_id=rec1.id,
                delegated_by_id=sa.id,
                start_date=date(2026, 11, 1),
                end_date=date(2026, 11, 30),
                is_active=True,
            ),
            VacancyDelegation(
                vacancy_id=v_closed_dec.id,
                delegated_to_id=rec2.id,
                delegated_by_id=sa.id,
                start_date=date(2026, 11, 1),
                end_date=date(2026, 11, 30),
                is_active=False,
            ),
            VacancyDelegation(
                vacancy_id=v_closed_dec.id,
                delegated_to_id=rec_inactive.id,
                delegated_by_id=sa.id,
                start_date=date(2026, 11, 1),
                end_date=date(2026, 11, 20),
                is_active=True,
            ),
        ])

        # History for v_hold_interval: entered Hold Nov 5, exited Hold Nov 10
        db.add(VacancyHistory(
            vacancy_id=v_hold_interval.id,
            user_id=sa.id,
            action_type="UPDATE",
            changes=json.dumps({"Статус вакансии": {"old": "Открыта", "new": "Hold"}}, ensure_ascii=False),
            created_at=datetime(2026, 11, 5, 10, 0, tzinfo=timezone.utc),
        ))
        db.add(VacancyHistory(
            vacancy_id=v_hold_interval.id,
            user_id=sa.id,
            action_type="UPDATE",
            changes=json.dumps({"Статус вакансии": {"old": "Hold", "new": "Открыта"}}, ensure_ascii=False),
            created_at=datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc),
        ))

        # Weekly reports: Oct report vs Nov report
        db.add(WeeklyReport(
            vacancy_id=v_open_3.id, week_start=date(2026, 10, 12), week_number=42, year=2026,
            resumes_sent=10, candidates_agreed=5, interviews_conducted=3, offer_made=1,
            offer_rejection_reason="Уровень дохода",
        ))
        db.add(WeeklyReport(
            vacancy_id=v_open_1.id, week_start=date(2026, 11, 16), week_number=47, year=2026,
            resumes_sent=4, candidates_agreed=2, interviews_conducted=1, offer_made=1,
        ))
        db.add(WeeklyReport(
            vacancy_id=v_closed_nov1.id, week_start=date(2026, 11, 9), week_number=46, year=2026,
            resumes_sent=6, candidates_agreed=4, interviews_conducted=2, offer_made=1, offer_accepted=1,
            offer_rejection_reason="Контроффер",
        ))
        await db.commit()

        ids = {
            "blocks": {"digital": blk_digital.id, "com": blk_com.id, "other": blk_other.id},
            "statuses": {"open": st_open.id, "offer": st_offer.id, "closed": st_closed.id, "hold": st_hold.id, "cancel": st_cancel.id},
            "roles": {"ds": role_ds.id, "dev": role_dev.id},
            "levels": {"mid": lvl_mid.id, "sen": lvl_sen.id},
            "mgrs": {"m1": mgr_1.id, "m2": mgr_2.id},
            "projects": {"ai": proj_ai.id, "home": proj_home.id},
            "recs": {"r1": rec1.id, "r2": rec2.id, "old": rec_inactive.id},
            "vacs": {"open1": v_open_1.id, "offer1": v_offer_1.id, "closed_nov1": v_closed_nov1.id, "closed_dec": v_closed_dec.id, "hold_interval": v_hold_interval.id, "collision": v_collision.id},
        }

    token = create_access_token({"sub": "sa@test.ru", "role": "superadmin"})
    return engine, ids, {"Authorization": f"Bearer {token}"}


@asyncio_mark
async def test_dashboards_consistency_and_all_filters():
    engine, ids, headers = await _setup_test_app()
    transport = httpx.ASGITransport(app=app)
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            blk_dig = ids["blocks"]["digital"]
            blk_com = ids["blocks"]["com"]

            # 1. Exact reproduction of screenshot (Nov 1 - Nov 25, Digital Block)
            params_nov_dig = {
                "start_date": "2026-11-01",
                "end_date": "2026-11-25",
                "block_ids": str(blk_dig),
            }
            r = await client.get("/api/dashboards/metrics", params=params_nov_dig, headers=headers)
            assert r.status_code == 200
            d = r.json()

            # Check Vacancies tab matches too!
            r_vac = await client.get("/api/vacancies", params={
                "block_id": [blk_dig],
                "status_id": [ids["statuses"]["open"], ids["statuses"]["offer"]],
            }, headers=headers)
            assert r_vac.status_code == 200
            assert r_vac.json()["total"] == 4, f"Vacancies tab expected 4, got {r_vac.json()['total']}"

            # Check chart2_open_closed ("Вакансии по статусам")
            c2 = d["chart2_open_closed"]
            assert c2["open"] == 4, f"Expected open=4 (3 Открыта + 1 Оффер, NOT 5!), got {c2['open']}"
            assert c2["closed"] == 1
            assert c2["hold"] == 1
            assert c2["cancel"] == 0
            assert c2["total"] == 6

            # Check chart6_statuses ("Детализация Открытых")
            c6_map = {x["status"]: x["value"] for x in d["chart6_statuses"]}
            assert c6_map.get("Открыта") == 3, f"Expected Открыта=3, got {c6_map}"
            assert c6_map.get("Оффер") == 1, f"Expected Оффер=1, got {c6_map}"

            # Check Ivakhin table matches chart2 identically for Nov
            ivk = d["chart_ivakhin_statuses"]
            assert len(ivk) == 1
            assert ivk[0]["open"] == 4
            assert ivk[0]["closed"] == 1
            assert ivk[0]["hold"] == 1
            assert ivk[0]["cancel"] == 0

            # Check Recruiter Load Matrix & chart8 & Excel export match
            # Digital unique active = 4, BUT v_open_1 has co_recruiter rec2 -> Recruiter Load = 5!
            assert d["recruiter_load_totals"]["total_open"] == 5
            assert d["recruiter_load_totals"]["open"] == 4
            assert d["recruiter_load_totals"]["offer"] == 1
            assert sum(x["value"] for x in d["chart8_recruiter_load"]) == 7  # 6 unique + 1 co_recruiter
            # Inactive recruiter name must be present (not "ID X")
            rec_names_in_load = {x["recruiter"] for x in d["recruiter_load_matrix"]}
            assert "Уволенный Рекрутер" in rec_names_in_load
            assert "Уволенный Рекрутер" in {x["value"] for x in d["filters"]["recruiters"]}

            r_exp_rec = await client.get("/api/dashboards/export/recruiter-load", params=params_nov_dig, headers=headers)
            assert r_exp_rec.status_code == 200
            wb = openpyxl.load_workbook(BytesIO(r_exp_rec.content))
            ws = wb.active
            # Last row total_open cell (col 9) must be 5 (4 unique + 1 co_recruiter, including pre-Nov vacancies!)
            assert ws.cell(row=ws.max_row, column=9).value == 5

            r_exp_ivk = await client.get("/api/dashboards/export/ivakhin-statuses", params=params_nov_dig, headers=headers)
            assert r_exp_ivk.status_code == 200

            # Check Funnel & Rejections respect Nov period (Oct report with 10 resumes & Уровень дохода excluded!)
            funnel_map = {s["stage"]: s["value"] for s in d["chart3_funnel"]}
            assert funnel_map["Передано заказчику"] == 10, f"Expected 4+6=10 (excluding Oct 10), got {funnel_map}"
            rej_map = {x["reason"]: x["value"] for x in d["chart_rejections"]}
            assert rej_map.get("Уровень дохода", 0) == 0, f"Oct rejection leaked into Nov: {rej_map}"
            assert rej_map.get("Контроффер", 0) == 1

            # Check JO Conversion has ONLY Nov (no fake 0% Jan..Oct months)
            jo_months = d["chart_jo_conversion"]["month"]
            assert len(jo_months) == 1 and jo_months[0]["label"] == "Ноя"

            # Check Excel Ivakhin export matches JSON chart_ivakhin_statuses
            wb_ivk = openpyxl.load_workbook(BytesIO(r_exp_ivk.content))
            ws_ivk_sum = wb_ivk["Свод по месяцам"]
            # Total row at bottom: col 3=open, 4=closed, 5=hold, 6=cancel, 7=total
            assert ws_ivk_sum.cell(row=ws_ivk_sum.max_row, column=3).value == 4
            assert ws_ivk_sum.cell(row=ws_ivk_sum.max_row, column=4).value == 1
            assert ws_ivk_sum.cell(row=ws_ivk_sum.max_row, column=5).value == 1
            assert ws_ivk_sum.cell(row=ws_ivk_sum.max_row, column=6).value == 0
            assert ws_ivk_sum.cell(row=ws_ivk_sum.max_row, column=7).value == 5  # open + hold

            # Check interdependent filter options keep self options intact
            assert len(d["filters"]["blocks"]) >= 2, "Block filter must still show other available blocks!"
            assert {o["value"] for o in d["filters"]["projects"]} == {"ИИ", "Умный Дом"}

            # 2. Test Hold history intervals in ComCluster (Hold only Nov 5 - Nov 10)
            r_oct_com = await client.get("/api/dashboards/metrics", params={
                "start_date": "2026-10-01", "end_date": "2026-10-31", "block_ids": str(blk_com)
            }, headers=headers)
            assert r_oct_com.json()["chart2_open_closed"]["hold"] == 0, "Hold didn't start until Nov 5!"
            assert r_oct_com.json()["chart2_open_closed"]["open"] == 2  # v_closed_dec + v_hold_interval

            r_mid_hold = await client.get("/api/dashboards/metrics", params={
                "start_date": "2026-11-01", "end_date": "2026-11-07", "block_ids": str(blk_com)
            }, headers=headers)
            assert r_mid_hold.json()["chart2_open_closed"]["hold"] == 1
            assert r_mid_hold.json()["chart2_open_closed"]["open"] == 1

            # 3. Test historical Closed-after-cutoff respects Status=Открыта across ALL charts + active delegation ONLY in Recruiter Load
            r_st_open = await client.get("/api/dashboards/metrics", params={
                "start_date": "2026-11-01", "end_date": "2026-11-25",
                "block_ids": str(blk_com), "status_ids": str(ids["statuses"]["open"])
            }, headers=headers)
            d_st = r_st_open.json()
            assert d_st["chart2_open_closed"]["open"] == 2
            assert d_st["chart_ivakhin_statuses"][0]["open"] == 2
            # 2 unique + 1 active delegation (v_hold_interval -> rec1); revoked & expired delegations ignored!
            assert d_st["recruiter_load_totals"]["total_open"] == 3
            assert {x["recruiter"] for x in d_st["recruiter_load_matrix"]} == {"Рекрутер Основной", "Рекрутер Замещающий"}
            assert len(d_st["chart_avg_days_timeline"]["month"]) == 0 or d_st["chart_avg_days_timeline"]["month"][0]["count"] == 0

            # Delegation filter with recruiter_ids=rec1 in ComCluster: unique=1, Recruiter Load=2 (own + delegated)
            r_com_rec1 = await client.get("/api/dashboards/metrics", params={
                "start_date": "2026-11-01", "end_date": "2026-11-25",
                "block_ids": str(blk_com), "recruiter_ids": str(ids["recs"]["r1"])
            }, headers=headers)
            d_com_r1 = r_com_rec1.json()
            assert d_com_r1["chart2_open_closed"]["total"] == 1
            assert d_com_r1["recruiter_load_totals"]["total_open"] == 2
            assert [x["recruiter"] for x in d_com_r1["recruiter_load_matrix"]] == ["Рекрутер Основной"]
            assert d_com_r1["chart8_recruiter_load"] == [{"recruiter": "Рекрутер Основной", "value": 2}]

            # 4. Test Vacancy ID collision resistance (v_open_1.id == 1 vs v_collision.vacancy_id == "1")
            r_vac1 = await client.get("/api/dashboards/metrics", params={"vacancy_ids": str(ids["vacs"]["open1"])}, headers=headers)
            assert r_vac1.json()["chart2_open_closed"]["total"] == 1, "PK=1 collided with vacancy_id='1'!"

            # 5. Test IT Role, Level, Admin Manager, Project, Recruiter, GroupBy, Inverted Dates
            r_ds = await client.get("/api/dashboards/metrics", params={"it_role_ids": str(ids["roles"]["ds"]), "block_ids": str(blk_dig)}, headers=headers)
            assert r_ds.json()["chart2_open_closed"]["total"] == 2  # v_open_1 + v_closed_nov1

            r_sen = await client.get("/api/dashboards/metrics", params={"level_ids": str(ids["levels"]["sen"]), "block_ids": str(blk_dig)}, headers=headers)
            assert r_sen.json()["chart2_open_closed"]["total"] == 2

            r_mgr = await client.get("/api/dashboards/metrics", params={"admin_manager_ids": str(ids["mgrs"]["m1"]), "block_ids": str(blk_dig)}, headers=headers)
            assert r_mgr.json()["chart2_open_closed"]["total"] == 2  # v_open_1 + v_open_2

            r_proj = await client.get("/api/dashboards/metrics", params={"project_ids": str(ids["projects"]["ai"]), "block_ids": str(blk_dig)}, headers=headers)
            assert r_proj.json()["chart2_open_closed"]["total"] == 2  # v_open_1 + v_open_3

            # Recruiter filter excludes co-recruiter from unique charts, INCLUDES it in Recruiter Load!
            r_rec2 = await client.get("/api/dashboards/metrics", params={"recruiter_ids": str(ids["recs"]["r2"]), "block_ids": str(blk_dig)}, headers=headers)
            d_rec2 = r_rec2.json()
            assert d_rec2["chart2_open_closed"]["total"] == 1  # only v_open_2 (not v_open_1!)
            assert d_rec2["recruiter_load_totals"]["total_open"] == 2  # v_open_2 + co_recruiter v_open_1!
            assert [x["recruiter"] for x in d_rec2["recruiter_load_matrix"]] == ["Рекрутер Замещающий"]
            assert d_rec2["chart8_recruiter_load"] == [{"recruiter": "Рекрутер Замещающий", "value": 2}]

            # Inverted dates automatically swap cleanly
            r_inv = await client.get("/api/dashboards/metrics", params={
                "start_date": "2026-11-25", "end_date": "2026-11-01", "block_ids": str(blk_dig)
            }, headers=headers)
            assert r_inv.json()["chart2_open_closed"]["open"] == 4

            # Group by level switch
            r_grp = await client.get("/api/dashboards/metrics", params={"group_by": "level"}, headers=headers)
            assert any(x["label"] == "Сеньор" for x in r_grp.json()["chart5_avg_days"])

            # 6. Status=Hold isolates ONLY Hold across all charts (including JO conversion & timelines)
            r_hold_only = await client.get("/api/dashboards/metrics", params={
                "start_date": "2026-11-01", "end_date": "2026-11-25",
                "block_ids": str(blk_dig), "status_ids": str(ids["statuses"]["hold"])
            }, headers=headers)
            dh = r_hold_only.json()
            assert dh["chart2_open_closed"] == {"total": 1, "open": 0, "closed": 0, "hold": 1, "cancel": 0}
            assert dh["chart_ivakhin_statuses"][0]["hold"] == 1
            assert dh["chart_ivakhin_statuses"][0]["open"] == 0
            assert dh["recruiter_load_totals"]["total_open"] == 0
            assert dh["chart1_source"] == []
            assert dh["chart4_companies"] == []
            assert dh["chart5_avg_days"] == []
            assert all(m["count"] == 0 and m["value"] == 0 for m in dh["chart_avg_days_timeline"]["month"])
            assert dh["chart_jo_conversion"]["month"][0]["closed"] == 0

            # 7. Status=Оффер isolates Оффер across chart2, chart6, Ivakhin, and RecruiterLoad
            r_offer_only = await client.get("/api/dashboards/metrics", params={
                "start_date": "2026-11-01", "end_date": "2026-11-25",
                "block_ids": str(blk_dig), "status_ids": str(ids["statuses"]["offer"])
            }, headers=headers)
            do = r_offer_only.json()
            assert do["chart2_open_closed"]["open"] == 1
            assert do["chart6_statuses"] == [{"status": "Оффер", "value": 1}]
            assert do["chart_ivakhin_statuses"][0]["open"] == 1
            assert do["recruiter_load_totals"]["offer"] == 1
            assert do["recruiter_load_totals"]["total_open"] == 1

            # 8. No period selected: undated Отмена counts as Отмена & balance holds
            r_all_period = await client.get("/api/dashboards/metrics", params={"block_ids": str(blk_dig)}, headers=headers)
            da = r_all_period.json()
            c2a = da["chart2_open_closed"]
            assert c2a["total"] == c2a["open"] + c2a["closed"] + c2a["hold"] + c2a["cancel"]
            assert c2a["cancel"] == 2  # v_cancel_undated + v_cancel_oct
            assert c2a["open"] == 4

            print("ALL DASHBOARD CONSISTENCY & FILTER TESTS PASSED (100%)!")

    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_dashboards_consistency_and_all_filters())
