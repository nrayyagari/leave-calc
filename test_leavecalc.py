"""Unit tests for leavecalc — pure logic verification.

Run:  python -m pytest test_leavecalc.py -q  (or just `python test_leavecalc.py`)
"""

from __future__ import annotations

import datetime as dt
import sys

from leavecalc import (
    WEEKEND_DAYS_5DAY,
    WEEKEND_DAYS_6DAY,
    compute_month,
    get_bank_saturdays,
    get_selectable_leave_dates,
    nth_weekday_of_month,
)


def _check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print(f"  ok: {msg}")


def test_june_2026_baseline():
    print("June 2026 baseline (KA, 5-day):")
    r = compute_month(6, 2026, "KA", [])
    _check(r.total_days == 30, "June has 30 days")
    _check(len(r.weekend_days) == 8, "8 weekend days in June 2026 (4 Sat + 4 Sun)")
    _check(len(r.bank_saturdays) == 2, "2nd & 4th Saturdays = 2")
    _check(len(r.public_holidays) >= 1, ">=1 public holiday in KA June 2026")
    # 30 - 8 weekends - 1 PH (Ashura on fri 2026-06-26) = 21 (bank sats overlap weekends)
    _check(r.working_days == 21, f"working days == 21 (got {r.working_days})")


def test_leave_on_working_day():
    print("Leave on working day (Mon 2026-06-01) reduces WD:")
    r = compute_month(6, 2026, "KA", [dt.date(2026, 6, 1)])
    _check(r.working_days == 20, f"WD == 20 (got {r.working_days})")
    _check(r.leave_on_nonworking == [], "no overlap warning")
    _check(len(r.leave_days_used) == 1, "one leave used")


def test_leave_on_weekend_ignored():
    print("Leave on weekend (Sat 2026-06-06) ignored + warned:")
    r = compute_month(6, 2026, "KA", [dt.date(2026, 6, 6)])
    _check(r.working_days == 21, f"WD still 21 (got {r.working_days})")
    _check(len(r.leave_on_nonworking) == 1, "warned once")
    _check(r.leave_on_nonworking[0] == dt.date(2026, 6, 6), "the right date")
    _check(r.leave_days_used == [], "no leave counted")


def test_leave_on_bank_saturday_ignored():
    print("Leave on 2nd Saturday (2026-06-13) ignored:")
    r = compute_month(6, 2026, "KA", [dt.date(2026, 6, 13)])
    _check(r.working_days == 21, f"WD still 21 (got {r.working_days})")
    _check(len(r.leave_on_nonworking) == 1, "warned")


def test_leave_on_public_holiday_ignored():
    print("Leave on public holiday (2026-06-26) ignored:")
    r = compute_month(6, 2026, "KA", [dt.date(2026, 6, 26)])
    _check(r.working_days == 21, f"WD still 21 (got {r.working_days})")
    _check(len(r.leave_on_nonworking) == 1, "warned")


def test_selectable_leave_dates_exclude_non_working_days():
    print("Selectable leave dates exclude weekends, company holidays, and selected leaves:")
    selectable = get_selectable_leave_dates(6, 2026, "KA", [dt.date(2026, 6, 1)])
    _check(dt.date(2026, 6, 1) not in selectable, "already selected leave is excluded")
    _check(dt.date(2026, 6, 6) not in selectable, "weekend is excluded")
    _check(dt.date(2026, 6, 26) not in selectable, "company holiday is excluded")
    _check(dt.date(2026, 6, 2) in selectable, "working day remains selectable")


def test_multiple_leaves_mixed():
    print("Mixed leaves (working + weekend + PH):")
    leaves = [dt.date(2026, 6, 1),   # Mon — used
              dt.date(2026, 6, 6),   # Sat — ignored
              dt.date(2026, 6, 26),   # PH — ignored
              dt.date(2026, 6, 15)]   # Mon — used
    r = compute_month(6, 2026, "KA", leaves)
    _check(r.working_days == 19, f"WD == 19 (got {r.working_days})")
    _check(len(r.leave_days_used) == 2, "2 leaves counted")
    _check(len(r.leave_on_nonworking) == 2, "2 warned")


def test_6day_week_saturday_is_working():
    print("6-day week: a normal Saturday IS working unless it's 2nd/4th:")
    r = compute_month(6, 2026, "KA", [], weekend_days=WEEKEND_DAYS_6DAY)
    # 30 - 4 Sundays - 1 PH - 2 bank sats = 23 (only Sundays + 2 bank sats non-working)
    _check(r.working_days == 23, f"WD == 23 (got {r.working_days})")


def test_duplicates_and_other_month():
    print("Duplicate leave + out-of-month date handling:")
    leaves = [dt.date(2026, 6, 1), dt.date(2026, 6, 1), dt.date(2026, 5, 31)]
    r = compute_month(6, 2026, "KA", leaves)
    _check(len(r.leave_days_used) == 1, "dedup + out-of-month ignored")
    _check(r.working_days == 20, f"WD == 20 (got {r.working_days})")


def test_bank_saturdays_helper():
    print("Bank Saturdays helper:")
    sats = get_bank_saturdays(2026, 6)
    _check(sats == [dt.date(2026, 6, 13), dt.date(2026, 6, 27)], f"got {sats}")
    feb_sats = get_bank_saturdays(2026, 2)
    _check(feb_sats == [dt.date(2026, 2, 14), dt.date(2026, 2, 28)], f"feb got {feb_sats}")


def test_february_2026_baseline():
    print("February 2026 baseline:")
    r = compute_month(2, 2026, "KA", [])
    _check(r.total_days == 28, "Feb 2026 = 28 days")
    # Feb 2026: 4 Sat (7,14,21,28) + 4 Sun (1,8,15,22) = 8 weekend days.
    # Bank Sats: 14, 28 — subset of weekends. So WD = 28 - 8 - (any public holidays)
    print(f"  -> Feb 2026 KA: PH={len(r.public_holidays)} WD={r.working_days}")


def test_nth_weekday_helper():
    print("nth_weekday_of_month:")
    _check(nth_weekday_of_month(2026, 6, 5, 2) == dt.date(2026, 6, 13), "2nd Sat June 2026")
    _check(nth_weekday_of_month(2026, 1, 0, 1) == dt.date(2026, 1, 5), "1st Mon Jan 2026")
    _check(nth_weekday_of_month(2026, 2, 5, 5) is None, "5th Sat Feb 2026 doesn't exist")


def run_all():
    print("\n=== leavecalc unit tests ===\n")
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            print()
            fn()
    print("\nALL TESTS PASSED\n")


if __name__ == "__main__":
    run_all()
    sys.exit(0)
