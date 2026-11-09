import logging
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User, UserRole, SystemSetting
from auth import get_current_active_admin, get_current_user
from email_service import (
    is_smtp_configured,
    send_recruiter_weekly_reminder,
    send_registration_email,
    get_smtp_setting,
    set_dynamic_smtp_setting,
    update_env_file,
    check_smtp_connection,
    load_smtp_settings_from_db,
)
from services.scheduler_service import (
    run_weekly_reminder_job,
    get_scheduler,
    get_next_friday_13_msk,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Уведомления"])

SMTP_MANAGER_EMAIL = "yuliya.e.novikova@rt.ru"


def require_smtp_manager(current_user: User = Depends(get_current_user)) -> User:
    if not current_user:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    email = (current_user.email or "").strip().lower()
    if email != SMTP_MANAGER_EMAIL and current_user.role != UserRole.SUPERADMIN:
        raise HTTPException(
            status_code=403,
            detail=f"Настройки почтового сервиса доступны только пользователю {SMTP_MANAGER_EMAIL}",
        )
    return current_user


class TestEmailRequest(BaseModel):
    recipient: EmailStr
    template: Optional[str] = "reminder"  # "reminder", "registration", "all"


class SmtpPasswordUpdateRequest(BaseModel):
    password: str
    username: Optional[str] = None
    from_email: Optional[str] = None
    server: Optional[str] = None
    port: Optional[int] = None


class SmtpTestConnectionRequest(BaseModel):
    password: Optional[str] = None
    username: Optional[str] = None
    server: Optional[str] = None
    port: Optional[int] = None


class SmtpSelfTestRequest(BaseModel):
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


@router.get("/smtp-settings")
async def get_smtp_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_smtp_manager),
):
    """
    Получить текущие настройки и статус подключения к SMTP.
    Доступно только Yuliya.e.novikova@rt.ru и супер-администраторам.
    """
    await load_smtp_settings_from_db(db)
    connected, conn_msg = check_smtp_connection()
    pwd = get_smtp_setting("SMTP_PASSWORD", "")
    has_pwd = bool(pwd and "REPLACE_WITH" not in pwd)

    res = await db.execute(select(SystemSetting).where(SystemSetting.key == "SMTP_PASSWORD"))
    setting_row = res.scalar_one_or_none()

    return {
        "smtp_server": get_smtp_setting("SMTP_SERVER", "smtp.yandex.ru"),
        "smtp_port": int(get_smtp_setting("SMTP_PORT", "465")),
        "smtp_username": get_smtp_setting("SMTP_USERNAME", ""),
        "smtp_from": get_smtp_setting("SMTP_FROM", ""),
        "smtp_ssl_tls": get_smtp_setting("SMTP_SSL_TLS", "True").lower() == "true",
        "password_configured": has_pwd,
        "is_smtp_configured": is_smtp_configured(),
        "connected": connected,
        "connection_message": conn_msg,
        "manager_email": SMTP_MANAGER_EMAIL,
        "current_user_email": current_user.email,
        "updated_at": setting_row.updated_at.isoformat() if setting_row and setting_row.updated_at else None,
        "updated_by": setting_row.updated_by if setting_row else None,
    }


@router.post("/smtp-settings")
async def update_smtp_settings(
    body: SmtpPasswordUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_smtp_manager),
):
    """
    Обновить пароль (и при необходимости другие параметры) почтового сервера.
    Доступно только Yuliya.e.novikova@rt.ru и супер-администраторам.
    """
    new_pwd = body.password.strip()
    if not new_pwd:
        raise HTTPException(status_code=400, detail="Пароль не может быть пустым")

    srv = body.server or get_smtp_setting("SMTP_SERVER", "")
    prt = body.port or int(get_smtp_setting("SMTP_PORT", "465"))
    usr = body.username or get_smtp_setting("SMTP_USERNAME", "")

    connected, conn_msg = check_smtp_connection(server=srv, port=prt, user=usr, pwd=new_pwd)

    async def _upsert_setting(k: str, v: str, desc: str):
        res = await db.execute(select(SystemSetting).where(SystemSetting.key == k))
        row = res.scalar_one_or_none()
        if not row:
            row = SystemSetting(key=k, value=v, description=desc, updated_by=current_user.email)
            db.add(row)
        else:
            row.value = v
            row.updated_by = current_user.email
            row.updated_at = func.now()

    await _upsert_setting("SMTP_PASSWORD", new_pwd, "Пароль SMTP сервиса")
    if body.username:
        await _upsert_setting("SMTP_USERNAME", body.username.strip(), "Логин SMTP сервиса")
    if body.from_email:
        await _upsert_setting("SMTP_FROM", body.from_email.strip(), "Адрес отправителя SMTP")
    if body.server:
        await _upsert_setting("SMTP_SERVER", body.server.strip(), "Хост SMTP сервера")
    if body.port:
        await _upsert_setting("SMTP_PORT", str(body.port), "Порт SMTP сервера")

    await db.commit()

    # Обновляем в памяти приложения
    set_dynamic_smtp_setting("SMTP_PASSWORD", new_pwd)
    if body.username:
        set_dynamic_smtp_setting("SMTP_USERNAME", body.username.strip())
    if body.from_email:
        set_dynamic_smtp_setting("SMTP_FROM", body.from_email.strip())
    if body.server:
        set_dynamic_smtp_setting("SMTP_SERVER", body.server.strip())
    if body.port:
        set_dynamic_smtp_setting("SMTP_PORT", str(body.port))

    # Обновляем в файле .env на диске
    update_env_file("SMTP_PASSWORD", new_pwd)
    if body.username:
        update_env_file("SMTP_USERNAME", body.username.strip())
    if body.from_email:
        update_env_file("SMTP_FROM", body.from_email.strip())

    return {
        "success": True,
        "connected": connected,
        "message": conn_msg if connected else f"Пароль сохранен, но почтовый сервер сообщил: {conn_msg}",
    }


@router.post("/smtp-test-connection")
async def test_smtp_connection_endpoint(
    body: SmtpTestConnectionRequest,
    current_user: User = Depends(require_smtp_manager),
):
    """
    Проверка связи с SMTP сервером с текущим или переданным паролем.
    """
    connected, conn_msg = check_smtp_connection(
        server=body.server,
        port=body.port,
        user=body.username,
        pwd=body.password,
    )
    return {
        "connected": connected,
        "message": conn_msg,
    }


@router.post("/smtp-send-test")
async def send_self_test_email(
    request: Request,
    body: SmtpSelfTestRequest,
    current_user: User = Depends(require_smtp_manager),
):
    """
    Отправка тестового письма исключительно на адрес текущего пользователя (Yuliya.e.novikova@rt.ru).
    """
    recipient = current_user.email
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
            email=recipient,
            full_name=current_user.full_name or "Юлия Новикова",
            password="DemoPassword2026!",
            base_url=base_url,
        )
        results["registration"] = {
            "status": "sent" if reg_res else ("mock_printed" if not is_smtp_configured() else "failed"),
            "success": bool(reg_res),
        }

    if body.template in ("reminder", "all"):
        rem_res = await send_recruiter_weekly_reminder([recipient], base_url=base_url)
        results["reminder"] = rem_res

    return {
        "success": True,
        "recipient": recipient,
        "template": body.template,
        "smtp_configured": is_smtp_configured(),
        "delivery": results,
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
