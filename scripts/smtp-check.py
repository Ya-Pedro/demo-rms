#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита диагностики корпоративного SMTP-шлюза (RMS Mail Checker).
Не требует установки сторонних библиотек (работает на стандартном Python 3.7+).

Использование:
    python3 smtp-check.py --server smtp.rt.ru --port 587 --user RMS@gd.rt.ru --password 'ВАШ_ПАРОЛЬ' --to my.email@rt.ru

Либо просто запуск без параметров (интерактивный режим с вводом с клавиатуры):
    python3 smtp-check.py
"""

import sys
import os
import socket
import ssl
import smtplib
import argparse
import getpass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Цветовое оформление для терминала
USE_COLOR = sys.stdout.isatty() and os.name != 'nt' or 'ANSICON' in os.environ or 'WT_SESSION' in os.environ

def _color(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

def green(t: str) -> str: return _color(t, "32;1")
def red(t: str) -> str: return _color(t, "31;1")
def yellow(t: str) -> str: return _color(t, "33;1")
def cyan(t: str) -> str: return _color(t, "36;1")
def bold(t: str) -> str: return _color(t, "1")


def print_banner():
    print(cyan("\n" + "=" * 68))
    print(cyan("     ДИАГНОСТИКА ПОДКЛЮЧЕНИЯ К ПОЧТОВОМУ СЕРВЕРУ (SMTP)     "))
    print(cyan("=" * 68 + "\n"))


def run_checks(server: str, port: int, user: str, password: str, to_email: str = None, from_email: str = None, insecure: bool = False, debug: bool = False):
    from_email = from_email or user

    print(bold("Параметры проверки:"))
    print(f"  • Сервер:       {server}")
    print(f"  • Порт:         {port}")
    print(f"  • Логин:        {user}")
    print(f"  • Пароль:       {'*' * len(password) if password else '[НЕ ЗАДАН]'}")
    print(f"  • Отправитель:  {from_email}")
    if to_email:
        print(f"  • Получатель:   {to_email}")
    print(f"  • Режим SSL:    {'STARTTLS' if port in (587, 25) else 'SSL/TLS'}")
    print(f"  • Проверка CA:  {'Отключена (--insecure)' if insecure else 'Включена (строгая)'}")
    print("-" * 68)

    # -------------------------------------------------------------
    # ШАГ 1: DNS-резолв
    # -------------------------------------------------------------
    print(f"\n{bold('[ШАГ 1/4] Проверка сетевого имени (DNS)...')}")
    try:
        resolved_ips = socket.getaddrinfo(server, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        ip_addresses = list(set([item[4][0] for item in resolved_ips]))
        print(green(f"  [OK] Домен '{server}' успешно найден."))
        print(f"       IP-адреса: {', '.join(ip_addresses)}")
    except socket.gaierror as e:
        print(red(f"  [ОШИБКА] Не удалось разрешить имя сервера '{server}': {e}"))
        print(yellow("  Причина: DNS-сервер не знает такой адрес."))
        print("  Что делать:")
        print("    1. Проверьте подключение к корпоративной сети или корпоративному VPN.")
        print("    2. Проверьте правильность написания адреса сервера (например, smtp.rt.ru).")
        print("    3. Если тестирование идет с внешнего ПК, нужен корпоративный DNS или VPN-канал.")
        return False
    except Exception as e:
        print(red(f"  [ОШИБКА] Неожиданная ошибка DNS: {e}"))
        return False

    # -------------------------------------------------------------
    # ШАГ 2: Доступность TCP-порта
    # -------------------------------------------------------------
    print(f"\n{bold(f'[ШАГ 2/4] Проверка связи с портом {port} (TCP connect)...')}")
    try:
        sock = socket.create_connection((server, port), timeout=7)
        sock.close()
        print(green(f"  [OK] Порт {port} открыт и принимает входящие соединения."))
    except socket.timeout:
        print(red(f"  [ОШИБКА] Превышено время ожидания (Connection timeout) к {server}:{port}"))
        print(yellow("  Причина: Сетевой экран (Firewall/ИБ) блокирует порт, либо сервер не отвечает."))
        print("  Что делать:")
        print(f"    1. Запросите у ИБ/сетевиков открытие порта {port} от вашего IP до {server}.")
        print("    2. Попробуйте альтернативный порт (например, 25 или 465).")
        return False
    except ConnectionRefusedError:
        print(red(f"  [ОШИБКА] Соединение отклонено (Connection refused) {server}:{port}"))
        print(yellow("  Причина: Сервер доступен, но служба SMTP не слушает на этом порту."))
        print("  Что делать: уточните у службы поддержки правильный номер порта (25, 465 или 587).")
        return False
    except Exception as e:
        print(red(f"  [ОШИБКА] Не удалось подключиться к порту: {e}"))
        return False

    # -------------------------------------------------------------
    # ШАГ 3: SMTP-протокол, шифрование и аутентификация
    # -------------------------------------------------------------
    print(f"\n{bold('[ШАГ 3/4] Проверка протокола SMTP и авторизации техучетки...')}")
    smtp_client = None
    try:
        # Настройка SSL контекста
        ssl_ctx = ssl.create_default_context()
        if insecure:
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

        if port == 465:
            print("  Установка SSL/TLS соединения на порту 465...")
            smtp_client = smtplib.SMTP_SSL(server, port, context=ssl_ctx, timeout=10)
        else:
            print(f"  Подключение к SMTP на порту {port}...")
            smtp_client = smtplib.SMTP(server, port, timeout=10)

        if debug:
            smtp_client.set_debuglevel(2)

        if port != 465:
            smtp_client.ehlo()
            if smtp_client.has_extn("STARTTLS"):
                print("  Сервер поддерживает STARTTLS. Запуск шифрования канала...")
                smtp_client.starttls(context=ssl_ctx)
                smtp_client.ehlo()
                print(green("  [OK] Канал связи зашифрован (STARTTLS)."))
            else:
                print(yellow("  [ИНФО] Сервер не запросил STARTTLS, продолжаю в открытом канале."))

        if user and password:
            print(f"  Проверка логина '{user}' и пароля...")
            smtp_client.login(user, password)
            print(green("  [OK] Авторизация успешна! Учетные данные верны."))
        else:
            print(yellow("  [ИНФО] Логин или пароль не указаны. Проверка авторизации пропущена."))

    except ssl.SSLCertVerificationError as e:
        print(red(f"  [ОШИБКА SSL] Проверка сертификата не удалась: {e}"))
        print(yellow("  Причина: Шлюз использует внутренний корпоративный сертификат (Ростелеком CA / Минцифры)."))
        print("  Что делать:")
        print("    Перезапустите утилиту с флагом " + bold("--insecure") + " (шифрование сохранится, проверка цепочки публичных центров будет отключена).")
        if smtp_client:
            try: smtp_client.close()
            except: pass
        return False
    except smtplib.SMTPAuthenticationError as e:
        err_msg = e.smtp_error.decode("utf-8", errors="ignore") if hasattr(e, "smtp_error") and isinstance(e.smtp_error, bytes) else str(e)
        print(red(f"  [ОШИБКА АВТОРИЗАЦИИ] Код {e.smtp_code}: {err_msg}"))
        print(yellow("  Причина: Сервер отверг имя пользователя или пароль."))
        print("  Что делать:")
        print("    1. Проверьте правильность пароля.")
        print("    2. Проверьте формат логина. Иногда требуется указать с доменом, например:")
        print(f"       'gd\\RMS' или 'rt\\RMS' вместо '{user}'.")
        if smtp_client:
            try: smtp_client.close()
            except: pass
        return False
    except Exception as e:
        print(red(f"  [ОШИБКА] Сбой на этапе SMTP: {type(e).__name__}: {e}"))
        if smtp_client:
            try: smtp_client.close()
            except: pass
        return False

    # -------------------------------------------------------------
    # ШАГ 4: Отправка тестового письма (проверка Relay)
    # -------------------------------------------------------------
    if not to_email:
        print(f"\n{bold('[ШАГ 4/4] Отправка тестового письма:')} " + yellow("пропущена (не указан получатель)."))
        print(green("\nИТОГ: Связь со шлюзом есть, логин и пароль работают!"))
        if smtp_client:
            try: smtp_client.quit()
            except: pass
        return True

    print(f"\n{bold(f'[ШАГ 4/4] Отправка тестового письма на {to_email}...')}")
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Тест SMTP из консоли (RMS Диагностика)"
        msg["From"] = from_email
        msg["To"] = to_email

        body_text = f"Тестовое письмо от {from_email}.\nПодключение к {server}:{port} успешно установлено."
        body_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px; color: #1e293b; background: #f8fafc;">
            <div style="background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; max-width: 500px;">
                <h3 style="color: #4f46e5; margin-top: 0;">RMS &bull; Проверка почтового шлюза</h3>
                <p>Это письмо подтверждает, что почтовый сервер успешно принимает и доставляет сообщения от системы RMS.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 15px 0;" />
                <p style="font-size: 13px; color: #64748b;">
                    <b>Шлюз:</b> {server}:{port}<br>
                    <b>Учетная запись:</b> {user}<br>
                    <b>Отправитель:</b> {from_email}<br>
                    <b>Получатель:</b> {to_email}
                </p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        smtp_client.sendmail(from_email, [to_email], msg.as_string())
        print(green(f"  [OK] Письмо успешно отправлено на {to_email}!"))
        print(green("\nИТОГ: Все проверки пройдены на 100%! Шлюз полностью готов к рассылкам."))
        smtp_client.quit()
        return True
    except smtplib.SMTPRecipientsRefused as e:
        print(red(f"  [ОШИБКА RELAY] Сервер отклонил получателя {to_email}: {e}"))
        print(yellow("  Причина: Учетной записи не разрешено отправлять на этот адрес (политика Relay/ИБ)."))
        print("  Что делать: если это внешний адрес (например, @yandex.ru/@mail.ru), запросите у администраторов шлюза право внешней отправки.")
    except Exception as e:
        print(red(f"  [ОШИБКА ОТПРАВКИ] {type(e).__name__}: {e}"))

    if smtp_client:
        try: smtp_client.close()
        except: pass
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Утилита диагностики корпоративного SMTP шлюза RMS",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--server", help="Адрес SMTP сервера (например: smtp.rt.ru)")
    parser.add_argument("--port", type=int, help="Порт SMTP (обычно: 587, 25 или 465)")
    parser.add_argument("--user", help="Логин технической учетной записи (например: RMS@gd.rt.ru)")
    parser.add_argument("--password", help="Пароль учетной записи")
    parser.add_argument("--to", help="Email получателя для отправки проверочного письма (например: my.email@rt.ru)")
    parser.add_argument("--from-email", help="Email отправителя (From, по умолчанию равен user)")
    parser.add_argument("--insecure", action="store_true", help="Не проверять SSL сертификат (для корпоративных центров сертификации)")
    parser.add_argument("--debug", action="store_true", help="Выводить полный технический протокол диалога с сервером")

    args = parser.parse_args()

    print_banner()

    server = args.server
    if not server:
        server = input("Введите адрес SMTP сервера [по умолчанию: smtp.rt.ru]: ").strip() or "smtp.rt.ru"

    port = args.port
    if not port:
        port_input = input("Введите порт SMTP [по умолчанию: 587]: ").strip() or "587"
        try:
            port = int(port_input)
        except ValueError:
            print(red("Ошибка: порт должен быть числом."))
            sys.exit(1)

    user = args.user
    if not user:
        user = input("Введите логин учетной записи [например: RMS@gd.rt.ru]: ").strip()

    password = args.password
    if not password and user:
        password = getpass.getpass("Введите пароль учетной записи (ввод скрыт): ").strip()

    to_email = args.to
    if not to_email:
        to_email = input("Введите email для тестового письма [Enter чтобы пропустить]: ").strip() or None

    run_checks(
        server=server,
        port=port,
        user=user,
        password=password,
        to_email=to_email,
        from_email=args.from_email,
        insecure=args.insecure,
        debug=args.debug,
    )
    print("\n" + "=" * 68 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем.")
        sys.exit(0)
