#!/usr/bin/env python3
"""
Скрипт для тестирования и подробной диагностики отправки почты из консоли.
Позволяет:
1. Выполнить пошаговую диагностику: DNS-резолв хоста, TCP-соединение, TLS/SSL рукопожатие, SMTP авторизацию.
2. Отправить реальное тестовое письмо с подробным протокольным логом диалога (set_debuglevel=2).
3. Переопределять параметры прямо из аргументов командной строки (--server, --port, --user, --password и т.д.).
"""

import argparse
import asyncio
import os
import smtplib
import socket
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from email_service import (
    is_smtp_configured,
    get_mail_config,
    send_registration_email,
    send_recruiter_weekly_reminder,
)


def mask_password(pwd: str) -> str:
    if not pwd:
        return "[НЕ ЗАДАН]"
    if len(pwd) <= 4:
        return "****"
    return pwd[:2] + "*" * (len(pwd) - 4) + pwd[-2:]


def check_smtp_connection(debug: bool = False, insecure: bool = False) -> tuple[bool, str]:
    server = os.environ.get("SMTP_SERVER", "").strip()
    port = int(os.environ.get("SMTP_PORT", 587))
    user = os.environ.get("SMTP_USERNAME", "").strip()
    pwd = os.environ.get("SMTP_PASSWORD", "").strip()
    use_ssl = os.environ.get("SMTP_SSL_TLS", "False").lower() == "true"
    use_starttls = os.environ.get("SMTP_STARTTLS", "True").lower() == "true"
    use_cred = os.environ.get("SMTP_USE_CREDENTIALS", "True").lower() == "true"

    if port == 465:
        use_ssl, use_starttls = True, False
    elif port in (587, 25):
        use_ssl, use_starttls = False, True

    if not server:
        return False, "SMTP_SERVER не указан"

    print("\n--- Шаг 1: DNS-резолв хоста ---")
    try:
        ip = socket.gethostbyname(server)
        print(f"[OK] Домен '{server}' успешно разрешен в IP: {ip}")
    except Exception as e:
        return False, f"Ошибка DNS: сервер не может определить IP для '{server}' ({e}).\n" \
                      "Убедитесь, что стенд подключен к корпоративной сети/VPN или указан правильный DNS."

    print("\n--- Шаг 2: Проверка TCP-порта ---")
    try:
        sock = socket.create_connection((server, port), timeout=6)
        sock.close()
        print(f"[OK] Порт {port} на {server} открыт и доступен для подключения.")
    except Exception as e:
        return False, f"Ошибка сети: невозможно подключиться к {server}:{port} ({e}).\n" \
                      "Порт может блокироваться фаерволом или шлюз недоступен по этому порту."

    print("\n--- Шаг 3: SMTP-протокол, шифрование и авторизация ---")
    try:
        context = ssl.create_default_context()
        validate_certs = not insecure and (os.environ.get("SMTP_VALIDATE_CERTS", "True").lower() == "true")
        if not validate_certs:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        if use_ssl or port == 465:
            print(f"Подключение через SMTP_SSL к {server}:{port}...")
            with smtplib.SMTP_SSL(server, port, context=context, timeout=10) as s:
                if debug:
                    s.set_debuglevel(2)
                if use_cred and user and pwd:
                    print(f"Попытка авторизации под пользователем '{user}'...")
                    s.login(user, pwd)
                    print("[OK] Авторизация успешна!")
                return True, "Успешное подключение и авторизация (SSL/TLS порт 465)"
        else:
            print(f"Подключение через SMTP к {server}:{port}...")
            with smtplib.SMTP(server, port, timeout=10) as s:
                if debug:
                    s.set_debuglevel(2)
                s.ehlo()
                if use_starttls:
                    print("Запуск STARTTLS рукопожатия...")
                    s.starttls(context=context)
                    s.ehlo()
                    print("[OK] Шифрование STARTTLS установлено!")
                if use_cred and user and pwd:
                    print(f"Попытка авторизации под пользователем '{user}'...")
                    s.login(user, pwd)
                    print("[OK] Авторизация успешна!")
                return True, f"Успешное подключение и авторизация (STARTTLS порт {port})"
    except ssl.SSLCertVerificationError as e:
        return False, f"Ошибка проверки SSL-сертификата: {e}.\n" \
                      "Корпоративный сертификат не распознан. Добавьте флаг --insecure."
    except smtplib.SMTPAuthenticationError as e:
        err_text = e.smtp_error.decode("utf-8", errors="ignore") if hasattr(e, "smtp_error") and isinstance(e.smtp_error, bytes) else str(e)
        return False, f"Ошибка авторизации (неверный логин или пароль): {err_text}"
    except smtplib.SMTPConnectError as e:
        return False, f"Не удалось подключиться к серверу {server}:{port}: {e}"
    except Exception as e:
        return False, f"Сбой SMTP: {type(e).__name__}: {e}"


def send_raw_test_email(recipient: str, debug: bool = True, insecure: bool = False) -> tuple[bool, str]:
    server = os.environ.get("SMTP_SERVER", "").strip()
    port = int(os.environ.get("SMTP_PORT", 587))
    user = os.environ.get("SMTP_USERNAME", "").strip()
    pwd = os.environ.get("SMTP_PASSWORD", "").strip()
    from_addr = os.environ.get("SMTP_FROM", "").strip() or user
    use_ssl = os.environ.get("SMTP_SSL_TLS", "False").lower() == "true"
    use_starttls = os.environ.get("SMTP_STARTTLS", "True").lower() == "true"

    if port == 465:
        use_ssl, use_starttls = True, False
    elif port in (587, 25):
        use_ssl, use_starttls = False, True

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Тестовое сообщение RMS (Диагностика SMTP)"
    msg["From"] = from_addr
    msg["To"] = recipient

    text_body = "Это проверочное письмо из консоли RMS для тестирования SMTP-шлюза."
    html_body = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #f8fafc; color: #1e293b;">
        <h2 style="color: #4f46e5;">RMS &mdash; Проверка отправки почты</h2>
        <p>Это тестовое сообщение, отправленное напрямую из консоли для проверки сетевой связности, авторизации и релея.</p>
        <div style="background: #ffffff; padding: 15px; border-radius: 6px; border: 1px solid #e2e8f0; margin-top: 15px;">
            <b>SMTP сервер:</b> {server}:{port}<br>
            <b>Отправитель:</b> {from_addr}<br>
            <b>Получатель:</b> {recipient}
        </div>
    </div>
    """
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    context = ssl.create_default_context()
    validate_certs = not insecure and (os.environ.get("SMTP_VALIDATE_CERTS", "True").lower() == "true")
    if not validate_certs:
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

    try:
        print("\n--- Отправка тестового письма с подробным протокольным логом (set_debuglevel=2) ---")
        if use_ssl or port == 465:
            with smtplib.SMTP_SSL(server, port, context=context, timeout=12) as s:
                if debug:
                    s.set_debuglevel(2)
                if user and pwd:
                    s.login(user, pwd)
                s.sendmail(from_addr, [recipient], msg.as_string())
        else:
            with smtplib.SMTP(server, port, timeout=12) as s:
                if debug:
                    s.set_debuglevel(2)
                s.ehlo()
                if use_starttls:
                    s.starttls(context=context)
                    s.ehlo()
                if user and pwd:
                    s.login(user, pwd)
                s.sendmail(from_addr, [recipient], msg.as_string())
        return True, f"Письмо успешно передано почтовому серверу для отправки на {recipient}!"
    except Exception as e:
        return False, f"Ошибка при отправке письма: {type(e).__name__}: {e}"


async def main():
    parser = argparse.ArgumentParser(
        description="Тестирование и диагностика отправки почты RMS из консоли"
    )
    parser.add_argument(
        "recipient",
        nargs="?",
        default=None,
        help="Email получателя для отправки тестового письма",
    )
    parser.add_argument(
        "--server",
        default=None,
        help="SMTP сервер (переопределяет настройки, например: smtp.rt.ru)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="SMTP порт (25, 465, 587)",
    )
    parser.add_argument(
        "--user",
        default=None,
        help="Логин пользователя SMTP (например, RMS@gd.rt.ru)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="Пароль пользователя SMTP",
    )
    parser.add_argument(
        "--from-addr",
        default=None,
        help="Адрес отправителя (From, по умолчанию равен user)",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Отключить строгую проверку SSL-сертификата (полезно для корпоративных УЦ Ростелекома)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=True,
        help="Включить подробный протокольный вывод SMTP команд и ответов сервера (включен по умолчанию)",
    )
    parser.add_argument(
        "--no-debug",
        dest="debug",
        action="store_false",
        help="Отключить подробный протокольный вывод",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Только проверить настройки и подключение к SMTP без отправки писем",
    )
    parser.add_argument(
        "--template",
        choices=["raw", "registration", "reminder", "all"],
        default="raw",
        help="Шаблон письма: 'raw' (прямой тест smtplib с протокольным логом), 'registration', 'reminder' или 'all'",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("RMS_BASE_URL", "https://rms.ittori.online"),
        help="Базовый URL системы для ссылок в письме",
    )

    args = parser.parse_args()

    # Сначала пытаемся подгрузить настройки из БД, если база доступна
    try:
        from database import AsyncSessionLocal
        from email_service import load_smtp_settings_from_db
        async with AsyncSessionLocal() as session:
            await load_smtp_settings_from_db(session)
    except Exception:
        pass

    # Переопределяем параметры, если они переданы через CLI аргументы
    if args.server:
        os.environ["SMTP_SERVER"] = args.server.strip()
    if args.port:
        os.environ["SMTP_PORT"] = str(args.port)
        if args.port == 465:
            os.environ["SMTP_SSL_TLS"] = "True"
            os.environ["SMTP_STARTTLS"] = "False"
        else:
            os.environ["SMTP_SSL_TLS"] = "False"
            os.environ["SMTP_STARTTLS"] = "True"
    if args.user:
        os.environ["SMTP_USERNAME"] = args.user.strip()
    if args.password:
        os.environ["SMTP_PASSWORD"] = args.password.strip()
    if args.from_addr:
        os.environ["SMTP_FROM"] = args.from_addr.strip()
    elif args.user and not os.environ.get("SMTP_FROM"):
        os.environ["SMTP_FROM"] = args.user.strip()
    if args.insecure:
        os.environ["SMTP_VALIDATE_CERTS"] = "False"

    print("\n" + "=" * 65)
    print("      ДИАГНОСТИКА И ТЕСТИРОВАНИЕ ОТПРАВКИ EMAIL В RMS      ")
    print("=" * 65)

    server = os.environ.get("SMTP_SERVER", "")
    port = os.environ.get("SMTP_PORT", "")
    user = os.environ.get("SMTP_USERNAME", "")
    pwd = os.environ.get("SMTP_PASSWORD", "")
    from_addr = os.environ.get("SMTP_FROM", "") or user
    ssl_tls = os.environ.get("SMTP_SSL_TLS", "")
    starttls = os.environ.get("SMTP_STARTTLS", "")
    val_certs = os.environ.get("SMTP_VALIDATE_CERTS", "True")

    print(f"SMTP Сервер:       {server or '[НЕ ЗАДАН]'}")
    print(f"SMTP Порт:         {port or '[НЕ ЗАДАН]'}")
    print(f"Пользователь:      {user or '[НЕ ЗАДАН]'}")
    print(f"Пароль:            {mask_password(pwd)}")
    print(f"Адрес отправителя: {from_addr or '[НЕ ЗАДАН]'}")
    print(f"SSL/TLS (порт 465):{ssl_tls}")
    print(f"STARTTLS (587):    {starttls}")
    print(f"Проверка SSL серт: {val_certs}")
    print("-" * 65)

    # Запускаем пошаговую диагностику соединения
    print("Запуск проверки сетевого подключения к SMTP серверу...")
    ok, msg = check_smtp_connection(debug=args.debug, insecure=args.insecure)
    if ok:
        print(f"\n[УСПЕХ] {msg}")
    else:
        print(f"\n[ОШИБКА ДИАГНОСТИКИ]\n{msg}")
        if args.check_only:
            sys.exit(1)

    print("=" * 65 + "\n")

    if args.check_only:
        return

    recipient = args.recipient
    if not recipient:
        try:
            recipient = input("Введите email получателя для отправки тестового письма: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nОтменено.")
            return

    if not recipient or "@" not in recipient:
        print("Ошибка: указан некорректный email получателя.")
        sys.exit(1)

    print(f"Запуск отправки тестового письма на: {recipient}")
    print(f"Отправитель: {from_addr}")
    print(f"Режим отправки: {args.template}\n")

    # 1. Прямой тест через smtplib с протокольным выводом
    if args.template in ("raw", "all"):
        ok, res_msg = send_raw_test_email(
            recipient=recipient,
            debug=args.debug,
            insecure=args.insecure,
        )
        if ok:
            print(f"\n[УСПЕХ] {res_msg}")
        else:
            print(f"\n[ОШИБКА ОТПРАВКИ]\n{res_msg}")

    # 2. Шаблон регистрации
    if args.template in ("registration", "all"):
        print("-" * 65)
        print("Тестирование шаблона «Регистрация нового пользователя»")
        success = await send_registration_email(
            email=recipient,
            full_name="Тестовый Пользователь",
            password="DemoPassword2026!",
            base_url=args.base_url,
        )
        if success:
            print(f"[УСПЕХ] Письмо регистрации успешно отправлено на {recipient}!")
        else:
            print(f"[ОШИБКА] Не удалось отправить письмо регистрации.")

    # 3. Шаблон напоминания
    if args.template in ("reminder", "all"):
        print("\n" + "-" * 65)
        print("Тестирование шаблона «Еженедельное напоминание рекрутерам»")
        res = await send_recruiter_weekly_reminder(
            recipients=[recipient],
            base_url=args.base_url,
        )
        if res.get("status") == "sent":
            print(f"[УСПЕХ] Напоминание успешно отправлено на {recipient}!")
        else:
            print(f"[ОШИБКА] Не удалось отправить напоминание: {res}")

    print("\n" + "=" * 65)
    print("Диагностика завершена.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
