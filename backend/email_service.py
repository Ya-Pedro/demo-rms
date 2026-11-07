from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
import os
import logging

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


async def send_welcome_email(email: EmailStr, full_name: str, password: str) -> bool:
    if not is_smtp_configured():
        logger.warning(f"SMTP not configured. Printing credentials to console.")
        print("\n" + "=" * 50)
        print("[MOCK EMAIL] Новый пользователь создан")
        print(f"Кому: {email}")
        print(f"ФИО: {full_name}")
        print(f"Login: {email}")
        print(f"Pass: {password}")
        print("=" * 50 + "\n")
        return False

    try:
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #0050B3;">Добро пожаловать в RMS!</h2>
            <p>Уважаемый(ая) <strong>{full_name}</strong>,</p>
            <p>Для вас создана учетная запись в системе управления вакансиями RMS.</p>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Email:</strong> {email}</p>
                <p style="margin: 5px 0;"><strong>Пароль:</strong> {password}</p>
            </div>
            <p style="color: #ff4d4f;"><strong>Важно:</strong> При первом входе система потребует сменить пароль.</p>
            <hr style="border: none; border-top: 1px solid #d9d9d9; margin: 20px 0;">
            <p style="color: #8c8c8c; font-size: 12px;">
                Это автоматическое сообщение. Пожалуйста, не отвечайте на него.
            </p>
        </body>
        </html>
        """

        message = MessageSchema(
            subject="Добро пожаловать в RMS - Ваши учетные данные",
            recipients=[email],
            body=html_body,
            subtype=MessageType.html,
        )

        fm = FastMail(get_mail_config())
        await fm.send_message(message)
        logger.info(f"Welcome email sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        print("\n" + "=" * 50)
        print(f"[EMAIL ERROR] Не удалось отправить email: {str(e)}")
        print(f"[MOCK EMAIL] Новый пользователь создан")
        print(f"Login: {email}")
        print(f"Pass: {password}")
        print("=" * 50 + "\n")
        return False


async def send_password_reset_email(email: EmailStr, full_name: str, password: str) -> bool:
    if not is_smtp_configured():
        logger.warning(f"SMTP not configured. Printing reset credentials to console.")
        print("\n" + "=" * 50)
        print("[MOCK EMAIL] Сброс пароля")
        print(f"Кому: {email}")
        print(f"ФИО: {full_name}")
        print(f"Новый пароль: {password}")
        print("=" * 50 + "\n")
        return False

    try:
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #0050B3;">Сброс пароля RMS</h2>
            <p>Уважаемый(ая) <strong>{full_name}</strong>,</p>
            <p>Ваш пароль был сброшен. Используйте новый временный пароль для входа:</p>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 4px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Email:</strong> {email}</p>
                <p style="margin: 5px 0;"><strong>Новый пароль:</strong> {password}</p>
            </div>
            <p style="color: #ff4d4f;"><strong>Важно:</strong> При входе система потребует создать новый пароль.</p>
            <hr style="border: none; border-top: 1px solid #d9d9d9; margin: 20px 0;">
            <p style="color: #8c8c8c; font-size: 12px;">
                Если вы не запрашивали сброс пароля, обратитесь к администратору.
            </p>
        </body>
        </html>
        """

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


async def send_recruiter_weekly_reminder(recipients: list[str]) -> dict:
    subject = "Заполнение отчетности в RMS"
    text_content = (
        "Привет, не забудь заполнить отчет по вакансиям за текущую неделю.\n"
        "Срок заполнения- сегодня до конца рабочего дня.\n\n"
        "Система http://rms-poc-sandbox.apps.stage.rt.ru/\n"
        "Инструкция по работе в системе \\\\sks10fs003.ks.rt.ru\\RTI\\Общая\\Прием\\БАЗА_ЗНАНИЙ\\Рекрутмент\\RMS система"
    )

    html_content = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 20px; }
    .card { max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 28px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .header { margin-bottom: 20px; padding-bottom: 14px; border-bottom: 2px solid #f1f5f9; }
    .title { font-size: 22px; font-weight: 800; background: linear-gradient(135deg, #4f46e5 0%, #ec4899 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }
    .content { font-size: 15px; color: #334155; margin-bottom: 20px; }
    .deadline { background: #fef2f2; border-left: 4px solid #ef4444; padding: 12px 16px; border-radius: 4px; margin: 16px 0; font-weight: 600; color: #991b1b; }
    .btn { display: inline-block; background: #1677ff; color: #ffffff !important; font-weight: 600; text-decoration: none; padding: 12px 24px; border-radius: 6px; margin: 14px 0; }
    .info-box { background: #f8fafc; border: 1px solid #e2e8f0; padding: 14px 16px; border-radius: 8px; font-size: 13px; color: #475569; word-break: break-all; margin-top: 16px; }
    .footer { margin-top: 24px; font-size: 12px; color: #94a3b8; text-align: center; }
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1 class="title">RMS</h1>
    </div>
    <div class="content">
      <p style="font-size: 16px; margin-top: 0;">Привет, не забудь заполнить отчет по вакансиям за текущую неделю.</p>
      <div class="deadline">
        ⏰ Срок заполнения — сегодня до конца рабочего дня.
      </div>
      <p>
        <a href="http://rms-poc-sandbox.apps.stage.rt.ru/" class="btn" target="_blank">Перейти в систему RMS</a>
      </p>
      <div class="info-box">
        <p style="margin: 0 0 8px 0;"><strong>Система:</strong> <a href="http://rms-poc-sandbox.apps.stage.rt.ru/" style="color: #1677ff;">http://rms-poc-sandbox.apps.stage.rt.ru/</a></p>
        <p style="margin: 0;"><strong>Инструкция по работе в системе:</strong><br><code style="font-family: monospace; background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-size: 12px;">\\\\sks10fs003.ks.rt.ru\\RTI\\Общая\\Прием\\БАЗА_ЗНАНИЙ\\Рекрутмент\\RMS система</code></p>
      </div>
    </div>
    <div class="footer">
      Это автоматическое напоминание из системы управления рекрутментом RMS.
    </div>
  </div>
</body>
</html>"""

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
