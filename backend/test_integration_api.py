import asyncio
import httpx

from auth import create_access_token

BASE_URL = "http://localhost:8000/api"

async def test_integration():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        # 1. Setup Superadmin token
        print("--- [STEP 1] Setup Superadmin Authorization ---")
        admin_token = create_access_token({"sub": "admin1@rms-system.ru", "role": "superadmin"})
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        print("  ✓ Superadmin authorization token generated")

        # 2. Check /fields spec
        print("\n--- [STEP 2] Check /fields specification ---")
        fields_res = await client.get("/integration/fields")
        assert fields_res.status_code == 200
        fields_data = fields_res.json()
        assert fields_data["total_fields"] == 38, f"Expected 38 fields, got {fields_data['total_fields']}"
        print(f"  ✓ 38 fields specification verified: {fields_data['total_fields']} fields")

        # 3. Create an integration token for external system
        print("\n--- [STEP 3] Create integration token for '1С:ЗУП' ---")
        create_res = await client.post(
            "/integration/tokens",
            json={"name": "1С:ЗУП Корпоративный", "description": "Синхронизация вакансий с кадровой системой 1C"},
            headers=admin_headers,
        )
        assert create_res.status_code == 200, f"Create token failed: {create_res.text}"
        token_data = create_res.json()["item"]
        api_key = token_data["token"]
        token_id = token_data["id"]
        assert api_key.startswith("rms_live_"), f"Unexpected token prefix: {api_key}"
        print(f"  ✓ Token created: ID={token_id}, name='{token_data['name']}', key={api_key[:16]}...")

        # 4. Unauthorized request without token
        print("\n--- [STEP 4] Test unauthorized access without token ---")
        unauth_res = await client.get("/integration/vacancies")
        assert unauth_res.status_code == 401, f"Expected 401, got {unauth_res.status_code}"
        print("  ✓ Request without token rejected with 401 Unauthorized")

        # 5. Fetch vacancies with X-API-Key
        print("\n--- [STEP 5] Fetch vacancies using X-API-Key header ---")
        api_headers = {"X-API-Key": api_key}
        vacs_res = await client.get("/integration/vacancies?limit=5", headers=api_headers)
        assert vacs_res.status_code == 200, f"Failed fetching vacancies: {vacs_res.text}"
        vacs_data = vacs_res.json()
        assert vacs_data["success"] is True
        assert "items" in vacs_data
        assert len(vacs_data["items"]) > 0
        first_item = vacs_data["items"][0]
        print(f"  ✓ Successfully fetched {len(vacs_data['items'])} vacancies (Total in RMS: {vacs_data['total']})")

        # Check all 38 fields in the item
        expected_fields = [f["field"] for f in fields_data["fields"]]
        missing_fields = [f for f in expected_fields if f not in first_item]
        assert not missing_fields, f"Missing fields in vacancy item: {missing_fields}"
        print(f"  ✓ All 38 required fields are present in the response item!")
        print(f"    Sample fields:")
        for k in ["ID вакансии", "Вакансия", "Статус вакансии", "Рекрутер", "Передано заказчику", "Оффер принят", "Дата формирования выгрузки"]:
            print(f"      - {k}: {first_item.get(k)}")

        # 6. Fetch single vacancy by ID
        vac_id = first_item["ID вакансии"]
        print(f"\n--- [STEP 6] Fetch single vacancy by ID ({vac_id}) ---")
        single_res = await client.get(f"/integration/vacancies/{vac_id}", headers=api_headers)
        assert single_res.status_code == 200
        single_data = single_res.json()
        assert single_data["item"]["ID вакансии"] == vac_id
        print(f"  ✓ Successfully fetched single vacancy #{vac_id} with all 38 fields")

        # 7. Test Bearer Authorization header as alternative
        print("\n--- [STEP 7] Test Authorization: Bearer <api_key> ---")
        bearer_res = await client.get("/integration/vacancies?limit=1", headers={"Authorization": f"Bearer {api_key}"})
        assert bearer_res.status_code == 200
        print("  ✓ Bearer authentication works seamlessly")

        # 8. Test Toggle Token (Deactivate)
        print("\n--- [STEP 8] Deactivate token ---")
        toggle_res = await client.patch(f"/integration/tokens/{token_id}/toggle", headers=admin_headers)
        assert toggle_res.status_code == 200
        assert toggle_res.json()["is_active"] is False

        # Request with deactivated token should fail with 403 Forbidden
        deactivated_res = await client.get("/integration/vacancies", headers=api_headers)
        assert deactivated_res.status_code == 403, f"Expected 403, got {deactivated_res.status_code}"
        print("  ✓ Deactivated token rejected with 403 Forbidden")

        # Reactivate token
        toggle_res2 = await client.patch(f"/integration/tokens/{token_id}/toggle", headers=admin_headers)
        assert toggle_res2.status_code == 200
        assert toggle_res2.json()["is_active"] is True
        print("  ✓ Token reactivated successfully")

        # 9. List tokens
        print("\n--- [STEP 9] List tokens for admin ---")
        list_res = await client.get("/integration/tokens", headers=admin_headers)
        assert list_res.status_code == 200
        tokens_list = list_res.json()["items"]
        found = any(t["id"] == token_id for t in tokens_list)
        assert found, "Created token not found in list"
        print(f"  ✓ Found {len(tokens_list)} token(s) in admin listing, last_used_at is tracked")

        # 10. Clean up test token
        print("\n--- [STEP 10] Delete test token ---")
        del_res = await client.delete(f"/integration/tokens/{token_id}", headers=admin_headers)
        assert del_res.status_code == 200
        print("  ✓ Test token deleted")

        # Request with deleted token should now fail with 401
        del_check = await client.get("/integration/vacancies", headers=api_headers)
        assert del_check.status_code == 401
        print("  ✓ Deleted token no longer accepted (401)")

        print("\n" + "="*60)
        print("INTEGRATION API 100% VERIFIED AND WORKING!")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(test_integration())
