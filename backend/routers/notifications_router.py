import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, UserRole
from auth import get_current_active_admin
from email_service import is_smtp_configured, send_recruiter_weekly_reminder
from services.scheduler_service import (
    run_weekly_reminder_job,
    get_scheduler,
    get_next_friday_13_msk,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Уведомления"])


class TestEmailRequest(BaseModel):
    recipient: EmailStr


@router.get("/status")
async def get_notification_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_admin),
):
    """
    Возвращает статус планировщика рассылок и настройки почты.
    Доступно администраторам и супер-администраторам.
    """
    scheduler = get_scheduler()
    scheduler_info = scheduler.get_status() if scheduler else None

    # Подсчет активных рекрутеров
    stmt = select(func.count(User.id)).where(
        User.role == UserRole.RECRUITER,
        User.is_active == True,
    )
    recruiters_count = (await db.execute(stmt)).scalar() or 0

    return {
        "smtp_configured": is_smtp_configured(),
        "active_recruiters_count": recruiters_count,
        "next_weekly_reminder_msk": get_next_friday_13_msk().isoformat(),
        "scheduler": scheduler_info,
    }


@router.post("/send-weekly-reminder")
async def trigger_weekly_reminder(
    current_user: User = Depends(get_current_active_admin),
):
    """
    Ручной запуск рассылки еженедельного напоминания рекрутерам.
    Позволяет администратору протестировать или внепланово разослать отбивку.
    """
    logger.info(f"Пользователь {current_user.email} инициировал ручную отправку еженедельного напоминания")
    result = await run_weekly_reminder_job(force=True)
    return result


@router.post("/test-email")
async def send_test_email(
    body: TestEmailRequest,
    current_user: User = Depends(get_current_active_admin),
):
    """
    Тестовая отправка напоминания на конкретный указанный email.
    """
    logger.info(f"Тестовая отправка напоминания на {body.recipient} от {current_user.email}")
    result = await send_recruiter_weekly_reminder([body.recipient])
    return {
        "success": True,
        "recipient": body.recipient,
        "smtp_configured": is_smtp_configured(),
        "delivery": result,
    }
