\
\
   
from __future__ import annotations

import json
import logging
import traceback
from datetime import date, datetime, timezone
from typing import Optional, List, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import VacancyHistory, Vacancy, User

logger = logging.getLogger(__name__)

                                                                                

FIELD_LABELS: dict[str, str] = {
    "vacancy_id":           "ID вакансии",
    "open_date":            "Дата открытия",
    "quantity":             "Количество вакансий",
    "position_name":        "Должность",
    "hold_days":            "Дней в холде",
    "salary_gross":         "Зарплата (Gross)",
    "candidate_name":       "ФИО кандидата",
    "candidate_company":    "Компания кандидата",
    "ex_employee_name":     "ФИО бывшего сотрудника",
    "unit_id":              "ID ШЕ",
    "iqhr_link":            "Ссылка IQHR",
    "close_date":           "Дата закрытия",
    "status_changed_at":    "Дата изменения статуса",
    "city_text":            "Город (текст)",
    "status_id":            "Статус вакансии",
    "level_id":             "Уровень специалиста",
    "it_role_id":           "ИТ роль",
    "admin_manager_id":     "Административный руководитель",
    "team_lead_id":         "Тимлид",
    "project_id":           "Проект",
    "city_id":              "Город",
    "source_id":            "Источник найма",
    "internal_transfer_id": "Внутренний перевод",
    "replacement_type_id":  "Новая/Замена",
    "employment_type_id":   "Вид занятости",
    "feasibility_id":       "ТЭО проекта",
    "block_id":             "Блок",
    "recruiter_id":         "Рекрутер",
}

SKIP_FIELDS = {
    "id", "created_at", "updated_at", "counters_updated_at",
    "resumes_sent_cnt", "candidates_agreed_cnt",
    "interviews_planned_cnt", "interviews_conducted_cnt",
}

FK_RELATION_MAP: dict[str, tuple[str, str]] = {
    "status_id":            ("status",            "value"),
    "level_id":             ("level",             "value"),
    "it_role_id":           ("it_role",           "value"),
    "admin_manager_id":     ("admin_manager",     "value"),
    "team_lead_id":         ("team_lead",         "value"),
    "project_id":           ("project",           "value"),
    "city_id":              ("city",              "value"),
    "source_id":            ("source",            "value"),
    "internal_transfer_id": ("internal_transfer", "value"),
    "replacement_type_id":  ("replacement_type",  "value"),
    "employment_type_id":   ("employment_type",   "value"),
    "feasibility_id":       ("feasibility",       "value"),
    "block_id":             ("block",             "value"),
    "recruiter_id":         ("recruiter",         "full_name"),
}

REPORT_FIELD_LABELS = {
    "resumes_sent":         "Передано заказчику",
    "candidates_agreed":    "Резюме одобрено",
    "interviews_planned":   "Собеседования план",
    "interviews_conducted": "Собеседования факт",
    "offer_made":           "Оффер сделан",
}

ROLE_LABELS = {
    "superadmin": "суперадмин",
    "admin":      "администратор",
    "recruiter":  "рекрутер",
}

                                                                                

def _serialize_value(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Да" if value else "Нет"
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    return str(value)

def _user_label(user: User) -> str:
                                              
    role_str = ROLE_LABELS.get(str(user.role.value if hasattr(user.role, 'value') else user.role), "")
    name = user.full_name or user.email or f"ID {user.id}"
    return f"{name} ({role_str})" if role_str else name

def _resolve_fk(vacancy: Vacancy, field: str) -> Optional[str]:
    if field not in FK_RELATION_MAP:
        return None
    rel_attr, disp_attr = FK_RELATION_MAP[field]
    try:
        obj = getattr(vacancy, rel_attr, None)
        if obj is None:
            return None
        return str(getattr(obj, disp_attr, None) or "")
    except Exception:
        return None

def _snapshot_vacancy(vacancy: Vacancy) -> dict:
    snap = {}
    for field in FIELD_LABELS:
        if field in SKIP_FIELDS:
            continue
        text = _resolve_fk(vacancy, field)
        if text is not None and text:
            snap[field] = text
        else:
            raw = getattr(vacancy, field, None)
            snap[field] = _serialize_value(raw)
    return snap

def _build_diff(before: dict, after: dict) -> dict:
    diff = {}
    for field in set(before) | set(after):
        old_v = before.get(field, "—")
        new_v = after.get(field, "—")
        if old_v != new_v:
            label = FIELD_LABELS.get(field, field)
            diff[label] = {"old": old_v, "new": new_v}
    return diff

                                                                                

class VacancyHistoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def snapshot(self, vacancy: Vacancy) -> dict:
        return _snapshot_vacancy(vacancy)

    def _add(self, entry: VacancyHistory) -> None:
        self.db.add(entry)

                                                                                

    async def record_create(self, vacancy: Vacancy, user: User) -> None:
        changes = {}
        for field, label in FIELD_LABELS.items():
            if field in SKIP_FIELDS:
                continue
            text = _resolve_fk(vacancy, field)
            raw = text if (text is not None and text) else getattr(vacancy, field, None)
            if raw is not None and raw not in ("—", "", 0):
                val = text if (text is not None and text) else _serialize_value(raw)
                if val and val != "—":
                    changes[label] = {"old": "—", "new": val}

        self._add(VacancyHistory(
            vacancy_id=vacancy.id,
            user_id=user.id,
            action_type="CREATE",
            changes=json.dumps(changes, ensure_ascii=False),
            vacancy_snapshot=vacancy.position_name,
        ))
        logger.debug("history CREATE vacancy_id=%s user=%s fields=%d",
                     vacancy.id, user.id, len(changes))

                                                                                

    async def record_update(
        self,
        before_snap: dict,
        vacancy_after: Vacancy,
        user: User,
    ) -> None:
        after_snap = _snapshot_vacancy(vacancy_after)
        diff = _build_diff(before_snap, after_snap)

        logger.debug(
            "history UPDATE vacancy_id=%s user=%s diff_fields=%s",
            vacancy_after.id, user.id, list(diff.keys())
        )

        if not diff:
            logger.debug("history UPDATE: no diff, skipping")
            return

        self._add(VacancyHistory(
            vacancy_id=vacancy_after.id,
            user_id=user.id,
            action_type="UPDATE",
            changes=json.dumps(diff, ensure_ascii=False),
            vacancy_snapshot=vacancy_after.position_name,
        ))

                                                                                

    async def record_delete(self, vacancy: Vacancy, user: User) -> None:
        changes = {"Вакансия": {"old": vacancy.position_name, "new": "—"}}
        self._add(VacancyHistory(
            vacancy_id=None,
            user_id=user.id,
            action_type="DELETE",
            changes=json.dumps(changes, ensure_ascii=False),
            vacancy_snapshot=f"{vacancy.position_name} (ID: {vacancy.vacancy_id or vacancy.id})",
        ))

                                                                                

    async def record_delegation_created(
        self,
        vacancy_id: int,
        vacancy_name: str,
        delegated_to_name: str,
        start_date: date,
        end_date: date,
        user: User,
    ) -> None:
        changes = {
            "Временный рекрутер": {"old": "—", "new": delegated_to_name},
            "Период": {
                "old": "—",
                "new": f"{start_date.strftime('%d.%m.%Y')} – {end_date.strftime('%d.%m.%Y')}",
            },
        }
        self._add(VacancyHistory(
            vacancy_id=vacancy_id,
            user_id=user.id,
            action_type="DELEGATE",
            changes=json.dumps(changes, ensure_ascii=False),
            vacancy_snapshot=vacancy_name,
        ))

    async def record_delegation_revoked(
        self,
        vacancy_id: int,
        vacancy_name: str,
        delegated_to_name: str,
        user: User,
        reason: str = "Отозвано",
    ) -> None:
        changes = {
            "Временный рекрутер": {"old": delegated_to_name, "new": "—"},
            "Причина":            {"old": "—", "new": reason},
        }
        self._add(VacancyHistory(
            vacancy_id=vacancy_id,
            user_id=user.id,
            action_type="UNDELEGATE",
            changes=json.dumps(changes, ensure_ascii=False),
            vacancy_snapshot=vacancy_name,
        ))

                                                                                

    async def record_report_created(
        self,
        vacancy_id: int,
        vacancy_name: str,
        week_number: int,
        year: int,
        metrics: dict,
        user: User,
    ) -> None:
        changes: dict = {}
        for field, label in REPORT_FIELD_LABELS.items():
            v = metrics.get(field, 0) or 0
            if v:
                changes[label] = {"old": "—", "new": str(v)}

        if not changes:
            changes["Неделя"] = {"old": "—", "new": f"Неделя {week_number}, {year}"}

        self._add(VacancyHistory(
            vacancy_id=vacancy_id,
            user_id=user.id,
            action_type="REPORT",
            changes=json.dumps(changes, ensure_ascii=False),
            vacancy_snapshot=vacancy_name,
        ))
        logger.debug("history REPORT vacancy_id=%s week=%s/%s", vacancy_id, week_number, year)

    async def record_report_updated(
        self,
        vacancy_id: int,
        vacancy_name: str,
        week_number: int,
        year: int,
        old_metrics: dict,
        new_metrics: dict,
        user: User,
    ) -> None:
        changes: dict = {}
        for field, label in REPORT_FIELD_LABELS.items():
            old_v = old_metrics.get(field, 0) or 0
            new_v = new_metrics.get(field, 0) or 0
            if old_v != new_v:
                changes[label] = {"old": str(old_v), "new": str(new_v)}

        if not changes:
            return

        self._add(VacancyHistory(
            vacancy_id=vacancy_id,
            user_id=user.id,
            action_type="REPORT",
            changes=json.dumps(changes, ensure_ascii=False),
            vacancy_snapshot=vacancy_name,
        ))

                                                                                

    async def get_history(
        self,
        vacancy_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[VacancyHistory]:
        q = (
            select(VacancyHistory)
            .options(selectinload(VacancyHistory.user))
            .where(VacancyHistory.vacancy_id == vacancy_id)
        )
        if start_date:
            q = q.where(VacancyHistory.created_at >= datetime(
                start_date.year, start_date.month, start_date.day,
                0, 0, 0, tzinfo=timezone.utc,
            ))
        if end_date:
            q = q.where(VacancyHistory.created_at <= datetime(
                end_date.year, end_date.month, end_date.day,
                23, 59, 59, tzinfo=timezone.utc,
            ))
        q = q.order_by(VacancyHistory.created_at.desc())
        result = await self.db.execute(q)
        return result.scalars().all()