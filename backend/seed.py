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
import random
import secrets
import string
from datetime import date, timedelta, datetime
from sqlalchemy import select

from database import engine, AsyncSessionLocal, Base
from models import User, Dictionary, Vacancy, WeeklyReport, UserRole, DictionaryType
from auth import get_password_hash

def generate_password(length: int = 16) -> str:
                                                    
    alphabet = string.ascii_letters + string.digits + "!@#$%"
                                                             
    password = (
        secrets.choice(string.ascii_uppercase) +
        secrets.choice(string.ascii_lowercase) +
        secrets.choice(string.digits) +
        secrets.choice("!@#$%") +
        ''.join(secrets.choice(alphabet) for _ in range(length - 4))
    )
                  
    lst = list(password)
    random.shuffle(lst)
    return ''.join(lst)

DICTIONARIES_DATA = {
    DictionaryType.SPECIALIST_LEVEL: ["Стажер", "Джуниор", "Миддл", "Сеньор", "Тимлид"],
    DictionaryType.VACANCY_STATUS: [
        "Hold", "Открыта", "Закрыта", "Отмена", "Подготовка документов",
        "Выход", "Оффер", "Согласование фин условий", "Проверка СБ"
    ],
    DictionaryType.IT_ROLE: [
        "Бизнес Аналитик", "Системный Аналитик", "Java разработчик",
        "Python разработчик", "QA", "Devops", "Fullstack разработчик",
        "Data Scientist", "Руководитель проекта", "UI/UX дизайнер",
        "React.js разработчик", "C# разработчик", "Golang разработчик",
    ],
    DictionaryType.PROJECT: [
        "CRM", "DataLab", "Wink", "Диджитал", "Кибербезопасность",
        "Эксплуатация", "B2B", "РТКИТ+", "ИИ", "НГБИ"
    ],
    DictionaryType.SOURCE: ["внутренний перевод", "hh", "приведи друга", "рекомендация руководителя"],
    DictionaryType.EMPLOYMENT_TYPE: ["Основное место работы", "Внутреннее совместительство", "Внешнее совместительство"],
    DictionaryType.REPLACEMENT_TYPE: ["Новая", "Замена"],
    DictionaryType.FEASIBILITY: ["ТЭО-2024-00001", "ТЭО-2024-00002", "ТЭО-2025-00001", "1000504233070"],
    DictionaryType.BLOCK: ["Блок Развитие Ит", "Блок Диджитал", "АУП", "Эксплуатация", "РТК ИТ +"],
    DictionaryType.ADMIN_MANAGER: [
        "Иванов Сергей Петрович", "Петров Алексей Сергеевич",
        "Козлов Дмитрий Андреевич", "Смирнова Ольга Николаевна",
    ],
    DictionaryType.TEAM_LEAD: [
        "Волков Андрей Сергеевич", "Зайцева Мария Александровна",
        "Орлов Владимир Петрович", "Белова Ирина Николаевна",
    ],
    DictionaryType.INTERNAL_TRANSFER: ["БОРУП.Перевод из ГК", "Перевод внутри РТК ИТ", "Биржа"],
    DictionaryType.CITY: ["Москва", "Санкт-Петербург", "Казань", "Новосибирск", "Удаленно"],
}

FIRST_NAMES   = ["Александр", "Дмитрий", "Максим", "Сергей", "Андрей", "Анна", "Мария", "Елена", "Ольга", "Наталья"]
LAST_NAMES    = ["Иванов", "Смирнов", "Кузнецов", "Попов", "Васильев", "Петров", "Соколов", "Морозов"]
PATRONYMICS_M = ["Александрович", "Дмитриевич", "Сергеевич", "Андреевич", "Михайлович"]
PATRONYMICS_F = ["Александровна", "Дмитриевна", "Сергеевна", "Андреевна", "Михайловна"]
COMPANIES     = ["Яндекс", "VK", "Сбер", "Тинькофф", "Ozon", "Wildberries", "МТС", "Билайн", "Accenture"]
SALARY_RANGES = [150000, 180000, 200000, 220000, 250000, 300000, 350000, 400000, 500000, None]

def random_name():
    first  = random.choice(FIRST_NAMES)
    last   = random.choice(LAST_NAMES)
    female = first in ["Анна", "Мария", "Елена", "Ольга", "Наталья"]
    patr   = random.choice(PATRONYMICS_F if female else PATRONYMICS_M)
    return f"{last} {first} {patr}"

def _get_week_start(year: int, week: int) -> date:
    jan4  = date(year, 1, 4)
    start = jan4 - timedelta(days=jan4.weekday())
    return start + timedelta(weeks=week - 1)

async def seed_database():
    print("=" * 65)
    print("RMS Database Seeding  [ТОЛЬКО ДЛЯ РАЗРАБОТКИ]")
    print("=" * 65)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Таблицы пересозданы")

                                                        
    generated_passwords: dict[str, str] = {}

    async with AsyncSessionLocal() as db:

                                                                            
        admin_pwd = generate_password()
        generated_passwords["admin@rms-system.ru (SUPERADMIN)"] = admin_pwd
        admin = User(
            email="admin@rms-system.ru",
            hashed_password=get_password_hash(admin_pwd),
            full_name="Супер Администратор",
            role=UserRole.SUPERADMIN,
            is_active=True,
            is_temporary_password=True,                                            
        )
        db.add(admin)

                                                                             
        manager_pwd = generate_password()
        generated_passwords["manager1@rms-system.ru (ADMIN)"] = manager_pwd
        manager = User(
            email="manager1@rms-system.ru",
            hashed_password=get_password_hash(manager_pwd),
            full_name="Смирнов Алексей (Админ)",
            role=UserRole.ADMIN,
            is_active=True,
            is_temporary_password=True,                           
        )
        db.add(manager)
        await db.flush()

                                                                            
        recruiter_names = [
            "Афанасьева Анна", "Быкова Марина", "Бойко Вероника",
            "Вороненко Юлия", "Егоричева Юлия", "Кузьмина Татьяна",
            "Литвиненко Светлана", "Мосина Анастасия", "Русник Елена",
            "Сафонова Екатерина",
        ]
        recruiters = []
        for i, name in enumerate(recruiter_names):
            r_pwd = generate_password()
            email = f"recruiter{i+1}@rms-system.ru"
            generated_passwords[f"{email} (RECRUITER)"] = r_pwd
            r = User(
                email=email,
                hashed_password=get_password_hash(r_pwd),
                full_name=name,
                role=UserRole.RECRUITER,
                is_active=True,
                is_temporary_password=True,                           
            )
            db.add(r)
            recruiters.append(r)
        await db.flush()
        print(f"Пользователи: 1 superadmin, 1 admin, {len(recruiters)} рекрутеров")

                                                                             
        dict_items = {}
        for dt, values in DICTIONARIES_DATA.items():
            dict_items[dt] = []
            for idx, val in enumerate(values):
                item = Dictionary(type=dt, value=val, sort_order=idx, is_active=True)
                db.add(item)
                dict_items[dt].append(item)
        await db.flush()
        print(f"Справочники: {sum(len(v) for v in dict_items.values())} записей")

                                                                             
        vacancies = []
        current_week = date.today().isocalendar()[1]
        current_year = date.today().year

        for i in range(0):
            open_date  = date.today() - timedelta(days=random.randint(10, 120))
            st         = random.choice(dict_items[DictionaryType.VACANCY_STATUS])
            is_closed  = st.value in ["Закрыта", "Оффер", "Выход"]
            close_date = open_date + timedelta(days=random.randint(20, 80)) if is_closed else None

            v = Vacancy(
                vacancy_id=f"VAC-2025-{1000 + i}",
                open_date=open_date,
                quantity=random.randint(1, 3),
                level_id=random.choice(dict_items[DictionaryType.SPECIALIST_LEVEL]).id,
                position_name=random.choice(dict_items[DictionaryType.IT_ROLE]).value,
                status_id=st.id,
                it_role_id=random.choice(dict_items[DictionaryType.IT_ROLE]).id,
                admin_manager_id=random.choice(dict_items[DictionaryType.ADMIN_MANAGER]).id,
                team_lead_id=random.choice(dict_items[DictionaryType.TEAM_LEAD]).id,
                project_id=random.choice(dict_items[DictionaryType.PROJECT]).id,
                city_id=random.choice(dict_items[DictionaryType.CITY]).id,
                source_id=random.choice(dict_items[DictionaryType.SOURCE]).id,
                internal_transfer_id=random.choice(dict_items[DictionaryType.INTERNAL_TRANSFER]).id,
                status_changed_at=date.today() - timedelta(days=random.randint(1, 30)),
                close_date=close_date,
                candidate_name=random_name() if random.random() > 0.3 else None,
                candidate_company=random.choice(COMPANIES) if random.random() > 0.4 else None,
                replacement_type_id=random.choice(dict_items[DictionaryType.REPLACEMENT_TYPE]).id,
                unit_id=f"SHE-{random.randint(1000, 9999)}",
                employment_type_id=random.choice(dict_items[DictionaryType.EMPLOYMENT_TYPE]).id,
                feasibility_id=random.choice(dict_items[DictionaryType.FEASIBILITY]).id,
                iqhr_link=f"https://iqhr.company.ru/request/{random.randint(100000, 999999)}",
                recruiter_id=random.choice(recruiters).id,
                block_id=random.choice(dict_items[DictionaryType.BLOCK]).id,
                hold_days=random.randint(0, 10),
                salary_gross=random.choice(SALARY_RANGES),
                counters_updated_at=datetime.now(),
            )
            db.add(v)
            vacancies.append(v)
        await db.flush()
        print(f"Вакансии: {len(vacancies)} создано")

                                                                             
        report_count = 0
        for v in vacancies:
            for wk_offset in range(random.randint(2, 4)):
                wk = current_week - wk_offset
                yr = current_year
                if wk < 1:
                    wk += 52
                    yr -= 1
                ws = _get_week_start(yr, wk)
                rep = WeeklyReport(
                    vacancy_id=v.id,
                    week_number=wk,
                    year=yr,
                    week_start=ws,
                    report_date=datetime.now() - timedelta(days=wk_offset * 7),
                    resumes_sent=random.randint(1, 8),
                    candidates_agreed=random.randint(0, 4),
                    interviews_planned=random.randint(0, 4),
                    interviews_conducted=random.randint(0, 3),
                    offer_made=random.randint(0, 1),
                )
                db.add(rep)
                report_count += 1

        await db.commit()
        print(f"Еженедельные отчёты: {report_count} создано")

                                         
    print()
    print("=" * 65)
    print("СГЕНЕРИРОВАННЫЕ ПАРОЛИ — сохраните сейчас, они больше не покажутся")
    print("=" * 65)
    for email, pwd in generated_passwords.items():
        print(f"  {email}")
        print(f"    Пароль: {pwd}")
        print()
    print("Все пользователи должны сменить пароль при первом входе.")
    print("=" * 65)

if __name__ == "__main__":
    asyncio.run(seed_database())