import asyncio
import httpx
from datetime import timedelta
from auth import create_access_token

async def test():
    # 1. Token for Yuliya and Irek
    yuliya_token = create_access_token({'sub': 'Yuliya.e.novikova@rt.ru', 'role': 'superadmin'}, expires_delta=timedelta(hours=1))
    irek_token = create_access_token({'sub': 'irek.nasibullin@rt.ru', 'role': 'superadmin'}, expires_delta=timedelta(hours=1))
    # 2. Token for another recruiter (e.g. as@as.as)
    other_token = create_access_token({'sub': 'as@as.as', 'role': 'recruiter'}, expires_delta=timedelta(hours=1))

    async with httpx.AsyncClient(base_url='http://127.0.0.1:8000') as client:
        # Check unauthorized user
        r_other = await client.get('/api/notifications/smtp-settings', headers={'Authorization': f'Bearer {other_token}'})
        print('Other user (as@as.as) access test:', r_other.status_code, r_other.json())
        assert r_other.status_code == 403, f'Expected 403, got {r_other.status_code}'

        r_other_send = await client.post('/api/notifications/smtp-send-test', json={}, headers={'Authorization': f'Bearer {other_token}'})
        print('Other user send test email:', r_other_send.status_code)
        assert r_other_send.status_code == 403, f'Expected 403, got {r_other_send.status_code}'

        # Check Yuliya
        r_yuliya = await client.get('/api/notifications/smtp-settings', headers={'Authorization': f'Bearer {yuliya_token}'})
        print('Yuliya GET /api/notifications/smtp-settings:', r_yuliya.status_code, r_yuliya.json())
        assert r_yuliya.status_code == 200, f'Expected 200, got {r_yuliya.status_code}'

        # Check Irek
        r_irek = await client.get('/api/notifications/smtp-settings', headers={'Authorization': f'Bearer {irek_token}'})
        print('Irek GET /api/notifications/smtp-settings:', r_irek.status_code, r_irek.json())
        assert r_irek.status_code == 200, f'Expected 200, got {r_irek.status_code}'
        y_data = r_yuliya.json()
        assert 'smtp_server' in y_data
        assert 'connected' in y_data
        print(f"SMTP Server: {y_data.get('smtp_server')}, Port: {y_data.get('smtp_port')}, Connected: {y_data.get('connected')}, Msg: {y_data.get('connection_message')}")

        # Check Yuliya connection test endpoint
        r_conn = await client.post('/api/notifications/smtp-test-connection', json={}, headers={'Authorization': f'Bearer {yuliya_token}'})
        print('Yuliya POST /api/notifications/smtp-test-connection:', r_conn.status_code, r_conn.json())
        assert r_conn.status_code == 200, f'Expected 200, got {r_conn.status_code}'

    print('=== ALL SMTP PERMISSION & ENDPOINT TESTS PASSED ON SERVER! ===')

if __name__ == '__main__':
    asyncio.run(test())
