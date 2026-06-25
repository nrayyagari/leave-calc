"""Company holiday definitions.

Replace these placeholder holidays with the official company holiday list as it
becomes available. The structure is keyed by year and supports both default
holidays and state-specific additions or overrides.
"""

from __future__ import annotations

import datetime as dt

HolidayEntry = tuple[dt.date, str]


COMPANY_HOLIDAYS: dict[int, dict[str, list[HolidayEntry]]] = {
    2025: {
        "default": [
            (dt.date(2025, 1, 1), "New Year's Day"),
            (dt.date(2025, 5, 1), "Labour Day"),
            (dt.date(2025, 8, 15), "Independence Day"),
            (dt.date(2025, 10, 2), "Gandhi Jayanti"),
            (dt.date(2025, 12, 25), "Christmas Day"),
        ],
    },
    2026: {
        "default": [
            (dt.date(2026, 1, 1), "New Year's Day"),
            (dt.date(2026, 5, 1), "Labour Day"),
            (dt.date(2026, 8, 15), "Independence Day"),
            (dt.date(2026, 10, 2), "Gandhi Jayanti"),
            (dt.date(2026, 12, 25), "Christmas Day"),
        ],
        "KA": [
            (dt.date(2026, 6, 26), "Eid al-Adha"),
        ],
        "TG": [
            (dt.date(2026, 6, 26), "Eid al-Adha"),
        ],
    },
}


def get_company_holidays(year: int, state: str) -> list[HolidayEntry]:
    """Return the merged company holiday list for a year and state."""
    year_holidays = COMPANY_HOLIDAYS.get(year, {})
    merged: dict[dt.date, str] = {}

    for holiday_date, name in year_holidays.get("default", []):
        merged[holiday_date] = name
    for holiday_date, name in year_holidays.get(state, []):
        merged[holiday_date] = name

    return sorted(merged.items())
