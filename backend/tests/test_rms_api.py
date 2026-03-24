\
\
\
   
import pytest
import requests
import os

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:8000/api').rstrip('/')

class TestAuth:
                                       
    
    def test_login_success(self):
                                            
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@rms-system.ru",
            "password": "admin123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    
    def test_login_invalid_credentials(self):
                                                  
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "invalid@test.ru",
            "password": "wrongpassword"
        })
        assert response.status_code == 401

class TestVacancies:
                            
    
    @pytest.fixture
    def auth_headers(self):
                                        
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@rms-system.ru",
            "password": "admin123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_vacancies(self, auth_headers):
                                          
        response = requests.get(f"{BASE_URL}/api/vacancies?skip=0&limit=100", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

class TestDictionaries:
                                   
    
    @pytest.fixture
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@rms-system.ru",
            "password": "admin123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_dictionaries_specialist_level(self, auth_headers):
                                                                       
        response = requests.get(
            f"{BASE_URL}/api/dictionaries?type=specialist_level&skip=0&limit=500",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    
    def test_get_dictionary_by_type(self, auth_headers):
                                              
        response = requests.get(
            f"{BASE_URL}/api/dictionaries/by-type/vacancy_status",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

class TestUsers:
                             
    
    @pytest.fixture
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@rms-system.ru",
            "password": "admin123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_get_users(self, auth_headers):
                                                      
        response = requests.get(f"{BASE_URL}/api/users?skip=0&limit=100", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) > 0

class TestExport:
                                                             
    
    @pytest.fixture
    def auth_headers(self):
        response = requests.post(f"{BASE_URL}/api/auth/login", json={
            "email": "admin@rms-system.ru",
            "password": "admin123"
        })
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}
    
    def test_export_vacancies_all_time(self, auth_headers):
                                                                            
        response = requests.get(
            f"{BASE_URL}/api/export/vacancies?period=all_time",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers.get("Content-Type", "")
                                                         
        content_disp = response.headers.get("Content-Disposition", "")
        assert "attachment" in content_disp
                                                                             
        assert "vacancies_" in content_disp
    
    def test_export_vacancies_current_month(self, auth_headers):
                                                   
        response = requests.get(
            f"{BASE_URL}/api/export/vacancies?period=current_month",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "spreadsheetml.sheet" in response.headers.get("Content-Type", "")
    
    def test_export_vacancies_current_week(self, auth_headers):
                                                  
        response = requests.get(
            f"{BASE_URL}/api/export/vacancies?period=current_week",
            headers=auth_headers
        )
        assert response.status_code == 200
        assert "spreadsheetml.sheet" in response.headers.get("Content-Type", "")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
