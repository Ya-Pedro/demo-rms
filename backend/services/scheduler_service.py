import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Optional
from zoneinfo import ZoneInfo
from sqlalchemy import select

from database import AsyncSessionLocal
from models import User, UserRole
from email_service import send_recruiter_weekly_reminder, is_smtp_configured

logger = logging.getLogger(__name__)

MOSCOW_TZ = ZoneInfo("Europe/Moscow")


def get_next_friday_13_msk() -> datetime:
    now = datetime.now(MOSCOW_TZ)
    # Friday is weekday 4
    days_ahead = (4 - now.weekday()) % 7
    target = now.replace(hour=13, minute=0, second=0, microsecond=0) + timedelta(days=days_ahead)
    if target <= now:
        target += timedelta(days=7)
    return target


async def run_weekly_reminder_job(force: bool = False) -> dict:
    """
    Рассылка еженедельного напоминания о заполнении отчета всем активным рекрутерам.
    """
    logger.info("Запуск задачи рассылки еженедельного напоминания рекрутерам...")
    async with AsyncSessionLocal() as db:
        stmt = select(User).where(
            User.role == UserRole.RECRUITER,
            User.is_active == True,
        )
        recruiters = (await db.execute(stmt)).scalars().all()

    emails = [u.email.strip() for u in recruiters if u.email and "@" in u.email]
    logger.info(f"Найдено активных рекрутеров для рассылки: {len(emails)} ({emails})")

    if not emails:
        logger.warning("Нет активных пользователей в роли 'Рекрутер' с валидными email.")
        return {
            "success": True,
            "recipients_count": 0,
            "recipients": [],
            "message": "Нет активных рекрутеров для отправки",
            "smtp_configured": is_smtp_configured(),
        }

    result = await send_recruiter_weekly_reminder(emails)
    logger.info(f"Результат отправки напоминаний: {result}")

    return {
        "success": True,
        "recipients_count": len(emails),
        "recipients": emails,
        "smtp_configured": is_smtp_configured(),
        "delivery": result,
    }


class WeeklyReminderScheduler:
    """
    Планировщик еженедельного напоминания рекрутерам:
    каждую пятницу в 13:00 по Московскому времени (Europe/Moscow).
    """

    def __init__(self, redis_client=None, check_interval_seconds: int = 30):
        self.redis = redis_client
        self.check_interval = check_interval_seconds
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._last_sent_date: Optional[date] = None

    def start(self):
        if self._task is None or self._task.done():
            self._stop_event.clear()
            self._task = asyncio.create_task(self._loop(), name="WeeklyReminderScheduler")
            logger.info("WeeklyReminderScheduler запущен (целевое время: каждая пятница в 13:00 МСК)")

    def stop(self):
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("WeeklyReminderScheduler остановлен")

    async def _loop(self):
        while not self._stop_event.is_set():
            try:
                await self._check_schedule()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в цикле WeeklyReminderScheduler: {e}", exc_info=True)

            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=self.check_interval)
            except asyncio.TimeoutError:
                pass

    async def _check_schedule(self):
        now_msk = datetime.now(MOSCOW_TZ)

        # Проверяем, пятница ли сегодня (weekday == 4) и 13:00
        if now_msk.weekday() != 4:
            return

        if now_msk.hour != 13 or now_msk.minute != 0:
            return

        today_str = now_msk.strftime("%Y-%m-%d")

        # Проверка блокировки через Redis (для работы в нескольких подах OpenShift)
        if self.redis is not None:
            lock_key = f"rms:scheduler:reminder_sent:{today_str}"
            try:
                # set nx=True вернет True только первому поду
                acquired = await self.redis.set(lock_key, "1", ex=86400, nx=True)
                if not acquired:
                    logger.debug(f"Напоминание за {today_str} уже отправлено другим экземпляром (Redis lock)")
                    return
            except Exception as re:
                logger.warning(f"Ошибка проверки Redis lock: {re}, используем локальную проверку")
                if self._last_sent_date == now_msk.date():
                    return
                self._last_sent_date = now_msk.date()
        else:
            if self._last_sent_date == now_msk.date():
                return
            self._last_sent_date = now_msk.date()

        logger.info(f"Наступило время еженедельной отправки: Пятница 13:00 МСК ({today_str})")
        await run_weekly_reminder_job()

    def get_status(self) -> dict:
        now_msk = datetime.now(MOSCOW_TZ)
        next_run = get_next_friday_13_msk()
        return {
            "current_time_msk": now_msk.isoformat(),
            "next_run_msk": next_run.isoformat(),
            "is_running": self._task is not None and not self._task.done(),
            "smtp_configured": is_smtp_configured(),
            "last_sent_date": self._last_sent_date.isoformat() if self._last_sent_date else None,
        }


# Глобальный экземпляр
scheduler_instance: Optional[WeeklyReminderScheduler] = None


def get_scheduler() -> Optional[WeeklyReminderScheduler]:
    return scheduler_instance
