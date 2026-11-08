from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from typing import Optional
import os
import logging
from email_templates import (
    get_recruiter_weekly_reminder_html,
    get_registration_email_html,
    get_welcome_email_html,
    get_password_reset_email_html,
)

logger = logging.getLogger(__name__)


def get_mail_config() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=os.environ.get("SMTP_USERNAME", ""),
        MAIL_PASSWORD=os.environ.get("SMTP_PASSWORD", ""),
        MAIL_FROM=os.environ.get("SMTP_FROM", "noreply@rms-system.ru"),
        MAIL_PORT=int(os.environ.get("SMTP_PORT", 587)),
        MAIL_SERVER=os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
        MAIL_STARTTLS=os.environ.get("SMTP_STARTTLS", "True").lower() == "true",
        MAIL_SSL_TLS=os.environ.get("SMTP_SSL_TLS", "False").lower() == "true",
        USE_CREDENTIALS=os.environ.get("SMTP_USE_CREDENTIALS", "True").lower() == "true",
        VALIDATE_CERTS=os.environ.get("SMTP_VALIDATE_CERTS", "True").lower() == "true",
        MAIL_FROM_NAME=os.environ.get("SMTP_FROM_NAME", "RMS Уведомления"),
    )


def is_smtp_configured() -> bool:
    server = os.environ.get("SMTP_SERVER", "").strip()
    user = os.environ.get("SMTP_USERNAME", "").strip()
    pwd = os.environ.get("SMTP_PASSWORD", "").strip()
    use_cred = os.environ.get("SMTP_USE_CREDENTIALS", "True").lower() == "true"

    if not server:
        return False
    # Check default placeholders
    if "yandex" in server.lower() or "gmail" in server.lower():
        if "your_email" in user or "REPLACE_WITH" in pwd or not pwd:
            return False
    if use_cred and (not user or not pwd or "your_email" in user or "REPLACE_WITH" in pwd):
        return False
    return True


# Backward compatibility global conf
conf = get_mail_config()


async def send_registration_email(
    email: EmailStr,
    full_name: str,
    password: str,
    base_url: Optional[str] = None
) -> bool:
    if not is_smtp_configured():
        logger.warning("SMTP not configured. Printing registration credentials to console.")
        print("\n" + "=" * 55)
        print("[MOCK EMAIL] Регистрация в системе RMS")
        print(f"Кому: {email}")
        print(f"ФИО: {full_name}")
        print(f"Логин (Email): {email}")
        print(f"Временный пароль: {password}")
        print(f"Адрес системы: {base_url or 'http://rms-poc-sandbox.apps.stage.rt.ru/'}")
        print("=" * 55 + "\n")
        return False

    try:
        html_body = get_registration_email_html(
            full_name=full_name,
            email=email,
            password=password,
            base_url=base_url
        )

        message = MessageSchema(
            subject="Регистрация в системе RMS — Ваши учетные данные",
            recipients=[email],
            body=html_body,
            subtype=MessageType.html,
        )

        fm = FastMail(get_mail_config())
        await fm.send_message(message)
        logger.info(f"Registration email sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send registration email to {email}: {str(e)}")
        print("\n" + "=" * 55)
        print(f"[EMAIL ERROR] Не удалось отправить письмо регистрации: {str(e)}")
        print("[MOCK EMAIL] Регистрация в системе RMS")
        print(f"Кому: {email}")
        print(f"Логин: {email}")
        print(f"Пароль: {password}")
        print("=" * 55 + "\n")
        return False


async def send_welcome_email(
    email: EmailStr,
    full_name: str,
    password: str,
    base_url: Optional[str] = None
) -> bool:
    return await send_registration_email(
        email=email,
        full_name=full_name,
        password=password,
        base_url=base_url
    )


async def send_password_reset_email(
    email: EmailStr,
    full_name: str,
    password: str,
    base_url: Optional[str] = None
) -> bool:
    if not is_smtp_configured():
        logger.warning(f"SMTP not configured. Printing reset credentials to console.")
        print("\n" + "=" * 55)
        print("[MOCK EMAIL] Сброс пароля в RMS")
        print(f"Кому: {email}")
        print(f"ФИО: {full_name}")
        print(f"Новый пароль: {password}")
        print(f"Адрес системы: {base_url or 'http://rms-poc-sandbox.apps.stage.rt.ru/'}")
        print("=" * 55 + "\n")
        return False

    try:
        html_body = get_password_reset_email_html(
            full_name=full_name,
            email=email,
            password=password,
            base_url=base_url
        )

        message = MessageSchema(
            subject="RMS - Сброс пароля",
            recipients=[email],
            body=html_body,
            subtype=MessageType.html,
        )

        fm = FastMail(get_mail_config())
        await fm.send_message(message)
        logger.info(f"Password reset email sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send reset email to {email}: {str(e)}")
        print("\n" + "=" * 50)
        print(f"[EMAIL ERROR] Не удалось отправить email: {str(e)}")
        print(f"[MOCK EMAIL] Сброс пароля")
        print(f"Login: {email}")
        print(f"Новый пароль: {password}")
        print("=" * 50 + "\n")
        return False


async def send_recruiter_weekly_reminder(recipients: list[str], base_url: Optional[str] = None) -> dict:
    resolved_url = (base_url or os.environ.get("RMS_BASE_URL", "http://rms-poc-sandbox.apps.stage.rt.ru")).rstrip('/')
    subject = "Заполнение отчетности в RMS"
    text_content = (
        "Привет, не забудь заполнить отчет по вакансиям за текущую неделю.\n"
        "Срок заполнения- сегодня до конца рабочего дня.\n\n"
        f"Система {resolved_url}/\n"
        "Инструкция по работе в системе \\\\sks10fs003.ks.rt.ru\\RTI\\Общая\\Прием\\БАЗА_ЗНАНИЙ\\Рекрутмент\\RMS система"
    )

    html_content = get_recruiter_weekly_reminder_html(base_url=resolved_url)

    clean_recipients = [r.strip() for r in recipients if r and "@" in r]
    if not clean_recipients:
        logger.warning("No valid recipients provided for weekly reminder.")
        return {"sent": 0, "failed": 0, "recipients": [], "status": "no_recipients"}

    configured = is_smtp_configured()
    if not configured:
        logger.info(f"[MOCK EMAIL] Еженедельное напоминание рекрутерам (SMTP не настроен): {len(clean_recipients)} получателей")
        print("\n" + "=" * 60)
        print("[MOCK EMAIL] Еженедельное напоминание рекрутерам о заполнении отчета")
        print(f"Количество получателей: {len(clean_recipients)}")
        print(f"Получатели: {', '.join(clean_recipients)}")
        print(f"Тема: {subject}")
        print("-" * 60)
        print(text_content)
        print("=" * 60 + "\n")
        return {
            "sent": len(clean_recipients),
            "failed": 0,
            "mock": True,
            "recipients": clean_recipients,
            "status": "mock_sent",
        }

    conf = get_mail_config()
    fm = FastMail(conf)

    sent_count = 0
    failed_recipients = []

    for email in clean_recipients:
        try:
            message = MessageSchema(
                subject=subject,
                recipients=[email],
                body=html_content,
                subtype=MessageType.html,
            )
            await fm.send_message(message)
            sent_count += 1
            logger.info(f"Weekly reminder email sent to {email}")
        except Exception as e:
            failed_recipients.append({"email": email, "error": str(e)})
            logger.error(f"Failed to send weekly reminder to {email}: {e}")

    return {
        "sent": sent_count,
        "failed": len(failed_recipients),
        "mock": False,
        "recipients": clean_recipients,
        "failed_recipients": failed_recipients,
        "status": "sent" if sent_count > 0 else "failed",
    }
