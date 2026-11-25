\
\
\
   
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional, List

from sqlalchemy import select, func, and_, or_, update, Integer, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from models import User, Vacancy, WeeklyReport, UserRole, Dictionary

                                                 
VACANCY_LOAD_OPTIONS = [
    selectinload(Vacancy.recruiter),
    selectinload(Vacancy.co_recruiter),
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
]

DICT_SORT_COLUMNS = (
    'level_id', 'status_id', 'it_role_id', 'admin_manager_id',
    'project_id', 'source_id', 'internal_transfer_id',
    'replacement_type_id', 'employment_type_id',
    'block_id',
)

USER_SORT_COLUMNS = ('recruiter_id', 'co_recruiter_id')

TEXT_SORT_COLUMNS = {
    'position_name', 'candidate_name', 'comment', 'offer_rejection_reason',
    'recommender_name', 'candidate_company', 'ex_employee_name', 'unit_id', 'iqhr_link',
}

HYBRID_TEXT_DICT_SORT = {
    'team_lead_text': (Vacancy.team_lead_text, Vacancy.team_lead_id, True),
    'city_text': (Vacancy.city_text, Vacancy.city_id, False),
    'feasibility_id': (Vacancy.feasibility_text, Vacancy.feasibility_id, False),
}

FUNNEL_MODEL_ATTR_MAP = {
    'resume_at_customer': Vacancy.resume_at_customer,
    'resume_approved': Vacancy.resume_approved,
    'interviews_fact': Vacancy.interviews_fact,
    'interviews_plan': Vacancy.interviews_plan,
    'offer_made': Vacancy.offer_made,
    'offer_accepted': Vacancy.offer_accepted_cnt,
}


def order_expr(expr, order_dir: str, is_text: bool = False):
    """Формирует ORDER BY так, чтобы NULL и пустые строки считались минимальными:
    ASC -> пустые сверху (NULLS FIRST), DESC -> пустые в конце (NULLS LAST).
    Текстовые значения сравниваются без учёта регистра и крайних пробелов.
    """
    target = func.lower(func.nullif(func.trim(expr), '')) if is_text else expr
    if order_dir == 'asc':
        return target.asc().nulls_first()
    return target.desc().nulls_last()


def apply_vacancy_sorting(
    query,
    sort_field: Optional[str],
    sort_order: Optional[str] = "desc",
    funnel_col_map: Optional[dict] = None,
    dialect_name: str = "postgresql",
):
    """Единая сортировка вакансий для таблицы и экспорта."""
    if not sort_field:
        return query.order_by(Vacancy.id.desc())

    fields = sort_field.split(',')
    orders = sort_order.split(',') if sort_order else []

    for i, f in enumerate(fields):
        field_name = f.strip()
        if not field_name:
            continue
        order_dir = orders[i].strip().lower() if i < len(orders) else 'desc'
        if order_dir not in ('asc', 'desc'):
            order_dir = 'desc'

        if field_name == 'vacancy_id':
            clean_vid = func.nullif(func.trim(Vacancy.vacancy_id), '')
            has_val = case((clean_vid.is_(None), None), else_=1)
            query = query.order_by(order_expr(has_val, order_dir))
            if dialect_name == 'postgresql':
                num_expr = func.cast(
                    func.nullif(func.regexp_replace(clean_vid, r'\D', '', 'g'), ''),
                    Integer,
                )
                query = query.order_by(order_expr(num_expr, order_dir))
            query = query.order_by(order_expr(clean_vid, order_dir, is_text=True))
        elif field_name == 'work_duration_days':
            sort_col = func.coalesce(Vacancy.close_date, func.current_date()) - Vacancy.open_date - func.coalesce(Vacancy.hold_days, 0)
            query = query.order_by(order_expr(sort_col, order_dir))
        elif funnel_col_map and field_name in funnel_col_map:
            sort_col = func.coalesce(funnel_col_map[field_name], 0)
            query = query.order_by(sort_col.asc() if order_dir == 'asc' else sort_col.desc())
        elif field_name in FUNNEL_MODEL_ATTR_MAP:
            sort_col = func.coalesce(FUNNEL_MODEL_ATTR_MAP[field_name], 0)
            query = query.order_by(sort_col.asc() if order_dir == 'asc' else sort_col.desc())
        elif field_name in HYBRID_TEXT_DICT_SORT:
            text_col, dict_fk_col, text_first = HYBRID_TEXT_DICT_SORT[field_name]
            dict_subq = select(Dictionary.value).where(Dictionary.id == dict_fk_col).scalar_subquery()
            clean_text = func.nullif(func.trim(text_col), '')
            clean_dict = func.nullif(func.trim(dict_subq), '')
            combined = func.coalesce(clean_text, clean_dict) if text_first else func.coalesce(clean_dict, clean_text)
            query = query.order_by(order_expr(combined, order_dir, is_text=True))
        elif field_name in DICT_SORT_COLUMNS:
            dict_subq = select(Dictionary.value).where(Dictionary.id == getattr(Vacancy, field_name)).scalar_subquery()
            query = query.order_by(order_expr(dict_subq, order_dir, is_text=True))
        elif field_name in USER_SORT_COLUMNS:
            user_subq = select(User.full_name).where(User.id == getattr(Vacancy, field_name)).scalar_subquery()
            query = query.order_by(order_expr(user_subq, order_dir, is_text=True))
        else:
            sort_col = getattr(Vacancy, field_name, None)
            if sort_col is not None and isinstance(sort_col, InstrumentedAttribute):
                is_text = field_name in TEXT_SORT_COLUMNS
                query = query.order_by(order_expr(sort_col, order_dir, is_text=is_text))

    return query.order_by(Vacancy.id.desc())


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

    # Mapping from vacancy sort field names to WeeklyReport aggregate columns
    FUNNEL_SORT_MAP = {
        'resume_at_customer': WeeklyReport.resumes_sent,
        'resume_approved': WeeklyReport.candidates_agreed,
        'interviews_fact': WeeklyReport.interviews_conducted,
        'interviews_plan': WeeklyReport.interviews_planned,
        'offer_made': WeeklyReport.offer_made,
        'offer_accepted': WeeklyReport.offer_accepted,
    }

    async def get_list(
        self,
        base_query,
        skip: int = 0,
        limit: int = 100,
        sort_field: Optional[str] = None,
        sort_order: str = "desc",
        period_conditions: Optional[list] = None,
    ) -> List[Vacancy]:
        if sort_field:
            fields = sort_field.split(',')
            orders = sort_order.split(',') if sort_order else []

            # Check if any of the sort fields require WeeklyReport aggregation
            needs_funnel_join = any(
                f.strip() in self.FUNNEL_SORT_MAP for f in fields
            )

            # If sorting by funnel fields, join with a WeeklyReport subquery
            if needs_funnel_join:
                metrics_subq = (
                    select(
                        WeeklyReport.vacancy_id.label('_mv_id'),
                        func.coalesce(func.sum(WeeklyReport.resumes_sent), 0).label('_mv_resumes_sent'),
                        func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0).label('_mv_candidates_agreed'),
                        func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0).label('_mv_interviews_conducted'),
                        func.coalesce(func.sum(WeeklyReport.interviews_planned), 0).label('_mv_interviews_planned'),
                        func.coalesce(func.sum(WeeklyReport.offer_made), 0).label('_mv_offer_made'),
                        func.coalesce(func.sum(WeeklyReport.offer_accepted), 0).label('_mv_offer_accepted'),
                    )
                )
                if period_conditions:
                    metrics_subq = metrics_subq.where(and_(*period_conditions))
                metrics_subq = metrics_subq.group_by(WeeklyReport.vacancy_id).subquery()

                base_query = base_query.outerjoin(
                    metrics_subq, Vacancy.id == metrics_subq.c._mv_id
                )

                funnel_col_map = {
                    'resume_at_customer': metrics_subq.c._mv_resumes_sent,
                    'resume_approved': metrics_subq.c._mv_candidates_agreed,
                    'interviews_fact': metrics_subq.c._mv_interviews_conducted,
                    'interviews_plan': metrics_subq.c._mv_interviews_planned,
                    'offer_made': metrics_subq.c._mv_offer_made,
                    'offer_accepted': metrics_subq.c._mv_offer_accepted,
                }

            else:
                funnel_col_map = None

            dialect_name = getattr(getattr(self.db, "bind", None), "dialect", None)
            dialect_str = dialect_name.name if dialect_name else "postgresql"
            base_query = apply_vacancy_sorting(
                base_query,
                sort_field=sort_field,
                sort_order=sort_order,
                funnel_col_map=funnel_col_map,
                dialect_name=dialect_str,
            )
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
        current_user: Optional[User] = None,
    ) -> dict:
        m_q = (
            select(
                WeeklyReport.vacancy_id,
                func.coalesce(func.sum(WeeklyReport.resumes_sent), 0).label("resumes_sent"),
                func.coalesce(func.sum(WeeklyReport.candidates_agreed), 0).label("candidates_agreed"),
                func.coalesce(func.sum(WeeklyReport.interviews_planned), 0).label("interviews_planned"),
                func.coalesce(func.sum(WeeklyReport.interviews_conducted), 0).label("interviews_conducted"),
                func.coalesce(func.sum(WeeklyReport.offer_made), 0).label("offer_made"),
                func.coalesce(func.sum(WeeklyReport.offer_accepted), 0).label("offer_accepted"),
            )
            .join(Vacancy, WeeklyReport.vacancy_id == Vacancy.id)
            .where(WeeklyReport.vacancy_id.in_(vacancy_ids))
        )
        if conditions:
            m_q = m_q.where(and_(*conditions))
        if current_user and current_user.role == UserRole.RECRUITER:
            m_q = m_q.where(
                or_(
                    WeeklyReport.user_id == current_user.id,
                    and_(WeeklyReport.user_id.is_(None), Vacancy.recruiter_id == current_user.id),
                )
            )
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