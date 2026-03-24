\
\
\
\
   
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models import User, Vacancy, WeeklyReport, UserRole
from services.repositories.vacancy_repository import VacancyRepository
from services.vacancy_filter import apply_vacancy_filters

                                                                               

def get_current_week_monday() -> date:
    today = date.today()
    return today - timedelta(days=today.weekday())

def get_current_week_info() -> tuple[int, int]:
                                                
    iso = date.today().isocalendar()
    return iso[1], iso[0]

                                                                                

FUNNEL_MAP = {
    "resume_at_customer": "resumes_sent",
    "resume_approved": "candidates_agreed",
    "interviews_fact": "interviews_conducted",
    "interviews_plan": "interviews_planned",
    "offer_made": "offer_made",
}

                                                                                

def vacancy_to_dict(vacancy: Vacancy, metrics=None) -> dict:
\
\
\
       
    if metrics is not None:
        resume_at_customer = metrics.resumes_sent or 0
        resume_approved = metrics.candidates_agreed or 0
        interviews_plan = metrics.interviews_planned or 0
        interviews_fact = metrics.interviews_conducted or 0
        offer_made = metrics.offer_made or 0
    else:
        resume_at_customer = resume_approved = interviews_plan = interviews_fact = offer_made = 0

    return {
        "id": vacancy.id,
        "vacancy_id": vacancy.vacancy_id,
        "open_date": vacancy.open_date,
        "quantity": vacancy.quantity,
        "level_id": vacancy.level_id,
        "position_name": vacancy.position_name,
        "status_id": vacancy.status_id,
        "it_role_id": vacancy.it_role_id,
        "admin_manager_id": vacancy.admin_manager_id,
        "team_lead_id": vacancy.team_lead_id,
        "project_id": vacancy.project_id,
        "resume_at_customer": resume_at_customer,
        "resume_approved": resume_approved,
        "interviews_fact": interviews_fact,
        "interviews_plan": interviews_plan,
        "offer_made": offer_made,
        "city_id": vacancy.city_id,
        "city_text": vacancy.city_text,
        "source_id": vacancy.source_id,
        "internal_transfer_id": vacancy.internal_transfer_id,
        "status_changed_at": vacancy.status_changed_at,
        "close_date": vacancy.close_date,
        "candidate_name": vacancy.candidate_name,
        "candidate_company": vacancy.candidate_company,
        "replacement_type_id": vacancy.replacement_type_id,
        "ex_employee_name": vacancy.ex_employee_name,
        "unit_id": vacancy.unit_id,
        "employment_type_id": vacancy.employment_type_id,
        "feasibility_id": vacancy.feasibility_id,
        "iqhr_link": vacancy.iqhr_link,
        "recruiter_id": vacancy.recruiter_id,
        "block_id": vacancy.block_id,
        "hold_days": vacancy.hold_days,
        "salary_gross": vacancy.salary_gross,
        "resumes_sent_cnt": vacancy.resumes_sent_cnt,
        "candidates_agreed_cnt": vacancy.candidates_agreed_cnt,
        "interviews_planned_cnt": vacancy.interviews_planned_cnt,
        "interviews_conducted_cnt": vacancy.interviews_conducted_cnt,
        "created_at": vacancy.created_at,
        "recruiter": vacancy.recruiter,
        "level": vacancy.level,
        "status": vacancy.status,
        "it_role": vacancy.it_role,
        "admin_manager": vacancy.admin_manager,
        "team_lead": vacancy.team_lead,
        "project": vacancy.project,
        "city": vacancy.city,
        "source": vacancy.source,
        "internal_transfer": vacancy.internal_transfer,
        "replacement_type": vacancy.replacement_type,
        "employment_type": vacancy.employment_type,
        "feasibility": vacancy.feasibility,
        "block": vacancy.block,
        "work_duration_days": vacancy.work_duration_days,
        "delegation": getattr(vacancy, "_active_delegation", None),
    }

                                                                                

class VacancyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = VacancyRepository(db)

    def _build_period_conditions(
        self,
        week_number: Optional[int],
        year: Optional[int],
        start_date: Optional[str],
        end_date: Optional[str],
    ) -> list:
                                                                    
        from datetime import date as _date
        conditions = []

        if week_number is not None or year is not None:
            wn = week_number or get_current_week_info()[0]
            yr = year or get_current_week_info()[1]
            conditions.append(WeeklyReport.week_number == wn)
            conditions.append(WeeklyReport.year == yr)
        elif start_date or end_date:
            if start_date:
                try:
                    conditions.append(WeeklyReport.week_start >= _date.fromisoformat(start_date))
                except ValueError:
                    pass
            if end_date:
                try:
                    conditions.append(WeeklyReport.week_start <= _date.fromisoformat(end_date))
                except ValueError:
                    pass
        else:
            wn, yr = get_current_week_info()
            conditions.append(WeeklyReport.week_number == wn)
            conditions.append(WeeklyReport.year == yr)

        return conditions

    async def list_vacancies(
        self,
        current_user: User,
        skip: int,
        limit: int,
        sort_field: Optional[str],
        sort_order: str,
        week_number: Optional[int],
        year: Optional[int],
        start_date: Optional[str],
        end_date: Optional[str],
        filter_params: dict,
    ) -> tuple[list, int]:
                                                              
        from sqlalchemy import func, select

                               
        clean_params = {k: v for k, v in filter_params.items() if v is not None}

        count_q = select(func.count(Vacancy.id))
        count_q, _ = apply_vacancy_filters(count_q, current_user, **clean_params)
        total = await self.repo.count(count_q)

        data_q = select(Vacancy)
        data_q, _ = apply_vacancy_filters(data_q, current_user, **clean_params)

        vacancies = await self.repo.get_list(data_q, skip=skip, limit=limit,
                                              sort_field=sort_field, sort_order=sort_order)

        metrics_map = {}
        if vacancies:
            period_conditions = self._build_period_conditions(week_number, year, start_date, end_date)
            metrics_map = await self.repo.get_weekly_metrics(
                [v.id for v in vacancies], period_conditions
            )

                                                                  
        if vacancies:
            from services.delegation_service import DelegationService
            delegation_svc = DelegationService(self.db)
            for v in vacancies:
                v._active_delegation = await delegation_svc.get_active_delegation(v.id)

        return vacancies, total, metrics_map

    async def get_vacancy_or_404(self, vacancy_id: int) -> Vacancy:
        vacancy = await self.repo.get_by_id(vacancy_id)
        if not vacancy:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")
        return vacancy

    async def check_recruiter_access(self, vacancy: Vacancy, current_user: User) -> None:
                                                                                      
        if current_user.role != UserRole.RECRUITER:
            return
        if vacancy.recruiter_id == current_user.id:
            return
        from services.delegation_service import DelegationService
        svc = DelegationService(self.db)
        if await svc.has_delegated_access(vacancy.id, current_user.id):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой вакансии",
        )

    async def create_vacancy(self, vacancy_data: dict, current_user: Optional[User] = None) -> tuple[Vacancy, object]:
\
\
\
           
                                
        funnel = {
            "resumes_sent": vacancy_data.pop("resume_at_customer", 0) or 0,
            "candidates_agreed": vacancy_data.pop("resume_approved", 0) or 0,
            "interviews_conducted": vacancy_data.pop("interviews_fact", 0) or 0,
            "interviews_planned": vacancy_data.pop("interviews_plan", 0) or 0,
            "offer_made": vacancy_data.pop("offer_made", 0) or 0,
        }
        vacancy_data["counters_updated_at"] = datetime.now(timezone.utc)

        vacancy = await self.repo.create(vacancy_data)

        week_num, yr = get_current_week_info()
        await self.repo.create_week_report({
            "vacancy_id": vacancy.id,
            "week_number": week_num,
            "year": yr,
            "week_start": get_current_week_monday(),
            "report_date": datetime.now(timezone.utc),
            **funnel,
        })
        await self.repo.commit()
        await self.repo.refresh(vacancy)

                                    
        vacancy = await self.repo.get_by_id(vacancy.id)

                               
        if current_user is not None:
            try:
                from services.vacancy_history_service import VacancyHistoryService
                _h = VacancyHistoryService(self.db)
                await _h.record_create(vacancy, current_user)
                await self.repo.commit()
            except Exception:
                import logging, traceback
                logging.getLogger(__name__).warning(
                    "history CREATE failed:\n%s", traceback.format_exc()
                )

        metrics_row = type("Metrics", (), {
            "resumes_sent": funnel["resumes_sent"],
            "candidates_agreed": funnel["candidates_agreed"],
            "interviews_planned": funnel["interviews_planned"],
            "interviews_conducted": funnel["interviews_conducted"],
            "offer_made": funnel["offer_made"],
        })()

        return vacancy, metrics_row

    async def update_vacancy(
        self, vacancy_id: int, update_data: dict, current_user: User
    ) -> tuple[Vacancy, object]:
                                                               
        vacancy = await self.get_vacancy_or_404(vacancy_id)
        await self.check_recruiter_access(vacancy, current_user)

                                            
        _hist_before = None
        try:
            from services.vacancy_history_service import VacancyHistoryService
            _hist_svc = VacancyHistoryService(self.db)
            _hist_before = _hist_svc.snapshot(vacancy)
        except Exception:
            import logging, traceback
            logging.getLogger(__name__).warning(
                "history snapshot failed:\n%s", traceback.format_exc()
            )

                                                
        funnel_updates = {}
        for vacancy_field, report_field in FUNNEL_MAP.items():
            if vacancy_field in update_data:
                funnel_updates[report_field] = update_data.pop(vacancy_field)

        await self.repo.update(vacancy, update_data)

        if funnel_updates:
            week_num, yr = get_current_week_info()
            week_report = await self.repo.get_week_report(vacancy_id, week_num, yr)
            if week_report:
                for field, value in funnel_updates.items():
                    setattr(week_report, field, value)
            else:
                await self.repo.create_week_report({
                    "vacancy_id": vacancy_id,
                    "week_number": week_num,
                    "year": yr,
                    "week_start": get_current_week_monday(),
                    "report_date": datetime.now(timezone.utc),
                    **funnel_updates,
                })

        await self.repo.commit()

                                                      
        week_num, yr = get_current_week_info()
        current_week_report = await self.repo.get_week_report(vacancy_id, week_num, yr)
                                                                            
        await self.db.flush()
        self.db.expire(vacancy)
        vacancy = await self.repo.get_by_id(vacancy_id)

                               
        if _hist_before is not None:
            try:
                from services.vacancy_history_service import VacancyHistoryService
                _hist_svc2 = VacancyHistoryService(self.db)
                await _hist_svc2.record_update(_hist_before, vacancy, current_user)
                await self.repo.commit()
            except Exception:
                import logging, traceback
                logging.getLogger(__name__).warning(
                    "history UPDATE failed:\n%s", traceback.format_exc()
                )

        return vacancy, current_week_report

    async def delete_vacancy(self, vacancy_id: int, current_user: User) -> None:
        vacancy = await self.get_vacancy_or_404(vacancy_id)
        await self.check_recruiter_access(vacancy, current_user)
                               
        try:
            from services.vacancy_history_service import VacancyHistoryService
            _hist_del = VacancyHistoryService(self.db)
            await _hist_del.record_delete(vacancy, current_user)
        except Exception:
            import logging, traceback
            logging.getLogger(__name__).warning(
                "history DELETE failed:\n%s", traceback.format_exc()
            )
        await self.repo.delete(vacancy)
        await self.repo.commit()