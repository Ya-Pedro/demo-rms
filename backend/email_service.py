\
\
   
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
import os
import logging

logger = logging.getLogger(__name__)

                                               
conf = ConnectionConfig(
    MAIL_USERNAME=os.environ.get("SMTP_USERNAME", ""),
    MAIL_PASSWORD=os.environ.get("SMTP_PASSWORD", ""),
    MAIL_FROM=os.environ.get("SMTP_FROM", "noreply@rms-system.ru"),
    MAIL_PORT=int(os.environ.get("SMTP_PORT", 587)),
    MAIL_SERVER=os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
    MAIL_STARTTLS=os.environ.get("SMTP_STARTTLS", "True").lower() == "true",
    MAIL_SSL_TLS=os.environ.get("SMTP_SSL_TLS", "False").lower() == "true",
    USE_CREDENTIALS=os.environ.get("SMTP_USE_CREDENTIALS", "True").lower() == "true",
    VALIDATE_CERTS=os.environ.get("SMTP_VALIDATE_CERTS", "True").lower() == "true"
)

async def send_welcome_email(email: EmailStr, full_name: str, password: str) -> bool:
\
\
\
       
                                 
    if not conf.MAIL_USERNAME or not conf.MAIL_PASSWORD:
        logger.warning(f"SMTP not configured. Printing credentials to console.")
        print("\n" + "="*50)
        print("[MOCK EMAIL] Новый пользователь создан")
        print(f"Кому: {email}")
        print(f"ФИО: {full_name}")
        print(f"Login: {email}")
        print(f"Pass: {password}")
        print("="*50 + "\n")
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
            subtype=MessageType.html
        )
        
        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info(f"Welcome email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {str(e)}")
        print("\n" + "="*50)
        print(f"[EMAIL ERROR] Не удалось отправить email: {str(e)}")
        print(f"[MOCK EMAIL] Новый пользователь создан")
        print(f"Login: {email}")
        print(f"Pass: {password}")
        print("="*50 + "\n")
        return False

async def send_password_reset_email(email: EmailStr, full_name: str, password: str) -> bool:
                                                                
    if not conf.MAIL_USERNAME or not conf.MAIL_PASSWORD:
        logger.warning(f"SMTP not configured. Printing reset credentials to console.")
        print("\n" + "="*50)
        print("[MOCK EMAIL] Сброс пароля")
        print(f"Кому: {email}")
        print(f"ФИО: {full_name}")
        print(f"Новый пароль: {password}")
        print("="*50 + "\n")
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
            subtype=MessageType.html
        )
        
        fm = FastMail(conf)
        await fm.send_message(message)
        logger.info(f"Password reset email sent to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send reset email to {email}: {str(e)}")
        print("\n" + "="*50)
        print(f"[EMAIL ERROR] Не удалось отправить email: {str(e)}")
        print(f"[MOCK EMAIL] Сброс пароля")
        print(f"Login: {email}")
        print(f"Новый пароль: {password}")
        print("="*50 + "\n")
        return False
