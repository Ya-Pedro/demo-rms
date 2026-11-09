#!/usr/bin/env python3
"""
Скрипт для тестирования отправки почты из консоли.
Позволяет проверить:
1. Текущие настройки подключения к SMTP серверу
2. Шаблон письма при регистрации нового пользователя (учетные данные)
3. Шаблон письма еженедельного напоминания по пятницам в 13:00 (заполнение отчетов)
"""

import argparse
import asyncio
import os
import smtplib
import ssl
import sys

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


def check_smtp_connection() -> tuple[bool, str]:
    server = os.environ.get("SMTP_SERVER", "").strip()
    port = int(os.environ.get("SMTP_PORT", 587))
    user = os.environ.get("SMTP_USERNAME", "").strip()
    pwd = os.environ.get("SMTP_PASSWORD", "").strip()
    use_ssl = os.environ.get("SMTP_SSL_TLS", "False").lower() == "true"
    use_starttls = os.environ.get("SMTP_STARTTLS", "True").lower() == "true"
    use_cred = os.environ.get("SMTP_USE_CREDENTIALS", "True").lower() == "true"

    if not server:
        return False, "SMTP_SERVER не указан"

    try:
        context = ssl.create_default_context()
        if not os.environ.get("SMTP_VALIDATE_CERTS", "True").lower() == "true":
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        if use_ssl or port == 465:
            with smtplib.SMTP_SSL(server, port, context=context, timeout=10) as s:
                if use_cred and user and pwd:
                    s.login(user, pwd)
                return True, "Успешное подключение и авторизация (SSL/TLS)"
        else:
            with smtplib.SMTP(server, port, timeout=10) as s:
                s.ehlo()
                if use_starttls:
                    s.starttls(context=context)
                    s.ehlo()
                if use_cred and user and pwd:
                    s.login(user, pwd)
                return True, "Успешное подключение и авторизация (STARTTLS/Plain)"
    except smtplib.SMTPAuthenticationError as e:
        return False, f"Ошибка авторизации SMTP (неверный логин или пароль приложения): {e}"
    except smtplib.SMTPConnectError as e:
        return False, f"Не удалось подключиться к серверу {server}:{port}: {e}"
    except Exception as e:
        return False, f"Сбой подключения к SMTP: {type(e).__name__}: {e}"


async def main():
    parser = argparse.ArgumentParser(
        description="Тестирование отправки корпоративных email-сообщений RMS из консоли"
    )
    parser.add_argument(
        "recipient",
        nargs="?",
        default=None,
        help="Email получателя для отправки тестового письма",
    )
    parser.add_argument(
        "--template",
        choices=["all", "registration", "reminder"],
        default="all",
        help="Шаблон для отправки: 'registration' (регистрация), 'reminder' (напоминание в пятницу 13:00) или 'all' (оба)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("RMS_BASE_URL", "https://rms.ittori.online"),
        help="Базовый URL системы для ссылок в письме (по умолчанию https://rms.ittori.online)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Только проверить настройки и подключение к SMTP без отправки писем",
    )

    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("      ДИАГНОСТИКА И ТЕСТИРОВАНИЕ ОТПРАВКИ EMAIL В RMS      ")
    print("=" * 65)

    server = os.environ.get("SMTP_SERVER", "")
    port = os.environ.get("SMTP_PORT", "")
    user = os.environ.get("SMTP_USERNAME", "")
    pwd = os.environ.get("SMTP_PASSWORD", "")
    from_addr = os.environ.get("SMTP_FROM", "")
    ssl_tls = os.environ.get("SMTP_SSL_TLS", "")
    starttls = os.environ.get("SMTP_STARTTLS", "")
    configured = is_smtp_configured()

    print(f"SMTP Сервер:       {server or '[НЕ ЗАДАН]'}")
    print(f"SMTP Порт:         {port or '[НЕ ЗАДАН]'}")
    print(f"Пользователь:      {user or '[НЕ ЗАДАН]'}")
    print(f"Пароль:            {mask_password(pwd)}")
    print(f"Адрес отправителя: {from_addr or '[НЕ ЗАДАН]'}")
    print(f"SSL/TLS (порт 465):{ssl_tls}")
    print(f"STARTTLS (587):    {starttls}")
    print(f"Статус настройки:  {'Настроен (Active)' if configured else 'Не настроен (Используется MOCK режим)'}")
    print("-" * 65)

    if configured:
        print("Проверка подключения к SMTP серверу...")
        ok, msg = check_smtp_connection()
        if ok:
            print(f"[OK] {msg}")
        else:
            print(f"[ВНИМАНИЕ / ОШИБКА] {msg}")
    else:
        print("[ИНФО] В .env используются значения по умолчанию или заглушки.")
        print("Письма будут выводиться в консоль (MOCK-режим).")
        print("Для отправки реальных писем укажите параметры в backend/.env:")
        print("  - Для Яндекс 360 / Yandex: SMTP_SERVER=smtp.yandex.ru, SMTP_PORT=465, SMTP_SSL_TLS=True")
        print("  - Для Mail.ru:             SMTP_SERVER=smtp.mail.ru, SMTP_PORT=465, SMTP_SSL_TLS=True")
        print("  - Для Корпоративного SMTP: SMTP_SERVER=smtp.company.ru, SMTP_PORT=25/587")

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

    print(f"Запуск отправки тестовых писем на: {recipient}")
    print(f"Выбранный шаблон: {args.template}")
    print(f"Базовый адрес системы: {args.base_url}\n")

    # 1. Шаблон регистрации
    if args.template in ("registration", "all"):
        print("-" * 65)
        print("1. Тестирование шаблона «Регистрация нового пользователя»")
        print("   Тема: Регистрация в системе RMS — Ваши учетные данные")
        print("   Включает: логин, сгенерированный пароль, ссылку на вход")
        print("-" * 65)

        success = await send_registration_email(
            email=recipient,
            full_name="Тестовый Пользователь",
            password="DemoPassword2026!",
            base_url=args.base_url,
        )
        if success:
            print(f"[УСПЕХ] Письмо регистрации успешно отправлено через SMTP на {recipient}!")
        elif not configured:
            print(f"[MOCK] Письмо регистрации успешно сымитировано (MOCK-режим).")
        else:
            print(f"[ОШИБКА] Не удалось отправить письмо регистрации (см. детали выше).")

    # 2. Шаблон пятничного напоминания (13:00)
    if args.template in ("reminder", "all"):
        print("\n" + "-" * 65)
        print("2. Тестирование шаблона «Еженедельное напоминание рекрутерам (Пятница 13:00)»")
        print("   Тема: Заполнение отчетности в RMS")
        print("   Включает: корпоративный баннер, текст отбивки, кнопку перехода")
        print("-" * 65)

        res = await send_recruiter_weekly_reminder(
            recipients=[recipient],
            base_url=args.base_url,
        )
        if res.get("status") == "sent":
            print(f"[УСПЕХ] Еженедельное напоминание успешно отправлено через SMTP на {recipient}!")
        elif res.get("status") == "mock_sent":
            print(f"[MOCK] Еженедельное напоминание успешно сымитировано (MOCK-режим).")
        else:
            print(f"[ОШИБКА] Не удалось отправить напоминание: {res}")

    print("\n" + "=" * 65)
    print("Тестирование завершено.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
