\
\
\
   
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import User, Vacancy, WeeklyReport, UserRole

                                                 
VACANCY_LOAD_OPTIONS = [
    selectinload(Vacancy.recruiter),
    selectinload(Vacancy.level),
    selectinload(Vacancy.status),
    selectinload(Vacancy.it_role),
    selectinload(Vacancy.admin_manager),
    selectinload(Vacancy.project),
    selectinload(Vacancy.source),
    selectinload(Vacancy.internal_transfer),
    selectinload(Vacancy.replacement_type),
    selectinload(Vacancy.employment_type),
    selectinload(Vacancy.feasibility),
    selectinload(Vacancy.block),
]

class VacancyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, vacancy_id: int) -> Vacancy | None:
        result = await self.db.execute(
            select(Vacancy)
            .options(*VACANCY_LOAD_OPTIONS)
            .where(Vacancy.id == vacancy_id)
        )
        return result.scalar_one_or_none()

    async def get_by_vacancy_id(self, vacancy_id: str) -> Vacancy | None:
        result = await self.db.execute(
            select(Vacancy).where(Vacancy.vacancy_id == vacancy_id)
        )
        return result.scalar_one_or_none()

    async def get_list(
        self,
        base_query,
        skip: int = 0,
        limit: int = 100,
        sort_field: Optional[str] = None,
        sort_order: str = "desc",
    ) -> List[Vacancy]:
        if sort_field:
            fields = sort_field.split(',')
            orders = sort_order.split(',') if sort_order else []
            for i, f in enumerate(fields):
                field_name = f.strip()
                order_dir = orders[i].strip() if i < len(orders) else 'desc'
                if field_name == 'work_duration_days':
                    sort_col = func.coalesce(Vacancy.close_date, func.current_date()) - Vacancy.open_date - func.coalesce(Vacancy.hold_days, 0)
                    if order_dir == 'asc':
                        base_query = base_query.order_by(sort_col.asc().nulls_last())
                    else:
                        base_query = base_query.order_by(sort_col.desc().nulls_last())
                else:
                    sort_col = getattr(Vacancy, field_name, None)
                    from sqlalchemy.orm.attributes import InstrumentedAttribute
                    if sort_col is not None and isinstance(sort_col, InstrumentedAttribute):
                        if order_dir == 'asc':
                            base_query = base_query.order_by(sort_col.asc().nulls_last())
                        else:
                            base_query = base_query.order_by(sort_col.desc().nulls_last())
            base_query = base_query.order_by(Vacancy.id.desc())
        else:
            base_query = base_query.order_by(Vacancy.id.desc())

        base_query = base_query.options(*VACANCY_LOAD_OPTIONS).offset(skip).limit(limit)
        result = await self.db.execute(base_query)
        return result.scalars().all()

    async def count(self, count_query) -> int:
        result = await self.db.execute(count_query)
        return result.scalar()

    async def create(self, data: dict) -> Vacancy:
        vacancy = Vacancy(**data)
        self.db.add(vacancy)
        await self.db.flush()
        return vacancy

    async def update(self, vacancy: Vacancy, data: dict) -> Vacancy:
        for field, value in data.items():
            setattr(vacancy, field, value)
        return vacancy

    async def delete(self, vacancy: Vacancy) -> None:
        await self.db.delete(vacancy)

    async def get_weekly_metrics(
        self,
        vacancy_ids: List[int],
        conditions: list,
    ) -> dict:
                                                                     
        m_q = (
            select(
                WeeklyReport.vacancy_id,
                func.coalesce(func.sum(WeeklyReport.resumes_sent), 0).label("resumes_sent"),
                func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0).label("candidates_agreed"),
                func.coalesce(func.sum(WeeklyReport.interviews_planned), 0).label("interviews_planned"),
                func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0).label("interviews_conducted"),
                func.coalesce(func.sum(WeeklyReport.offer_made), 0).label("offer_made"),
            )
            .where(WeeklyReport.vacancy_id.in_(vacancy_ids))
        )
        if conditions:
            m_q = m_q.where(and_(*conditions))
        m_q = m_q.group_by(WeeklyReport.vacancy_id)

        rows = (await self.db.execute(m_q)).all()
        return {row.vacancy_id: row for row in rows}

    async def get_week_report(
        self, vacancy_id: int, week_num: int, year: int
    ) -> WeeklyReport | None:
        result = await self.db.execute(
            select(WeeklyReport).where(
                WeeklyReport.vacancy_id == vacancy_id,
                WeeklyReport.week_number == week_num,
                WeeklyReport.year == year,
            )
        )
        return result.scalar_one_or_none()

    async def create_week_report(self, data: dict) -> WeeklyReport:
        report = WeeklyReport(**data)
        self.db.add(report)
        return report

    async def commit(self) -> None:
        await self.db.commit()

    async def refresh(self, obj) -> None:
        await self.db.refresh(obj)