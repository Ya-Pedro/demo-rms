\
\
\
\
\
\
\
   
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from database import get_db
from models import User
from services.delegation_service import DelegationService

router = APIRouter(tags=["Делегирование вакансий"])

                                                                                

class DelegationCreate(BaseModel):
    delegated_to_id: int
    start_date: date
    end_date: date

class DelegatedUserInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str

class DelegationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    vacancy_id: int
    delegated_to_id: int
    delegated_by_id: Optional[int] = None
    start_date: date
    end_date: date
    is_active: bool
    delegated_to: Optional[DelegatedUserInfo] = None
    delegated_by: Optional[DelegatedUserInfo] = None

                                                                                

@router.post(
    "/vacancies/{vacancy_id}/delegations",
    response_model=DelegationResponse,
    summary="Создать делегирование вакансии (только admin/superadmin)",
)
async def create_delegation(
    vacancy_id: int,
    body: DelegationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DelegationService(db)
    return await svc.create_delegation(
        vacancy_id=vacancy_id,
        delegated_to_id=body.delegated_to_id,
        start_date=body.start_date,
        end_date=body.end_date,
        current_user=current_user,
    )

@router.get(
    "/vacancies/{vacancy_id}/delegations",
    response_model=List[DelegationResponse],
    summary="История делегирований вакансии (только admin/superadmin)",
)
async def list_delegations(
    vacancy_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DelegationService(db)
    return await svc.list_delegations(vacancy_id, current_user)

@router.delete(
    "/delegations/{delegation_id}",
    status_code=204,
    summary="Досрочно завершить делегирование (только admin/superadmin)",
)
async def revoke_delegation(
    delegation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = DelegationService(db)
    await svc.revoke_delegation(delegation_id, current_user)