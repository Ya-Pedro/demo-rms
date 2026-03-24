import asyncio
import os
import logging
import calendar
from datetime import date, datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select, func, not_
from sqlalchemy.orm import aliased

from database import AsyncSessionLocal
from models import Vacancy, Dictionary, DictionaryType

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не найден BOT_TOKEN в переменных окружения!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

                                 
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Актуальные данные")]],
    resize_keyboard=True,
    is_persistent=True,
    input_field_placeholder="Выберите действие..."
)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот системы RMS.\nНажми кнопку ниже, чтобы получить выгрузку.",
        reply_markup=main_keyboard
    )

async def get_stats_by_filter(session, status_filter=None, current_month=False):
                                                                      
    block_dict = aliased(Dictionary)
    status_dict = aliased(Dictionary)

                                       
    stmt = (
        select(block_dict.value, func.count(Vacancy.id))
        .select_from(Vacancy)
        .join(block_dict, Vacancy.block_id == block_dict.id)
        .where(block_dict.type == DictionaryType.BLOCK)
    )

    if status_filter == "opened":
                                                 
        stmt = stmt.join(status_dict, Vacancy.status_id == status_dict.id)
        stmt = stmt.where(
            not_(status_dict.value.in_(["Закрыта", "Отмена", "Hold"]))
        )
    elif status_filter == "closed":
                                                    
        stmt = stmt.join(status_dict, Vacancy.status_id == status_dict.id)
        stmt = stmt.where(status_dict.value == "Закрыта")
        
        if current_month:
            today = date.today()
                                          
            start_of_month = today.replace(day=1)
                                             
            _, last_day = calendar.monthrange(today.year, today.month)
            end_of_month = today.replace(day=last_day)
            
                                        
            stmt = stmt.where(Vacancy.close_date >= start_of_month)
            stmt = stmt.where(Vacancy.close_date <= end_of_month)

                                                          
    stmt = stmt.group_by(block_dict.value).order_by(func.count(Vacancy.id).desc())
    res = await session.execute(stmt)
    return res.all()

@dp.message(F.text == "Актуальные данные")
async def send_actual_data(message: types.Message):
    wait_msg = await message.answer("⏳ Собираю актуальные данные...")
    
    try:
        async with AsyncSessionLocal() as session:
                               
            total_res = await session.execute(select(func.count(Vacancy.id)))
            total_vacancies = total_res.scalar() or 0

                         
            opened_data = await get_stats_by_filter(session, status_filter="opened")

                                          
            closed_data = await get_stats_by_filter(session, status_filter="closed", current_month=True)

                                             
        current_time_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

                                           
        text = [f"📅 <b>Данные на: {current_time_str}</b>\n"]
        text.append(f"<b>Всего вакансий: {total_vacancies}</b>\n")
        
        text.append("<b>Открыто</b>")
        text.append("<i>(Все кроме Закрыта, Отмена, Hold)</i>")
        if opened_data:
            for name, count in opened_data:
                text.append(f"• {name}: {count}")
        else:
            text.append("• Нет данных")

        text.append("\n<b>Закрыто за текущий месяц</b>")
        if closed_data:
            for name, count in closed_data:
                text.append(f"• {name}: {count}")
        else:
            text.append("• Нет данных")

        await wait_msg.delete()
        await message.answer("\n".join(text), parse_mode="HTML")
        
    except Exception as e:
        logging.error(f"Ошибка БД: {e}")
        await wait_msg.delete()
        await message.answer("❌ Ошибка при получении данных.")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())