\
\
\
\
\
\
\
\
\
   
from __future__ import annotations

from datetime import date, datetime, timezone
import os

def _today() -> date:
                                                                         
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(os.environ.get("APP_TIMEZONE", "Europe/Moscow"))
        return datetime.now(tz).date()
    except Exception:
        from datetime import timedelta
        return (datetime.now(timezone.utc) + timedelta(hours=3)).date()

from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import VacancyDelegation, Vacancy, User, UserRole

class DelegationService:
    def __init__(self, db: AsyncSession):
        self.db = db

                                                                                

    def _require_admin(self, current_user: User) -> None:
        pass

    async def _get_vacancy_or_404(self, vacancy_id: int) -> Vacancy:
        result = await self.db.execute(
            select(Vacancy).where(Vacancy.id == vacancy_id)
        )
        vacancy = result.scalar_one_or_none()
        if not vacancy:
            raise HTTPException(status_code=404, detail="Вакансия не найдена")
        return vacancy

    async def _get_delegatee_or_404(self, user_id: int) -> User:
        result = await self.db.execute(
            select(User).where(User.id == user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден или неактивен")
        return user

                                                                               

    async def get_active_delegation(
        self, vacancy_id: int
    ) -> Optional[VacancyDelegation]:
        today = _today()
        result = await self.db.execute(
            select(VacancyDelegation)
            .options(
                selectinload(VacancyDelegation.delegated_to),
                selectinload(VacancyDelegation.delegated_by),
            )
            .where(
                VacancyDelegation.vacancy_id == vacancy_id,
                VacancyDelegation.is_active == True,
                VacancyDelegation.start_date <= today,
                VacancyDelegation.end_date >= today,
            )
            .order_by(VacancyDelegation.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

                                                                               

    async def has_delegated_access(self, vacancy_id: int, user_id: int) -> bool:
        today = _today()
        result = await self.db.execute(
            select(VacancyDelegation.id).where(
                VacancyDelegation.vacancy_id == vacancy_id,
                VacancyDelegation.delegated_to_id == user_id,
                VacancyDelegation.is_active == True,
                VacancyDelegation.start_date <= today,
                VacancyDelegation.end_date >= today,
            )
        )
        return result.scalar_one_or_none() is not None

                                                                               

    async def get_delegated_vacancy_ids(self, user_id: int) -> List[int]:
        today = _today()
        result = await self.db.execute(
            select(VacancyDelegation.vacancy_id).where(
                VacancyDelegation.delegated_to_id == user_id,
                VacancyDelegation.is_active == True,
                VacancyDelegation.start_date <= today,
                VacancyDelegation.end_date >= today,
            )
        )
        return [row[0] for row in result.all()]

                                                                                

    async def create_delegation(
        self,
        vacancy_id: int,
        delegated_to_id: int,
        start_date: date,
        end_date: date,
        current_user: User,
    ) -> VacancyDelegation:
        vacancy = await self._get_vacancy_or_404(vacancy_id)
        
        # Разрешаем делегировать админам/суперадминам и самому рекрутеру (владельцу вакансии)
        if current_user.role not in (UserRole.SUPERADMIN, UserRole.ADMIN):
            if vacancy.recruiter_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет прав на делегирование этой вакансии"
                )

        if end_date < start_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Дата окончания не может быть раньше даты начала",
            )
        if end_date < date.today():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Дата окончания не может быть в прошлом",
            )

        vacancy = await self._get_vacancy_or_404(vacancy_id)
        delegatee = await self._get_delegatee_or_404(delegated_to_id)

        if vacancy.recruiter_id == delegated_to_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Нельзя делегировать вакансию её основному рекрутеру",
            )

                                                               
        existing = await self.get_active_delegation(vacancy_id)
        if existing:
            existing.is_active = False

        delegation = VacancyDelegation(
            vacancy_id=vacancy_id,
            delegated_to_id=delegated_to_id,
            delegated_by_id=current_user.id,
            start_date=start_date,
            end_date=end_date,
            is_active=True,
        )
        self.db.add(delegation)
        await self.db.commit()
        await self.db.refresh(delegation)

                                       
        result = await self.db.execute(
            select(VacancyDelegation)
            .options(
                selectinload(VacancyDelegation.delegated_to),
                selectinload(VacancyDelegation.delegated_by),
            )
            .where(VacancyDelegation.id == delegation.id)
        )
        final_delegation = result.scalar_one()

                                 
        try:
            from services.vacancy_history_service import VacancyHistoryService
            _hist = VacancyHistoryService(self.db)
            to_name = final_delegation.delegated_to.full_name if final_delegation.delegated_to else f"ID {delegated_to_id}"
            await _hist.record_delegation_created(
                vacancy_id=vacancy_id,
                vacancy_name=vacancy.position_name,
                delegated_to_name=to_name,
                start_date=start_date,
                end_date=end_date,
                user=current_user,
            )
            await self.db.commit()
        except Exception:
            import logging, traceback
            logging.getLogger(__name__).warning(
                "history DELEGATE failed:\n%s", traceback.format_exc()
            )

        return final_delegation

                                                                               

    async def revoke_delegation(
        self, delegation_id: int, current_user: User
    ) -> None:
        result = await self.db.execute(
            select(VacancyDelegation).where(VacancyDelegation.id == delegation_id)
        )
        delegation = result.scalar_one_or_none()
        if not delegation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Делегирование не найдено"
            )

        vacancy = await self._get_vacancy_or_404(delegation.vacancy_id)
        if current_user.role not in (UserRole.SUPERADMIN, UserRole.ADMIN):
            if vacancy.recruiter_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет прав на отзыв делегирования этой вакансии"
                )

        delegation.is_active = False

                                   
        try:
            from services.vacancy_history_service import VacancyHistoryService
            from models import Vacancy as _Vac, User as _User
            from sqlalchemy import select as _sel
            _hist2 = VacancyHistoryService(self.db)
            _vac = (await self.db.execute(_sel(_Vac).where(_Vac.id == delegation.vacancy_id))).scalar_one_or_none()
            _to  = (await self.db.execute(_sel(_User).where(_User.id == delegation.delegated_to_id))).scalar_one_or_none()
            to_name = _to.full_name if _to else f"ID {delegation.delegated_to_id}"
            await _hist2.record_delegation_revoked(
                vacancy_id=delegation.vacancy_id,
                vacancy_name=_vac.position_name if _vac else f"Вакансия #{delegation.vacancy_id}",
                delegated_to_name=to_name,
                user=current_user,
            )
        except Exception:
            import logging, traceback
            logging.getLogger(__name__).warning(
                "history UNDELEGATE failed:\n%s", traceback.format_exc()
            )

        await self.db.commit()

                                                                               

    async def list_delegations(
        self, vacancy_id: int, current_user: User
    ) -> List[VacancyDelegation]:
        vacancy = await self._get_vacancy_or_404(vacancy_id)
        if current_user.role not in (UserRole.SUPERADMIN, UserRole.ADMIN):
            if vacancy.recruiter_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Нет прав на просмотр делегирований этой вакансии"
                )

        result = await self.db.execute(
            select(VacancyDelegation)
            .options(
                selectinload(VacancyDelegation.delegated_to),
                selectinload(VacancyDelegation.delegated_by),
            )
            .where(VacancyDelegation.vacancy_id == vacancy_id)
            .order_by(VacancyDelegation.id.desc())
        )
        return result.scalars().all()