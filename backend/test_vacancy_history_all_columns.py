import asyncio
import json
import httpx
from datetime import date, datetime, timedelta
from auth import create_access_token
from database import AsyncSessionLocal
from models import User, Vacancy, WeeklyReport, Dictionary, DictionaryType, VacancyHistory
from sqlalchemy import select, delete

BASE_URL = "http://localhost:8000"

async def run_history_tests():
    print("=" * 70)
    print("STARTING VACANCY HISTORY COMPREHENSIVE TEST SUITE (ALL COLUMNS)")
    print("=" * 70)

    # Setup superadmin token for testing
    admin_token = create_access_token({"sub": "admin1@rms-system.ru", "role": "superadmin"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    async with AsyncSessionLocal() as db:
        # Load sample dictionary IDs for all dictionary types
        async def get_dict_ids(dtype):
            res = await db.execute(select(Dictionary).where(Dictionary.type == dtype, Dictionary.is_active == True))
            items = res.scalars().all()
            return [it.id for it in items]

        level_ids = await get_dict_ids(DictionaryType.SPECIALIST_LEVEL)
        status_ids = await get_dict_ids(DictionaryType.VACANCY_STATUS)
        it_role_ids = await get_dict_ids(DictionaryType.IT_ROLE)
        admin_manager_ids = await get_dict_ids(DictionaryType.ADMIN_MANAGER)
        project_ids = await get_dict_ids(DictionaryType.PROJECT)
        source_ids = await get_dict_ids(DictionaryType.SOURCE)
        transfer_ids = await get_dict_ids(DictionaryType.INTERNAL_TRANSFER)
        replacement_ids = await get_dict_ids(DictionaryType.REPLACEMENT_TYPE)
        employment_ids = await get_dict_ids(DictionaryType.EMPLOYMENT_TYPE)
        feasibility_ids = await get_dict_ids(DictionaryType.FEASIBILITY)
        block_ids = await get_dict_ids(DictionaryType.BLOCK)

        # Get users for recruiter / co_recruiter
        res_u = await db.execute(select(User).limit(5))
        users = res_u.scalars().all()
        user_ids = [u.id for u in users]

    print(f"Dictionaries loaded: levels={len(level_ids)}, statuses={len(status_ids)}, roles={len(it_role_ids)}, blocks={len(block_ids)}")
    print(f"Users loaded: {len(user_ids)}")

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # -------------------------------------------------------------
        # STEP 1: Create a test vacancy
        # -------------------------------------------------------------
        print("\n--- [STEP 1] Create Test Vacancy ---")
        create_payload = {
            "position_name": "History Test Vacancy",
            "quantity": 1,
            "status_id": status_ids[0] if status_ids else None,
            "comment": "Начальный комментарий",
            "offer_rejection_reason": "Начальная причина отказа",
            "team_lead_text": "Иванов Иван",
            "city_text": "Москва",
        }
        r = await client.post("/api/vacancies", json=create_payload, headers=headers)
        assert r.status_code == 201 or r.status_code == 200, f"Create vacancy failed: {r.status_code} {r.text}"
        vac = r.json()
        vac_id = vac["id"]
        print(f"  ✓ Created test vacancy id={vac_id}")

        # Check initial history entry
        r = await client.get(f"/api/vacancies/{vac_id}/history", headers=headers)
        assert r.status_code == 200, f"Get history failed: {r.text}"
        hist = r.json()
        assert len(hist) >= 1
        create_entry = hist[-1]
        assert create_entry["action_type"] == "CREATE"
        print(f"  ✓ Found CREATE history entry with {len(create_entry['changes'])} recorded fields")

        # -------------------------------------------------------------
        # STEP 2: Test Comment modification, addition and clearing
        # -------------------------------------------------------------
        print("\n--- [STEP 2] Test 'comment' (Комментарий) recording ---")
        # 2.1 Update comment
        r = await client.patch(f"/api/vacancies/{vac_id}", json={"comment": "Кандидат думает до пятницы"}, headers=headers)
        assert r.status_code == 200, f"Update comment failed: {r.text}"

        r = await client.get(f"/api/vacancies/{vac_id}/history", headers=headers)
        hist = r.json()
        latest = hist[0]
        assert "Комментарий" in latest["changes"], f"Комментарий missing from changes: {latest['changes']}"
        assert latest["changes"]["Комментарий"]["old"] == "Начальный комментарий"
        assert latest["changes"]["Комментарий"]["new"] == "Кандидат думает до пятницы"
        print(f"  ✓ Comment update recorded: {latest['changes']['Комментарий']}")

        # 2.2 Clear comment
        r = await client.patch(f"/api/vacancies/{vac_id}", json={"comment": ""}, headers=headers)
        assert r.status_code == 200
        r = await client.get(f"/api/vacancies/{vac_id}/history", headers=headers)
        latest = r.json()[0]
        assert "Комментарий" in latest["changes"]
        assert latest["changes"]["Комментарий"]["old"] == "Кандидат думает до пятницы"
        assert latest["changes"]["Комментарий"]["new"] == "—"
        print(f"  ✓ Comment clearing recorded: {latest['changes']['Комментарий']}")

        # -------------------------------------------------------------
        # STEP 3: Test Offer Rejection Reason modification and clearing
        # -------------------------------------------------------------
        print("\n--- [STEP 3] Test 'offer_rejection_reason' (Причина отказа от оффера) ---")
        # 3.1 Update offer rejection reason
        r = await client.patch(f"/api/vacancies/{vac_id}", json={"offer_rejection_reason": "Не устроила заработная плата"}, headers=headers)
        assert r.status_code == 200, f"Update rejection failed: {r.text}"

        r = await client.get(f"/api/vacancies/{vac_id}/history", headers=headers)
        latest = r.json()[0]
        assert "Причина отказа от оффера" in latest["changes"], f"Rejection reason missing: {latest['changes']}"
        assert latest["changes"]["Причина отказа от оффера"]["old"] == "Начальная причина отказа"
        assert latest["changes"]["Причина отказа от оффера"]["new"] == "Не устроила заработная плата"
        print(f"  ✓ Rejection reason update recorded: {latest['changes']['Причина отказа от оффера']}")

        # 3.2 Clear rejection reason
        r = await client.patch(f"/api/vacancies/{vac_id}", json={"offer_rejection_reason": None}, headers=headers)
        assert r.status_code == 200
        r = await client.get(f"/api/vacancies/{vac_id}/history", headers=headers)
        latest = r.json()[0]
        assert "Причина отказа от оффера" in latest["changes"]
        assert latest["changes"]["Причина отказа от оффера"]["old"] == "Не устроила заработная плата"
        assert latest["changes"]["Причина отказа от оффера"]["new"] == "—"
        print(f"  ✓ Rejection reason clearing recorded: {latest['changes']['Причина отказа от оффера']}")

        # -------------------------------------------------------------
        # STEP 4: Test Funnel metrics (Действия / Воронка)
        # -------------------------------------------------------------
        print("\n--- [STEP 4] Test Funnel Columns (Воронка / Действия) ---")
        funnel_tests = [
            ("resume_at_customer", 5, "Передано заказчику"),
            ("resume_approved", 3, "Резюме одобрено"),
            ("interviews_plan", 4, "Собеседования план"),
            ("interviews_fact", 2, "Собеседования факт"),
            ("offer_made", 1, "Оффер сделан"),
            ("offer_accepted", 1, "Оффер принят"),
        ]
        for field, new_val, label in funnel_tests:
            r = await client.patch(f"/api/vacancies/{vac_id}", json={field: new_val}, headers=headers)
            assert r.status_code == 200, f"Failed updating {field}: {r.text}"
            r = await client.get(f"/api/vacancies/{vac_id}/history", headers=headers)
            latest = r.json()[0]
            assert label in latest["changes"], f"{label} missing from history changes: {latest['changes']}"
            assert latest["changes"][label]["new"] == str(new_val)
            print(f"  ✓ Funnel field '{field}' ({label}) recorded: {latest['changes'][label]}")

        # -------------------------------------------------------------
        # STEP 5: Test All Other Columns One by One
        # -------------------------------------------------------------
        print("\n--- [STEP 5] Test All Remaining Vacancy Columns ---")
        columns_to_test = [
            ("position_name", "Senior Python / React Fullstack", "Должность"),
            ("quantity", 3, "Количество вакансий"),
            ("salary_gross", 350000, "Зарплата (Gross)"),
            ("hold_days", 14, "Дней в холде"),
            ("candidate_name", "Алексеев Алексей Алексеевич", "ФИО кандидата"),
            ("candidate_company", "ПАО Ростелеком", "Компания кандидата"),
            ("ex_employee_name", "Сидоров Сидор", "ФИО бывшего сотрудника"),
            ("unit_id", "UNIT-9988", "ID ШЕ"),
            ("iqhr_link", "https://iqhr.example.com/request/12345", "Ссылка IQHR"),
            ("close_date", "2026-12-31", "Дата закрытия"),
            ("team_lead_text", "Петров Петр Сергеевич", "Тимлид"),
            ("city_text", "Санкт-Петербург", "Город"),
        ]

        if len(status_ids) > 1:
            columns_to_test.append(("status_id", status_ids[1], "Статус вакансии"))
        if level_ids:
            columns_to_test.append(("level_id", level_ids[0], "Уровень специалиста"))
        if it_role_ids:
            columns_to_test.append(("it_role_id", it_role_ids[0], "ИТ роль"))
        if admin_manager_ids:
            columns_to_test.append(("admin_manager_id", admin_manager_ids[0], "Административный руководитель"))
        if project_ids:
            columns_to_test.append(("project_id", project_ids[0], "Проект"))
        if source_ids:
            columns_to_test.append(("source_id", source_ids[0], "Источник найма"))
        if transfer_ids:
            columns_to_test.append(("internal_transfer_id", transfer_ids[0], "Внутренний перевод"))
        if replacement_ids:
            columns_to_test.append(("replacement_type_id", replacement_ids[0], "Новая/Замена"))
        if employment_ids:
            columns_to_test.append(("employment_type_id", employment_ids[0], "Вид занятости"))
        if feasibility_ids:
            columns_to_test.append(("feasibility_id", feasibility_ids[0], "ТЭО проекта"))
        if block_ids:
            columns_to_test.append(("block_id", block_ids[0], "Блок"))
        if len(user_ids) > 1:
            columns_to_test.append(("recruiter_id", user_ids[0], "Рекрутер"))
            columns_to_test.append(("co_recruiter_id", user_ids[1], "Дополнительный рекрутер"))

        passed_columns = 0
        for field, new_val, expected_label in columns_to_test:
            r = await client.patch(f"/api/vacancies/{vac_id}", json={field: new_val}, headers=headers)
            assert r.status_code == 200, f"Failed updating {field}={new_val}: {r.text}"
            r = await client.get(f"/api/vacancies/{vac_id}/history", headers=headers)
            latest = r.json()[0]
            assert expected_label in latest["changes"], f"Expected label '{expected_label}' for field '{field}' not found in changes: {latest['changes']}"
            change = latest["changes"][expected_label]
            assert change["new"] != "—" and change["new"] != change["old"], f"Unexpected change payload: {change}"
            print(f"  ✓ Column '{field}' ({expected_label}) recorded: {change['old']} → {change['new']}")
            passed_columns += 1

        print(f"\n  ===> Successfully verified {passed_columns} standard vacancy columns!")

        # -------------------------------------------------------------
        # STEP 6: Test Weekly Reports Router (Comment and Rejection Reason)
        # -------------------------------------------------------------
        print("\n--- [STEP 6] Test Weekly Reports Comment and Rejection Reason ---")
        curr_week = date.today().isocalendar()[1]
        curr_year = date.today().isocalendar()[0]

        report_payload = {
            "vacancy_id": vac_id,
            "week_number": curr_week,
            "year": curr_year,
            "resumes_sent": 2,
            "candidates_agreed": 2,
            "interviews_planned": 1,
            "interviews_conducted": 1,
            "offer_made": 1,
            "offer_accepted": 0,
            "offer_rejection_reason": "Кандидат выбрал другой оффер",
            "comment": "Отчёт за текущую неделю по вакансии",
        }
        r = await client.post("/api/reports", json=report_payload, headers=headers)
        if r.status_code == 400 and "уже существует" in r.text:
            # Report already exists, get it and patch it
            r_get = await client.get(f"/api/reports/vacancy/{vac_id}", headers=headers)
            rep_id = r_get.json()["items"][0]["id"]
            r_rep = await client.patch(f"/api/reports/{rep_id}", json={
                "offer_rejection_reason": "Кандидат выбрал другой оффер",
                "comment": "Обновленный отчёт за текущую неделю",
            }, headers=headers)
            assert r_rep.status_code == 200, f"Update report failed: {r_rep.text}"
            print("  ✓ Weekly report updated with comment and offer rejection reason")
        else:
            assert r.status_code == 200 or r.status_code == 201, f"Create report failed: {r.status_code} {r.text}"
            print("  ✓ Weekly report created with comment and offer rejection reason")

        # Verify history includes the report and offer rejection reason
        r = await client.get(f"/api/vacancies/{vac_id}/history", headers=headers)
        assert r.status_code == 200
        hist = r.json()
        report_entries = [h for h in hist if h["action_type"] in ("REPORT", "OFFER_REJECTION")]
        assert len(report_entries) >= 1, f"No report entries in history: {[h['action_type'] for h in hist]}"
        print(f"  ✓ Found {len(report_entries)} REPORT/OFFER_REJECTION entries in history")

        # -------------------------------------------------------------
        # STEP 7: Cleanup test vacancy
        # -------------------------------------------------------------
        print("\n--- [STEP 7] Cleanup Test Vacancy ---")
        r = await client.delete(f"/api/vacancies/{vac_id}", headers=headers)
        assert r.status_code == 204 or r.status_code == 200, f"Delete failed: {r.text}"
        print(f"  ✓ Deleted test vacancy id={vac_id}")

    print("\n" + "=" * 70)
    print("ALL HISTORY TESTS PASSED SUCCESSFULLY! 100% VERIFIED!")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_history_tests())
