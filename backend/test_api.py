import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from database import async_session_maker
from models import User
from auth import create_access_token
import httpx

async def main():
    async with async_session_maker() as db:
        # Just create a fake token for admin1
        token = create_access_token({"sub": "admin1@rms-system.ru", "role": "superadmin"})
        
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "http://localhost:8000/api/dashboards/metrics",
            headers={"Authorization": f"Bearer {token}"}
        )
        print("Status:", res.status_code)
        if res.status_code == 500:
            print("Error:", res.text)
        elif res.status_code == 200:
            print("Success! Data length:", len(res.text))

asyncio.run(main())
