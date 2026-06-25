"""Streamlit UI for the Monthly Leave / Overtime Calculator.

All pure logic lives in `leavecalc.py`. This file only renders UI and calls
`compute_month(...)` from user inputs.
"""

from __future__ import annotations

import calendar
import datetime as dt
from pathlib import Path
from urllib.parse import quote

import streamlit as st

from leavecalc import compute_month

REGION_OPTIONS = ["Hyderabad", "Bangalore"]
REGION_CODES = {"Hyderabad": "TG", "Bangalore": "KA"}
SHIFT_OPTIONS = ["13:30 - 22:30 IST", "08:00 - 17:00 IST"]
ICON_PATH = Path(__file__).with_name("assets") / "leavec-jan06.png"

st.set_page_config(
    page_title="LeaveC",
    page_icon=str(ICON_PATH),
    layout="centered",
    initial_sidebar_state="collapsed",
)


def _fmt_date(d: dt.date) -> str:
    """User-facing format: 'Mon 11 May'."""
    return f"{calendar.day_name[d.weekday()][:3]} {d.day} {calendar.month_name[d.month][:3]}"


def _fmt_month_day(d: dt.date) -> str:
    """Compact date format for summaries: '11 May'."""
    return f"{d.day} {calendar.month_name[d.month][:3]}"


def _leave_key(d: dt.date) -> str:
    return f"lv_{d.isoformat()}"


def _month_bounds(year: int, month: int) -> tuple[dt.date, dt.date]:
    month_start = dt.date(year, month, 1)
    month_end = (month_start + dt.timedelta(days=31)).replace(day=1) - dt.timedelta(days=1)
    return month_start, month_end


def _current_month_leaves(month: int, year: int) -> list[dt.date]:
    return sorted(d for d in st.session_state.leaves if d.month == month and d.year == year)


def _build_summary_note(
    month: int,
    year: int,
    shift_time: str,
    result,
    working_days_pre_leave: int,
) -> str:
    public_holiday_details = ", ".join(
        f"{_fmt_month_day(day)}-{name}" for day, name in result.public_holidays
    )
    public_holidays_value = str(len(result.public_holidays))
    if public_holiday_details:
        public_holidays_value = f"{public_holidays_value} ({public_holiday_details})"

    rows = [
        ("Working days (pre-leave)", str(working_days_pre_leave)),
        ("Public holidays", public_holidays_value),
        ("Leaves taken", str(len(result.leave_days_used))),
    ]
    label_width = max(len(label) for label, _ in rows)

    def _row(label: str, value: str) -> str:
        return f"{label.ljust(label_width)} : {value}"

    note_lines = [
        f"Subject: Leave summary - {calendar.month_name[month]} {year}",
        "",
        "Hi,",
        "",
        (
            f"Please find below my leave summary for {calendar.month_name[month]} {year} "
            f"for the {shift_time} shift."
        ),
        "",
    ]
    note_lines.extend(_row(label, value) for label, value in rows)
    note_lines.extend(["", f"Net working days : {int(result.working_days)}"])

    if result.leave_days_used:
        note_lines.extend(["", "Leave dates"])
        for day in result.leave_days_used:
            note_lines.append(f"- {_fmt_date(day)}")

    note_lines.extend(["", "Thanks,", "[Your name]"])
    return "\n".join(note_lines)


if "leaves" not in st.session_state:
    st.session_state.leaves = []
if "show_result" not in st.session_state:
    st.session_state.show_result = False
if "leave_picker_nonce" not in st.session_state:
    st.session_state.leave_picker_nonce = 0

header_cols = st.columns([0.16, 1], gap="small")
with header_cols[0]:
    st.image(str(ICON_PATH), width=50)
with header_cols[1]:
    st.title("LeaveC")
    st.caption("Monthly working-day summary for email updates.")

today = dt.date.today()
last_of_prev = today.replace(day=1) - dt.timedelta(days=1)
default_month, default_year = last_of_prev.month, last_of_prev.year
YEAR_OPTIONS = list(range(default_year - 5, default_year + 6))

with st.container(border=True):
    st.subheader("1 · Period")
    period_cols = st.columns([1.2, 1, 1.35, 1.9], gap="small")

    with period_cols[0]:
        month = st.selectbox(
            "Month",
            options=list(range(1, 13)),
            index=default_month - 1,
            format_func=calendar.month_name.__getitem__,
        )
    with period_cols[1]:
        year = st.selectbox(
            "Year",
            options=YEAR_OPTIONS,
            index=YEAR_OPTIONS.index(default_year),
        )
    with period_cols[2]:
        region = st.selectbox("Region", options=REGION_OPTIONS, index=0)
    with period_cols[3]:
        shift_time = st.selectbox("Shift timing", options=SHIFT_OPTIONS, index=0)

month_num = int(month)
year_num = int(year)
state = REGION_CODES[region]
month_start, month_end = _month_bounds(year_num, month_num)

with st.container(border=True):
    st.subheader("2 · Leave dates")
    picker_cols = st.columns([0.85, 1.4], gap="large")

    with picker_cols[0]:
        new_date = st.date_input(
            "Pick a date",
            value=None,
            min_value=month_start,
            max_value=month_end,
            key=f"leave_picker_{st.session_state.leave_picker_nonce}",
        )
        action_cols = st.columns(2, gap="small")
        with action_cols[0]:
            if st.button("Add date", use_container_width=True):
                if new_date is not None:
                    leave_date = dt.date(year_num, month_num, new_date.day)
                    if leave_date not in st.session_state.leaves:
                        st.session_state.leaves.append(leave_date)
                        st.session_state.leaves.sort()
                    st.session_state[_leave_key(leave_date)] = True
                    st.session_state.leave_picker_nonce += 1
                    st.rerun()
        with action_cols[1]:
            if st.button("Clear all", use_container_width=True):
                for leave_date in st.session_state.leaves:
                    st.session_state.pop(_leave_key(leave_date), None)
                st.session_state.leaves = []
                st.session_state.leave_picker_nonce += 1
                st.rerun()

    with picker_cols[1]:
        current_leaves = _current_month_leaves(month_num, year_num)
        confirmed_leaves: list[dt.date] = []

        st.caption("Selected leave dates")
        if current_leaves:
            for leave_date in current_leaves:
                if st.checkbox(
                    _fmt_date(leave_date),
                    value=True,
                    key=_leave_key(leave_date),
                ):
                    confirmed_leaves.append(leave_date)

            removed_leaves = [leave_date for leave_date in current_leaves if leave_date not in confirmed_leaves]
            if removed_leaves:
                st.session_state.leaves = sorted(
                    leave_date
                    for leave_date in st.session_state.leaves
                    if leave_date not in removed_leaves
                )
        else:
            st.caption(f"No leave dates selected for {calendar.month_name[month_num]} {year_num}.")

result = compute_month(month_num, year_num, state, confirmed_leaves)
working_days_pre_leave = result.total_days - len(result.weekend_days) - len(result.public_holidays)
month_label = f"{calendar.month_name[month_num]} {year_num}"

action_cols = st.columns([1, 1.35, 1])
with action_cols[1]:
    if st.button("Calculate", type="primary", use_container_width=True):
        st.session_state.show_result = True

if st.session_state.show_result:
    with st.container(border=True):
        st.subheader("3 · Result")
        st.caption(f"{month_label} · {region} · {shift_time}")
        st.metric("Net working days", int(result.working_days))
        st.caption("Final count after weekends, public holidays, and counted leave dates.")
        st.divider()

        breakdown_cols = st.columns(2, gap="large")
        with breakdown_cols[0]:
            st.caption("Working days (pre-leave)")
            st.markdown(f"#### {working_days_pre_leave}")
        with breakdown_cols[1]:
            st.caption("Leaves counted")
            st.markdown(f"#### {len(result.leave_days_used)}")

        if result.leave_on_nonworking:
            with st.expander(
                f"{len(result.leave_on_nonworking)} leave date(s) fall on non-working days and are not counted"
            ):
                holiday_dates = {day for day, _ in result.public_holidays}
                for leave_date in result.leave_on_nonworking:
                    tags = []
                    if leave_date.weekday() in (5, 6):
                        tags.append(calendar.day_name[leave_date.weekday()][:3])
                    if leave_date in holiday_dates:
                        tags.append("holiday")
                    st.write(f"- {_fmt_date(leave_date)} · {' / '.join(tags)}")

    note_text = _build_summary_note(
        month=month_num,
        year=year_num,
        shift_time=shift_time,
        result=result,
        working_days_pre_leave=working_days_pre_leave,
    )
    mailto_subject = quote(f"Leave summary - {month_label}")
    mailto_body = quote(note_text)
    outlook_draft_url = f"mailto:?subject={mailto_subject}&body={mailto_body}"

    with st.container(border=True):
        st.subheader("4 · Copy text")
        summary_actions = st.columns([1.15, 1.85], gap="small")
        with summary_actions[0]:
            st.link_button("Open in Outlook draft", outlook_draft_url, use_container_width=True)
        with summary_actions[1]:
            st.caption(
                "Use the copy icon in the top-right of the copy text box. "
                "The Outlook button opens a prefilled draft in your default mail app."
            )
        st.code(note_text)
    
    with st.container(border=True):
        st.subheader("5 · Reference")
        reference_stats = st.columns(2, gap="small")
        reference_stats[0].metric(f"Total calendar days in {month_label}", result.total_days)
        reference_stats[1].metric("Weekends", len(result.weekend_days))
