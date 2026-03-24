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

from datetime import date, timedelta
from functools import lru_cache
from typing import Optional

try:
    import holidays as _holidays_lib
    _HAS_HOLIDAYS_LIB = True
except ImportError:
    _HAS_HOLIDAYS_LIB = False

                                                                                
                      
                                                                                

def calculate_working_days(
    start: Optional[date],
    end: Optional[date],
    extra_holidays: Optional[set[date]] = None,
    extra_workdays: Optional[set[date]] = None,
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
       
    if not start or not end or end < start:
        return 0

    ru_holidays = _get_ru_holidays(start.year, end.year)

    if extra_holidays:
        ru_holidays = ru_holidays | extra_holidays
    workday_overrides: set[date] = extra_workdays or set()

    count = 0
    cur = start
    while cur <= end:
                                                          
        if cur in workday_overrides:
            count += 1
                                           
        elif cur.weekday() < 5 and cur not in ru_holidays:
            count += 1
        cur += timedelta(days=1)

    return count

                                                                                
                    
                                                                                

@lru_cache(maxsize=10)
def _get_ru_holidays(year_from: int, year_to: int) -> frozenset[date]:
\
\
\
\
\
\
\
       
    if _HAS_HOLIDAYS_LIB:
        all_dates: set[date] = set()
        for year in range(year_from, year_to + 1):
            ru = _holidays_lib.Russia(years=year)
            all_dates.update(ru.keys())
        return frozenset(all_dates)
    else:
        import logging
        logging.getLogger(__name__).warning(
            "Библиотека `holidays` не установлена. "
            "Используется захардкоженный набор праздников 2026 года. "
            "Установите: pip install holidays"
        )
        return _FALLBACK_RU_HOLIDAYS_2026

                                                   
                                                                     
_FALLBACK_RU_HOLIDAYS_2026 = frozenset({
    date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3), date(2026, 1, 4),
    date(2026, 1, 5), date(2026, 1, 6), date(2026, 1, 7), date(2026, 1, 8),
    date(2026, 2, 23),
    date(2026, 3, 8),
    date(2026, 5, 1), date(2026, 5, 9),
    date(2026, 6, 12),
    date(2026, 11, 4),
})