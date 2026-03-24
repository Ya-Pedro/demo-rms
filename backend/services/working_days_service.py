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
\
\
\
   
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import List, Optional

import holidays as _holidays

logger = logging.getLogger(__name__)

                                       
                                                                         
_HOLD_SUBSTRINGS = ("hold", "холд")

def _is_hold_status(status_value: str) -> bool:
    low = (status_value or "").lower()
    return any(s in low for s in _HOLD_SUBSTRINGS)

def _ru_holidays(years: set[int]) -> set[date]:
                                                             
    result: set[date] = set()
    for y in years:
        result.update(_holidays.RU(years=y).keys())
    return result

def _count_workdays(start: date, end: date, ru_hols: set[date]) -> int:
\
\
\
       
    if end < start:
        return 0
    count = 0
    cur = start
    while cur <= end:
        if cur.weekday() < 5 and cur not in ru_hols:
            count += 1
        cur += timedelta(days=1)
    return count

def _extract_hold_intervals(
    history_records: list,
    status_map: dict[int, str],
    open_date: date,
    close_date: date,
) -> list[tuple[date, date]]:
\
\
\
\
\
\
\
\
       
                                      
    sorted_records = sorted(
        [r for r in history_records if r.action_type == "UPDATE"],
        key=lambda r: r.created_at,
    )

    intervals: list[tuple[date, date]] = []
    hold_start: Optional[date] = None

                                         
    for rec in sorted_records:
        try:
            changes: dict = json.loads(rec.changes or "{}")
        except (json.JSONDecodeError, TypeError):
            continue

        status_change = changes.get("Статус вакансии")
        if not status_change:
            continue

        new_val: str = status_change.get("new", "")
        old_val: str = status_change.get("old", "")

        rec_date: date = rec.created_at.date() if hasattr(rec.created_at, "date") else rec.created_at

        if _is_hold_status(new_val) and not _is_hold_status(old_val):
                          
            hold_start = rec_date

        elif hold_start is not None and not _is_hold_status(new_val):
                           
            hold_end = rec_date - timedelta(days=1)                           
            if hold_end >= hold_start:
                intervals.append((
                    max(hold_start, open_date),
                    min(hold_end, close_date),
                ))
            hold_start = None

                                                         
    if hold_start is not None:
        intervals.append((
            max(hold_start, open_date),
            close_date,
        ))

    return intervals

def calculate_net_working_days(
    open_date: date,
    close_date: date,
    history_records: list,
    status_map: dict[int, str],
) -> int:
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
       
    if not open_date or not close_date or close_date < open_date:
        return 0
    if open_date == close_date:
        return 0

                                                      
    years = set(range(open_date.year, close_date.year + 1))
    ru_hols = _ru_holidays(years)

                               
    total_workdays = _count_workdays(open_date, close_date, ru_hols)

                               
    hold_intervals = _extract_hold_intervals(
        history_records, status_map, open_date, close_date
    )

                                                                                   
    hold_workdays = 0
    if hold_intervals:
                                          
        merged: list[tuple[date, date]] = []
        for start, end in sorted(hold_intervals):
            if merged and start <= merged[-1][1] + timedelta(days=1):
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))

        for start, end in merged:
            hold_workdays += _count_workdays(start, end, ru_hols)

    result = max(0, total_workdays - hold_workdays)

    logger.debug(
        "net_workdays open=%s close=%s total=%d hold_intervals=%d hold_days=%d result=%d",
        open_date, close_date, total_workdays, len(hold_intervals), hold_workdays, result,
    )

    return result