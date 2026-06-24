"""Streamlit UI for the Monthly Overtime / Working-Day Calculator.

All pure logic lives in `leavecalc.py`. This file only renders UI and calls
`compute_month(...)` from user inputs.
"""

from __future__ import annotations

import calendar
import datetime as dt

import streamlit as st

from leavecalc import (
    STATE_LABELS,
    compute_month,
)

st.set_page_config(page_title="Monthly Overtime Calc", page_icon=":bank:", layout="centered")

st.title(":bank: Monthly Overtime — Working-Day Calculator")
st.caption(
    "Indian bank-holiday aware (gazetted holidays + RBI 2nd/4th Saturday rule) · "
    "5-day week (Sat+Sun) · Karnataka default"
)

# --- Step 1: confirm month & year ---
st.subheader("Step 1 — Confirm the month you're reporting for")
today = dt.date.today()
last_of_prev = today.replace(day=1) - dt.timedelta(days=1)
default_month, default_year = last_of_prev.month, last_of_prev.year

col_m, col_y, col_s = st.columns([2, 2, 3])
with col_m:
    month = st.selectbox(
        "Month",
        options=list(range(1, 13)),
        index=default_month - 1,
        format_func=calendar.month_name.__getitem__,
    )
with col_y:
    year = st.number_input("Year", min_value=2020, max_value=2100, value=default_year, step=1)
with col_s:
    state = st.selectbox("State", options=list(STATE_LABELS.keys()),
                         index=0, format_func=STATE_LABELS.__getitem__)

month_start = dt.date(int(year), int(month), 1)
month_end = (month_start.replace(day=1) + dt.timedelta(days=31)).replace(day=1) - dt.timedelta(days=1)

st.info(
    f"Reporting period: **{calendar.month_name[month]} {year}** "
    f"({month_start.isoformat()} → {month_end.isoformat()}) — {STATE_LABELS[state]}"
)

# --- Step 2: leave entry ---
st.subheader("Step 2 — Enter leave dates taken this month")
leaves = st.date_input(
    "Select all leave dates (multi-select)",
    value=[],
    min_value=month_start,
    max_value=month_end,
    help="Pick each date you took leave. Dates outside this month or on weekends/holidays are ignored with a warning.",
)

# --- Compute ---
if st.button("Compute working days", type="primary"):
    result = compute_month(int(month), int(year), state, list(leaves))

    st.subheader("Result")
    st.metric(
        label=f"Working days in {calendar.month_name[month]} {year}",
        value=f"{result.working_days:.0f}",
        help="After subtracting weekends, public holidays, RBI 2nd/4th Saturdays, and your leaves.",
    )

    st.write("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total days", result.total_days)
    c2.metric("Weekends (Sat+Sun)", len(result.weekend_days))
    c3.metric("Public holidays", len(result.public_holidays))
    c4.metric("Bank Saturdays (2nd/4th)", len(result.bank_saturdays))

    with st.expander("Public / gazetted holidays this month"):
        if result.public_holidays:
            for d, n in result.public_holidays:
                st.write(f"- `{d.isoformat()}` — {n}")
        else:
            st.write("_none_")

    with st.expander("Bank-closure Saturdays (RBI 2nd/4th)"):
        if result.bank_saturdays:
            for d in result.bank_saturdays:
                st.write(f"- `{d.isoformat()}` — {calendar.day_name[d.weekday()]}")
        else:
            st.write("_none this month_")

    with st.expander("Leaves you entered"):
        if result.leave_days_used:
            st.write("**Counted leaves (deducted from working days):**")
            for d in result.leave_days_used:
                st.write(f"- `{d.isoformat()}` — {calendar.day_name[d.weekday()]}")
        else:
            st.write("_No working-day leaves entered._")

        if result.leave_on_nonworking:
            st.warning(
                "These leave dates fell on weekends or holidays — "
                "**not deducted** (no loss of a working day):"
            )
            ph_dates = {pd for pd, _ in result.public_holidays}
            for d in result.leave_on_nonworking:
                labels = []
                if d.weekday() in (5, 6):
                    labels.append(calendar.day_name[d.weekday()])
                if d in ph_dates:
                    labels.append("public holiday")
                if d in set(result.bank_saturdays):
                    labels.append("bank Saturday")
                st.write(f"- `{d.isoformat()}` — {' / '.join(labels)}")

    # --- Forwardable note ---
    st.write("---")
    st.subheader("Note for your manager (copy or download)")
    note_lines = [
        f"Subject: Monthly overtime note — {calendar.month_name[month]} {year}",
        "",
        "Hi [Manager],",
        "",
        f"Please find below my working-day summary for {calendar.month_name[month]} {year}:",
        f"- Total calendar days: {result.total_days}",
        f"- Weekends (Sat+Sun): {len(result.weekend_days)}",
        f"- Public / gazetted holidays: {len(result.public_holidays)}",
        f"- Bank-closure Saturdays (2nd/4th): {len(result.bank_saturdays)}",
        f"- Leaves taken (working days): {len(result.leave_days_used)}",
        "",
        f"Net working days = {result.working_days:.0f}",
        "",
    ]
    if result.leave_days_used:
        note_lines.append("Leave dates:")
        for d in result.leave_days_used:
            note_lines.append(f"  - {d.isoformat()} ({calendar.day_name[d.weekday()]})")
        note_lines.append("")
    note_lines += ["Thanks,", "[Your name]"]
    note_text = "\n".join(note_lines)

    st.text_area("Copy-paste this note", value=note_text, height=300)
    st.download_button(
        label="Download note (txt)",
        data=note_text,
        file_name=f"overtime_note_{int(year)}_{int(month):02d}.txt",
        mime="text/plain",
    )

st.write("---")
st.caption(
    "Holiday source: `holidays` lib (India PUBLIC+OPTIONAL) + RBI 2nd/4th Saturday rule · "
    "5-day week default"
)