import asyncio
from database import AsyncSessionLocal
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from models import Vacancy
from routers.export_router import build_excel_from_vacancies

async def main():
    async with AsyncSessionLocal() as db:
        query = select(Vacancy).options(
            selectinload(Vacancy.recruiter),
            selectinload(Vacancy.level),
            selectinload(Vacancy.status),
            selectinload(Vacancy.it_role),
            selectinload(Vacancy.admin_manager),
            selectinload(Vacancy.team_lead),
            selectinload(Vacancy.project),
            selectinload(Vacancy.city),
            selectinload(Vacancy.source),
            selectinload(Vacancy.internal_transfer),
            selectinload(Vacancy.replacement_type),
            selectinload(Vacancy.employment_type),
            selectinload(Vacancy.feasibility),
            selectinload(Vacancy.block),
            selectinload(Vacancy.weekly_reports),
        )
        result = await db.execute(query)
        vacancies = result.scalars().all()
        print(f"Loaded {len(vacancies)} vacancies")
        try:
            out, fname = build_excel_from_vacancies(vacancies, "all_time")
            print("Export ok!", fname)
        except Exception as e:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
