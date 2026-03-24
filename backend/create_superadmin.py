\
\
\
\
\
\
\
\
\
\
\
\
\
\
   
import asyncio
import os
import sys
from sqlalchemy import select
from database import AsyncSessionLocal
from models import User, UserRole
from auth import get_password_hash, generate_random_password
import re

def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r'[a-zA-Zа-яА-ЯёЁ]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True

async def create_superadmin():
                                               
    email = os.environ.get("ADMIN_EMAIL")
    full_name = os.environ.get("ADMIN_NAME")
    password = os.environ.get("ADMIN_PASSWORD")

    print("=" * 60)
    print("Создание суперадмина RMS")
    print("=" * 60)

    if not email:
        email = input("Email: ").strip()
    if not full_name:
        full_name = input("Полное имя (Фамилия Имя Отчество): ").strip()
    if not password:
        print("\nВарианты:")
        print("  1. Ввести свой пароль")
        print("  2. Сгенерировать случайный")
        choice = input("Выбор (1/2): ").strip()
        if choice == "2":
            password = generate_random_password(16)
            print(f"\n  Сгенерированный пароль: {password}")
            print("  Сохраните его — он больше не будет показан!\n")
        else:
            import getpass
            password = getpass.getpass("Пароль (мин. 8 символов, буквы + цифры): ")
            confirm = getpass.getpass("Повторите пароль: ")
            if password != confirm:
                print("Ошибка: пароли не совпадают")
                sys.exit(1)

               
    if not email or "@" not in email:
        print("Ошибка: некорректный email")
        sys.exit(1)
    if not full_name:
        print("Ошибка: имя не может быть пустым")
        sys.exit(1)
    if not validate_password(password):
        print("Ошибка: пароль должен быть минимум 8 символов и содержать буквы и цифры")
        sys.exit(1)

    async with AsyncSessionLocal() as db:
                                        
        existing = (await db.execute(
            select(User).where(User.email == email)
        )).scalar_one_or_none()

        if existing:
            print(f"\nПользователь {email} уже существует (роль: {existing.role.value})")
            if existing.role != UserRole.SUPERADMIN:
                upgrade = input("Повысить до суперадмина? (y/n): ").strip().lower()
                if upgrade == "y":
                    existing.role = UserRole.SUPERADMIN
                    existing.is_active = True
                    await db.commit()
                    print(f"✅ {email} повышен до суперадмина")
            sys.exit(0)

        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            full_name=full_name,
            role=UserRole.SUPERADMIN,
            is_active=True,
            is_temporary_password=False,                              
        )
        db.add(user)
        await db.commit()

    print(f"\n✅ Суперадмин создан:")
    print(f"   Email:  {email}")
    print(f"   Имя:    {full_name}")
    print(f"   Роль:   superadmin")
    print(f"\nВойдите в систему по адресу вашего сервера.")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(create_superadmin())