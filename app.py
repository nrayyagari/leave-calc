"""Streamlit UI for the Monthly Leave / Overtime Calculator.

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

st.set_page_config(page_title="Leave Calculator", page_icon="📅", layout="centered")

# ---------- Helpers ----------
def _fmt_date(d: dt.date) -> str:
    return f"{d.isoformat()} · {calendar.day_name[d.weekday()][:3]} {d.day} {calendar.month_name[d.month][:3]}"


# ---------- Initialize session state for accumulated leaves ----------
if "leaves" not in st.session_state:
    st.session_state.leaves = []  # list[dt.date]

# ---------- Header ----------
st.title("📅 Leave Calculator")
st.caption("Indian IT · public holidays · 5-day week (Sat+Sun off)")

today = dt.date.today()
last_of_prev = today.replace(day=1) - dt.timedelta(days=1)
default_month, default_year = last_of_prev.month, last_of_prev.year

# ---------- Step 1: confirm period ----------
st.subheader("1 · Confirm period")
col_m, col_y, col_s = st.columns([2, 2, 3])
with col_m:
    month = st.selectbox(
        "Month",
        options=list(range(1, 13)),
        index=default_month - 1,
        format_func=calendar.month_name.__getitem__,
        label_visibility="collapsed",
    )
with col_y:
    year = st.number_input(
        "Year",
        min_value=2020,
        max_value=2100,
        value=default_year,
        step=1,
        label_visibility="collapsed",
    )
with col_s:
    state = st.selectbox(
        "State",
        options=list(STATE_LABELS.keys()),
        index=0,
        format_func=STATE_LABELS.__getitem__,
        label_visibility="collapsed",
    )

shift_time = st.text_input(
    "Shift timing (IST)",
    value="13:30 – 22:30 IST",
    help="Editable. Included verbatim in the summary to your manager.",
)

month_start = dt.date(int(year), int(month), 1)
month_end = (month_start.replace(day=1) + dt.timedelta(days=31)).replace(day=1) - dt.timedelta(days=1)

st.info(
    f"**{calendar.month_name[month]} {year}**  ·  "
    f"{month_start.isoformat()} → {month_end.isoformat()}  ·  "
    f"{STATE_LABELS[state]}"
)

# ---------- Step 2: pick leave dates (accumulating) ----------
st.subheader("2 · Pick leave dates")

# Sub-UI: pick one date at a time, add to session_state list
picker_cols = st.columns([3, 1, 1])
with picker_cols[0]:
    new_date = st.date_input(
        "Add a leave date",
        value=None,
        min_value=month_start,
        max_value=month_end,
        label_visibility="collapsed",
        help="Pick a date and click 'Add'. Repeat for each leave date.",
    )
with picker_cols[1]:
    if st.button("＋ Add", use_container_width=True):
        if new_date is not None:
            d = dt.date(int(year), int(month), new_date.day)
            if d not in st.session_state.leaves:
                st.session_state.leaves.append(d)
                st.session_state.leaves.sort()
            st.rerun()
with picker_cols[2]:
    if st.button("✕ Clear all", use_container_width=True):
        st.session_state.leaves = []
        st.rerun()

# Show currently accumulated leaves as tickable checkboxes (untick to remove)
confirmed_leaves: list[dt.date] = []
if st.session_state.leaves:
    st.write("**Selected leave dates**  ·  _untick to remove_")
    cols_per_row = 3
    # Render as a grid of checkboxes using st.columns
    for idx, d in enumerate(st.session_state.leaves):
        if d.month != int(month) or d.year != int(year):
            continue
        if st.checkbox(_fmt_date(d), value=True, key=f"lv_{d.isoformat()}"):
            confirmed_leaves.append(d)
else:
    st.caption("_No leave dates selected yet._")

# ---------- Step 3: Calculate ----------
st.write("")
if st.button("Calculate", type="primary", use_container_width=True):
    result = compute_month(int(month), int(year), state, confirmed_leaves)

    # ----- Result -----
    st.write("---")
    st.subheader("3 · Result")

    # Top row — the two numbers that matter, large and aligned
    r1c1, r1c2 = st.columns(2)
    r1c1.metric(
        label=f"Net working days · {calendar.month_name[month]} {year}",
        value=f"{result.working_days:.0f}",
    )
    r1c2.metric(
        label="Leaves counted",
        value=f"{len(result.leave_days_used)}",
    )

    # Compact breakdown — 3 numbers, aligned
    r2c1, r2c2, r2c3 = st.columns(3)
    r2c1.metric("Total days", result.total_days)
    r2c2.metric("Public holidays", len(result.public_holidays))
    r2c3.metric("Leaves taken", len(result.leave_days_used))

    # Warnings
    if result.leave_on_nonworking:
        with st.expander(f"⚠️ {len(result.leave_on_nonworking)} leave(s) fell on weekends/holidays — not deducted"):
            ph_dates = {pd for pd, _ in result.public_holidays}
            for d in result.leave_on_nonworking:
                tags = []
                if d.weekday() in (5, 6):
                    tags.append(calendar.day_name[d.weekday()])
                if d in ph_dates:
                    tags.append("public holiday")
                st.write(f"- {_fmt_date(d)}  ·  _{' / '.join(tags)}_")

    # Optional detail — collapsed by default
    with st.expander("Public holidays this month"):
        if result.public_holidays:
            for d, n in result.public_holidays:
                st.write(f"- `{d.isoformat()}` · {n}")
        else:
            st.write("_none_")

    with st.expander("Leaves counted"):
        if result.leave_days_used:
            for d in result.leave_days_used:
                st.write(f"- {_fmt_date(d)}")
        else:
            st.write("_none — no working-day leaves._")

    # ---------- Summary (forwardable note) ----------
    st.write("---")
    st.subheader("4 · Summary")
    note_lines = [
        f"Subject: Leave summary — {calendar.month_name[month]} {year}",
        "",
        "Hi [Manager],",
        "",
        f"Please find below my leave summary for {calendar.month_name[month]} {year}:",
        "",
        f"  Shift timing                 : {shift_time}",
        f"  Total calendar days          : {result.total_days}",
        f"  Public / gazetted holidays    : {len(result.public_holidays)}",
        f"  Leaves taken                  : {len(result.leave_days_used)}",
        "",
        f"  Net working days              = {result.working_days:.0f}",
        "",
    ]
    if result.public_holidays:
        note_lines.append("Public holidays:")
        for d, n in result.public_holidays:
            note_lines.append(f"  - {d.isoformat()} · {n}")
        note_lines.append("")
    if result.leave_days_used:
        note_lines.append("Leave dates:")
        for d in result.leave_days_used:
            note_lines.append(f"  - {d.isoformat()} ({calendar.day_name[d.weekday()]})")
        note_lines.append("")
    note_lines += ["Thanks,", "[Your name]"]
    note_text = "\n".join(note_lines)

    # st.code renders with a built-in one-click copy icon (top-right) — no extra libs
    st.code(note_text, language="text")
    st.download_button(
        label="⬇️ Download as .txt",
        data=note_text,
        file_name=f"leave_summary_{int(year)}_{int(month):02d}.txt",
        mime="text/plain",
    )

st.write("")
st.caption("_Holiday source: `holidays` lib (India PUBLIC+OPTIONAL) + RBI 2nd/4th Saturday rule_")