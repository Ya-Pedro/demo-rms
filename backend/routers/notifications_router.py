import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, UserRole
from auth import get_current_active_admin
from email_service import is_smtp_configured, send_recruiter_weekly_reminder, send_registration_email
from services.scheduler_service import (
    run_weekly_reminder_job,
    get_scheduler,
    get_next_friday_13_msk,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Уведомления"])


class TestEmailRequest(BaseModel):
    recipient: EmailStr
    template: Optional[str] = "reminder"  # "reminder", "registration", "all"


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
    request: Request,
    body: TestEmailRequest,
    current_user: User = Depends(get_current_active_admin),
):
    """
    Тестовая отправка писем на конкретный указанный email.
    Параметр template: 'reminder' (напоминание в пятницу), 'registration' (письмо регистрации) или 'all' (оба письма).
    """
    logger.info(f"Тестовая отправка письма ({body.template}) на {body.recipient} от {current_user.email}")
    origin = request.headers.get("origin") or request.headers.get("referer")
    base_url = None
    if origin:
        from urllib.parse import urlparse
        parsed = urlparse(origin)
        if parsed.scheme and parsed.netloc:
            base_url = f"{parsed.scheme}://{parsed.netloc}"

    results = {}

    if body.template in ("registration", "all"):
        reg_res = await send_registration_email(
            email=body.recipient,
            full_name="Тестовый Пользователь",
            password="DemoPass123!",
            base_url=base_url,
        )
        results["registration"] = {
            "status": "sent" if reg_res else ("mock_printed" if not is_smtp_configured() else "failed"),
            "success": reg_res or (not is_smtp_configured()),
        }

    if body.template in ("reminder", "all"):
        rem_res = await send_recruiter_weekly_reminder([body.recipient], base_url=base_url)
        results["reminder"] = rem_res

    return {
        "success": True,
        "recipient": body.recipient,
        "template": body.template,
        "smtp_configured": is_smtp_configured(),
        "delivery": results,
    }
