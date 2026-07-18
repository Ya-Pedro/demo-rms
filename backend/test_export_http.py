import httpx
import asyncio
from auth import create_access_token

async def main():
    token = create_access_token({"sub": "admin1@rms-system.ru", "role": "superadmin"})
    
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "http://localhost:8000/api/export/vacancies",
            params={"period": "all_time"},
            headers={"Authorization": f"Bearer {token}"}
        )
        print("Status:", res.status_code)
        if res.status_code != 200:
            print("Error body:", res.text)
        else:
            print("Success, headers:", res.headers)
            
if __name__ == "__main__":
    asyncio.run(main())
