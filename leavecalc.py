"""Pure working-day calculation logic — no Streamlit dependency.

This module is independently importable and unit-testable. The Streamlit layer
in `app.py` is a thin UI shell over these functions.
"""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import dataclass

import holidays

# ---------- Configuration defaults (overridable by callers) ----------
WEEKEND_DAYS_5DAY = (5, 6)        # Sat=5, Sun=6 — standard Indian IT 5-day week
WEEKEND_DAYS_6DAY = (6,)          # Sunday only — 6-day week

STATE_LABELS = {
    "KA": "Karnataka (Bengaluru)",
    "MH": "Maharashtra (Mumbai/Pune)",
    "TN": "Tamil Nadu (Chennai)",
    "TG": "Telangana (Hyderabad)",
    "DL": "Delhi",
    "WB": "West Bengal (Kolkata)",
    "AP": "Andhra Pradesh",
    "KL": "Kerala",
    "GJ": "Gujarat",
    "RJ": "Rajasthan",
    "UP": "Uttar Pradesh",
}


@dataclass
class MonthBreakdown:
    month: int
    year: int
    total_days: int
    weekend_days: list[dt.date]
    public_holidays: list[tuple[dt.date, str]]
    bank_saturdays: list[dt.date]
    leave_days_used: list[dt.date]
    leave_on_nonworking: list[dt.date]
    working_days_periods: list[tuple[dt.date, str]]
    working_days: float


def nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> dt.date | None:
    """Return the n-th `weekday` (0=Mon..6=Sun) of the given month, or None."""
    _, days_in_month = calendar.monthrange(year, month)
    hits = [dt.date(year, month, d) for d in range(1, days_in_month + 1)
            if dt.date(year, month, d).weekday() == weekday]
    return hits[n - 1] if len(hits) >= n else None


def get_bank_saturdays(year: int, month: int) -> list[dt.date]:
    """RBI rule: 2nd and 4th Saturdays are bank-closure holidays."""
    return [d for d in
            (nth_weekday_of_month(year, month, 5, n) for n in (2, 4))
            if d is not None]


def get_public_holidays(year: int, month: int, state: str) -> list[tuple[dt.date, str]]:
    """Return PUBLIC + OPTIONAL gazetted holidays for the state in that month."""
    ind = holidays.country_holidays(
        "IN",
        subdiv=state,
        years=year,
        language="en_US",
    )
    return [(d, name) for d, name in sorted(ind.items()) if d.month == month]


def compute_month(
    month: int,
    year: int,
    state: str,
    leave_dates: list[dt.date],
    weekend_days: tuple[int, ...] = WEEKEND_DAYS_5DAY,
) -> MonthBreakdown:
    """Compute the net working days for a given Indian state's month.

    Non-working day = weekend OR public/gazetted holiday OR RBI 2nd/4th Saturday.
    Leaves on non-working days are ignored (and surfaced for transparency).
    """
    _, days_in_month = calendar.monthrange(year, month)
    all_days = [dt.date(year, month, d) for d in range(1, days_in_month + 1)]

    ph = get_public_holidays(year, month, state)
    ph_dates = {d for d, _ in ph}
    bank_sats = get_bank_saturdays(year, month)
    bank_sat_dates = set(bank_sats)
    weekend_set = {d for d in all_days if d.weekday() in weekend_days}

    non_working = weekend_set | ph_dates | bank_sat_dates

    unique_leaves = sorted(set(leave_dates))
    leave_used = []
    leave_on_nonworking = []
    for l in unique_leaves:
        if l.month != month or l.year != year:
            continue
        if l in non_working:
            leave_on_nonworking.append(l)
        else:
            leave_used.append(l)

    working_periods = [(d, "working") for d in all_days
                       if d not in non_working and d not in set(leave_used)]

    return MonthBreakdown(
        month=month,
        year=year,
        total_days=days_in_month,
        weekend_days=sorted(weekend_set),
        public_holidays=ph,
        bank_saturdays=bank_sats,
        leave_days_used=leave_used,
        leave_on_nonworking=leave_on_nonworking,
        working_days_periods=working_periods,
        working_days=float(len(working_periods)),
    )