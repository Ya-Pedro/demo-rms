\
\
   
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List

from database import get_db
from models import User, WeeklyReport, Vacancy
from schemas import WeeklyReportCreate, WeeklyReportUpdate, WeeklyReportResponse
from auth import get_current_user

router = APIRouter(prefix="/weekly-reports", tags=["Еженедельные отчеты"])

@router.get("/weeks", response_model=List[dict])
async def get_available_weeks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    year: Optional[int] = None
):
                                               
    query = select(
        WeeklyReport.week_label,
        WeeklyReport.year
    ).distinct().order_by(WeeklyReport.year.desc(), WeeklyReport.week_label.desc())
    
    if year:
        query = query.where(WeeklyReport.year == year)
    
    result = await db.execute(query)
    weeks = result.all()
    
    return [{"week_label": w.week_label, "year": w.year} for w in weeks]

@router.get("", response_model=List[WeeklyReportResponse])
async def get_weekly_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    vacancy_id: Optional[int] = None,
    week_label: Optional[str] = None,
    year: Optional[int] = None
):
                                         
    query = select(WeeklyReport)
    
    if vacancy_id:
        query = query.where(WeeklyReport.vacancy_id == vacancy_id)
    
    if week_label:
        query = query.where(WeeklyReport.week_label == week_label)
    
    if year:
        query = query.where(WeeklyReport.year == year)
    
    query = query.order_by(WeeklyReport.year.desc(), WeeklyReport.week_label.desc())
    result = await db.execute(query)
    
    return result.scalars().all()

@router.post("", response_model=WeeklyReportResponse, status_code=status.HTTP_201_CREATED)
async def create_weekly_report(
    report_data: WeeklyReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
                                  
                             
    vacancy = await db.execute(
        select(Vacancy).where(Vacancy.id == report_data.vacancy_id)
    )
    if not vacancy.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Вакансия не найдена"
        )
    
                          
    existing = await db.execute(
        select(WeeklyReport).where(
            WeeklyReport.vacancy_id == report_data.vacancy_id,
            WeeklyReport.week_label == report_data.week_label,
            WeeklyReport.year == report_data.year
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Отчет за эту неделю уже существует"
        )
    
    new_report = WeeklyReport(**report_data.model_dump())
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    
    return new_report

@router.get("/{report_id}", response_model=WeeklyReportResponse)
async def get_weekly_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
                                 
    result = await db.execute(
        select(WeeklyReport).where(WeeklyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отчет не найден"
        )
    
    return report

@router.patch("/{report_id}", response_model=WeeklyReportResponse)
async def update_weekly_report(
    report_id: int,
    report_data: WeeklyReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
                              
    result = await db.execute(
        select(WeeklyReport).where(WeeklyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отчет не найден"
        )
    
    update_data = report_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(report, field, value)
    
    await db.commit()
    await db.refresh(report)
    
    return report

@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weekly_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
                              
    result = await db.execute(
        select(WeeklyReport).where(WeeklyReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Отчет не найден"
        )
    
    await db.delete(report)
    await db.commit()
