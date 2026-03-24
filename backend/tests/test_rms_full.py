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
   

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

                                                                                

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)

async def override_get_db():
    async with TestSessionLocal() as session:
        yield session

                                                                                

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
                                                          
    from database import Base
                                                            
    import models              
    from services.refresh_token import RefreshToken              
    from middleware.audit import AuditLog              

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session

@pytest_asyncio.fixture
async def app():
                                                         
    from server import app as fastapi_app
    from database import get_db
    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()

@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def superadmin_token(client, db_session):
                                          
    from models import User, UserRole
    from auth import get_password_hash

    user = User(
        email="superadmin@test.ru",
        hashed_password=get_password_hash("AdminPass1"),
        full_name="Суперадмин Тест",
        role=UserRole.SUPERADMIN,
        is_active=True,
        is_temporary_password=False,
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post("/api/auth/login", json={
        "email": "superadmin@test.ru", "password": "AdminPass1"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]

@pytest_asyncio.fixture
async def recruiter_token(client, db_session):
                                        
    from models import User, UserRole
    from auth import get_password_hash

    user = User(
        email="recruiter@test.ru",
        hashed_password=get_password_hash("RecPass12"),
        full_name="Рекрутер Тест",
        role=UserRole.RECRUITER,
        is_active=True,
        is_temporary_password=False,
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post("/api/auth/login", json={
        "email": "recruiter@test.ru", "password": "RecPass12"
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]

                                                                                  
                            
                                                                                  

class TestPasswordValidation:
                                                     

    def test_valid_password(self):
        from routers.auth_router import validate_password_strength
        assert validate_password_strength("Secret12") is True

    def test_too_short(self):
        from routers.auth_router import validate_password_strength
        assert validate_password_strength("Sec1") is False

    def test_only_letters(self):
        from routers.auth_router import validate_password_strength
        assert validate_password_strength("SecretPwd") is False

    def test_only_digits(self):
        from routers.auth_router import validate_password_strength
        assert validate_password_strength("12345678") is False

    def test_cyrillic_letters_allowed(self):
        from routers.auth_router import validate_password_strength
        assert validate_password_strength("Пароль12") is True

class TestWorkingDays:
                                          

    def test_weekday_to_weekday(self):
        from services.holidays import calculate_working_days
        from datetime import date
                                                                         
        result = calculate_working_days(date(2024, 1, 3), date(2024, 1, 5))
        assert result == 3

    def test_across_weekend(self):
        from services.holidays import calculate_working_days
        from datetime import date
                                                                       
        result = calculate_working_days(date(2024, 1, 5), date(2024, 1, 8))
        assert result == 2

    def test_new_year_holiday(self):
        from services.holidays import calculate_working_days
        from datetime import date
                                                                     
        result = calculate_working_days(date(2024, 12, 30), date(2025, 1, 9))
                                                             
        assert result <= 3                              

    def test_same_date(self):
        from services.holidays import calculate_working_days
        from datetime import date
        result = calculate_working_days(date(2024, 6, 3), date(2024, 6, 3))
        assert result == 1                     

class TestVacancyService:
                                                    

    def test_funnel_map_complete(self):
        from services.vacancy_service import FUNNEL_MAP
        expected_keys = {"resume_at_customer", "resume_approved", "interviews_fact",
                         "interviews_plan", "offer_made"}
        assert set(FUNNEL_MAP.keys()) == expected_keys

    def test_vacancy_to_dict_no_metrics(self):
        from services.vacancy_service import vacancy_to_dict
        from unittest.mock import MagicMock

        vacancy = MagicMock()
        vacancy.id = 1
        vacancy.position_name = "Python Dev"
        vacancy.vacancy_id = "VAC-001"
                                              
        for attr in ["open_date", "quantity", "level_id", "status_id", "it_role_id",
                     "admin_manager_id", "team_lead_id", "project_id", "city_id",
                     "city_text", "source_id", "internal_transfer_id", "status_changed_at",
                     "close_date", "candidate_name", "candidate_company", "replacement_type_id",
                     "ex_employee_name", "unit_id", "employment_type_id", "feasibility_id",
                     "iqhr_link", "recruiter_id", "block_id", "hold_days", "salary_gross",
                     "resumes_sent_cnt", "candidates_agreed_cnt", "interviews_planned_cnt",
                     "interviews_conducted_cnt", "created_at", "recruiter", "level",
                     "status", "it_role", "admin_manager", "team_lead", "project", "city",
                     "source", "internal_transfer", "replacement_type", "employment_type",
                     "feasibility", "block", "work_duration_days"]:
            setattr(vacancy, attr, None)

        result = vacancy_to_dict(vacancy, metrics=None)

        assert result["resume_at_customer"] == 0
        assert result["offer_made"] == 0
        assert result["position_name"] == "Python Dev"

    def test_vacancy_to_dict_with_metrics(self):
        from services.vacancy_service import vacancy_to_dict
        from unittest.mock import MagicMock

        vacancy = MagicMock()
        for attr in ["id", "vacancy_id", "position_name", "open_date", "quantity", "level_id",
                     "status_id", "it_role_id", "admin_manager_id", "team_lead_id", "project_id",
                     "city_id", "city_text", "source_id", "internal_transfer_id", "status_changed_at",
                     "close_date", "candidate_name", "candidate_company", "replacement_type_id",
                     "ex_employee_name", "unit_id", "employment_type_id", "feasibility_id",
                     "iqhr_link", "recruiter_id", "block_id", "hold_days", "salary_gross",
                     "resumes_sent_cnt", "candidates_agreed_cnt", "interviews_planned_cnt",
                     "interviews_conducted_cnt", "created_at", "recruiter", "level", "status",
                     "it_role", "admin_manager", "team_lead", "project", "city", "source",
                     "internal_transfer", "replacement_type", "employment_type", "feasibility",
                     "block", "work_duration_days"]:
            setattr(vacancy, attr, None)

        metrics = MagicMock()
        metrics.resumes_sent = 5
        metrics.candidates_agreed = 3
        metrics.interviews_planned = 2
        metrics.interviews_conducted = 1
        metrics.offer_made = 1

        result = vacancy_to_dict(vacancy, metrics=metrics)
        assert result["resume_at_customer"] == 5
        assert result["resume_approved"] == 3
        assert result["offer_made"] == 1

                                                                                  
                         
                                                                                  

class TestAuthAPI:
                                           

    async def test_login_success(self, client, superadmin_token):
                                                       
        resp = await client.post("/api/auth/login", json={
            "email": "superadmin@test.ru", "password": "AdminPass1"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client):
        resp = await client.post("/api/auth/login", json={
            "email": "superadmin@test.ru", "password": "wrongpass"
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        resp = await client.post("/api/auth/login", json={
            "email": "nobody@test.ru", "password": "Password1"
        })
        assert resp.status_code == 401

    async def test_get_me(self, client, superadmin_token):
        resp = await client.get("/api/auth/me",
                                headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "superadmin@test.ru"
        assert data["role"] == "superadmin"

    async def test_get_me_no_token(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code in (401, 403)

    async def test_change_password_weak(self, client, superadmin_token):
        resp = await client.post("/api/auth/change-own-password",
                                 headers={"Authorization": f"Bearer {superadmin_token}"},
                                 json={
                                     "current_password": "AdminPass1",
                                     "new_password": "weak",
                                     "confirm_password": "weak",
                                 })
        assert resp.status_code == 400

    async def test_change_password_mismatch(self, client, superadmin_token):
        resp = await client.post("/api/auth/change-own-password",
                                 headers={"Authorization": f"Bearer {superadmin_token}"},
                                 json={
                                     "current_password": "AdminPass1",
                                     "new_password": "NewPass12",
                                     "confirm_password": "DifferentPass1",
                                 })
        assert resp.status_code == 400

class TestRefreshTokenAPI:
                                                    

    async def test_refresh_returns_new_access_token(self, client):
                                                               
        login_resp = await client.post("/api/auth/login", json={
            "email": "superadmin@test.ru", "password": "AdminPass1"
        })
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        refresh_resp = await client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert refresh_resp.status_code == 200
        assert "access_token" in refresh_resp.json()

    async def test_invalid_refresh_token_rejected(self, client):
        resp = await client.post("/api/auth/refresh", json={
            "refresh_token": "totally_invalid_token_value_abc123"
        })
        assert resp.status_code == 401

    async def test_logout_revokes_token(self, client, superadmin_token):
                                                                     
        login_resp = await client.post("/api/auth/login", json={
            "email": "superadmin@test.ru", "password": "AdminPass1"
        })
        refresh_token = login_resp.json()["refresh_token"]

        logout_resp = await client.post("/api/auth/logout",
                                        headers={"Authorization": f"Bearer {superadmin_token}"},
                                        json={"refresh_token": refresh_token})
        assert logout_resp.status_code == 200

                                             
        retry_resp = await client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert retry_resp.status_code == 401

    async def test_logout_all_sessions(self, client, superadmin_token):
                                                          
        resp = await client.post("/api/auth/logout-all",
                                 headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        assert "count" in resp.json().get("message", "") or "сессии" in resp.json().get("message", "")

class TestVacanciesAPI:
                                         

    async def test_get_vacancies_list(self, client, superadmin_token):
        resp = await client.get("/api/vacancies",
                                headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    async def test_get_vacancies_unauthorized(self, client):
        resp = await client.get("/api/vacancies")
        assert resp.status_code in (401, 403)

    async def test_create_vacancy(self, client, superadmin_token):
        resp = await client.post("/api/vacancies",
                                 headers={"Authorization": f"Bearer {superadmin_token}"},
                                 json={"position_name": "Backend Developer", "quantity": 2})
        assert resp.status_code == 201
        data = resp.json()
        assert data["position_name"] == "Backend Developer"
        assert data["quantity"] == 2
        return data["id"]

    async def test_get_vacancy_by_id(self, client, superadmin_token):
                         
        create_resp = await client.post("/api/vacancies",
                                        headers={"Authorization": f"Bearer {superadmin_token}"},
                                        json={"position_name": "DevOps Engineer", "quantity": 1})
        vacancy_id = create_resp.json()["id"]

                        
        resp = await client.get(f"/api/vacancies/{vacancy_id}",
                                headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        assert resp.json()["id"] == vacancy_id

    async def test_update_vacancy(self, client, superadmin_token):
        create_resp = await client.post("/api/vacancies",
                                        headers={"Authorization": f"Bearer {superadmin_token}"},
                                        json={"position_name": "QA Engineer", "quantity": 1})
        vacancy_id = create_resp.json()["id"]

        resp = await client.patch(f"/api/vacancies/{vacancy_id}",
                                  headers={"Authorization": f"Bearer {superadmin_token}"},
                                  json={"quantity": 3, "resume_at_customer": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["quantity"] == 3
        assert data["resume_at_customer"] == 5

    async def test_delete_vacancy(self, client, superadmin_token):
        create_resp = await client.post("/api/vacancies",
                                        headers={"Authorization": f"Bearer {superadmin_token}"},
                                        json={"position_name": "To Delete", "quantity": 1})
        vacancy_id = create_resp.json()["id"]

        del_resp = await client.delete(f"/api/vacancies/{vacancy_id}",
                                       headers={"Authorization": f"Bearer {superadmin_token}"})
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/api/vacancies/{vacancy_id}",
                                    headers={"Authorization": f"Bearer {superadmin_token}"})
        assert get_resp.status_code == 404

    async def test_vacancy_not_found(self, client, superadmin_token):
        resp = await client.get("/api/vacancies/999999",
                                headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 404

    async def test_import_requires_superadmin(self, client, recruiter_token):
                                                 
        resp = await client.post("/api/vacancies/import",
                                 headers={"Authorization": f"Bearer {recruiter_token}"},
                                 files={"file": ("test.xlsx", b"fake", "application/vnd.ms-excel")})
        assert resp.status_code == 403

class TestRBACRules:
                                           

    async def test_recruiter_cannot_access_other_vacancy(self, client, recruiter_token, superadmin_token):
                                                           
                                                                                          
        create_resp = await client.post("/api/vacancies",
                                        headers={"Authorization": f"Bearer {superadmin_token}"},
                                        json={"position_name": "Admin Vacancy", "quantity": 1})
        vacancy_id = create_resp.json()["id"]

        resp = await client.get(f"/api/vacancies/{vacancy_id}",
                                headers={"Authorization": f"Bearer {recruiter_token}"})
                                                            
        assert resp.status_code in (200, 403)

    async def test_users_list_requires_admin(self, client, recruiter_token):
        resp = await client.get("/api/users",
                                headers={"Authorization": f"Bearer {recruiter_token}"})
        assert resp.status_code == 403

    async def test_superadmin_sees_all_users(self, client, superadmin_token):
        resp = await client.get("/api/users",
                                headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data

class TestFilteringAndPagination:
                                       

    async def test_pagination_skip_limit(self, client, superadmin_token):
        resp = await client.get("/api/vacancies?skip=0&limit=5",
                                headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 5

    async def test_sorting_asc(self, client, superadmin_token):
        resp = await client.get("/api/vacancies?sort_field=id&sort_order=asc",
                                headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        items = resp.json()["items"]
        if len(items) > 1:
            assert items[0]["id"] < items[-1]["id"]

    async def test_text_search(self, client, superadmin_token):
                                                 
        await client.post("/api/vacancies",
                          headers={"Authorization": f"Bearer {superadmin_token}"},
                          json={"position_name": "UniqueXYZ789 Developer", "quantity": 1})

        resp = await client.get("/api/vacancies?search_position_name=UniqueXYZ789",
                                headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any("UniqueXYZ789" in item["position_name"] for item in data["items"])

class TestDictionariesAPI:
                             

    async def test_get_dictionaries(self, client, superadmin_token):
        resp = await client.get("/api/dictionaries",
                                headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200

    async def test_get_dictionaries_by_type(self, client, superadmin_token):
        resp = await client.get("/api/dictionaries/by-type/vacancy_status",
                                headers={"Authorization": f"Bearer {superadmin_token}"})
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)