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

# ---------- Polite helpers ----------
def _fmt_date(d: dt.date) -> str:
    return f"{d.isoformat()} · {calendar.day_name[d.weekday()][:3]} {d.day} {calendar.month_name[d.month][:3]}"


def _normalize_dates(value) -> list[dt.date]:
    """st.date_input returns a single date or a list-tuple; normalize to list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return sorted(set(value))
    return [value]


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

# Shift timing (free text, defaults to 13:30–22:30 IST)
shift_time = st.text_input(
    "Shift timing (IST)",
    value="13:30 – 22:30 IST",
    help="Editable. Included verbatim in the note to your manager.",
)

month_start = dt.date(int(year), int(month), 1)
month_end = (month_start.replace(day=1) + dt.timedelta(days=31)).replace(day=1) - dt.timedelta(days=1)

st.info(
    f"**{calendar.month_name[month]} {year}**  ·  "
    f"{month_start.isoformat()} → {month_end.isoformat()}  ·  "
    f"{STATE_LABELS[state]}"
)

# ---------- Step 2: pick leave dates ----------
st.subheader("2 · Pick leave dates")
picked_raw = st.date_input(
    "Pick dates (click each one; pick multiple)",
    value=[],
    min_value=month_start,
    max_value=month_end,
    help="Click each date you took leave. Below they appear as tickable options — untick any you don't want counted.",
    label_visibility="collapsed",
)
picked = _normalize_dates(picked_raw)

# ---------- Step 2b: tickable confirm ----------
confirmed_leaves: list[dt.date] = []
if picked:
    st.write("**Confirm leaves** — untick to exclude:")
    for d in picked:
        label = _fmt_date(d)
        if st.checkbox(label, value=True, key=f"lv_{d.isoformat()}"):
            confirmed_leaves.append(d)
else:
    st.caption("_No leave dates picked yet._")

# ---------- Compute ----------
st.write("")
if st.button("Calculate working days", type="primary", use_container_width=True):
    result = compute_month(int(month), int(year), state, confirmed_leaves)

    # ----- Result banner -----
    st.write("---")
    st.subheader("3 · Result")
    big1, big2 = st.columns([1, 1])
    big1.metric(
        label=f"Net working days · {calendar.month_name[month]} {year}",
        value=f"{result.working_days:.0f}",
    )
    big2.metric(
        label="Leaves counted",
        value=f"{len(result.leave_days_used)}",
    )

    # ----- Compact breakdown -----
    c1, c2, c3 = st.columns(3)
    c1.metric("Total days", result.total_days)
    c2.metric("Public holidays", len(result.public_holidays))
    c3.metric("Leaves taken", len(result.leave_days_used))

    # ----- Warnings (overlapping leaves) -----
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

    # ----- Detail expanders (kept collapsed by default) -----
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

    # ---------- Manager note (compact: only public holidays + leaves) ----------
    st.write("---")
    st.subheader("4 · Note for your manager")
    note_lines = [
        f"Subject: Leave note — {calendar.month_name[month]} {year}",
        "",
        "Hi [Manager],",
        "",
        f"Please find below my leave summary for {calendar.month_name[month]} {year}:",
        "",
        f"  Shift timing               : {shift_time}",
        f"  Total calendar days         : {result.total_days}",
        f"  Public / gazetted holidays   : {len(result.public_holidays)}",
        f"  Leaves taken                 : {len(result.leave_days_used)}",
        "",
        f"  Net working days             = {result.working_days:.0f}",
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

    # st.code renders with a one-click copy icon (top-right) — no extra libs
    st.code(note_text, language="text")
    st.download_button(
        label="⬇️ Download as .txt",
        data=note_text,
        file_name=f"leave_note_{int(year)}_{int(month):02d}.txt",
        mime="text/plain",
    )

st.write("")
st.caption("_Holiday source: `holidays` lib (India PUBLIC+OPTIONAL) + RBI 2nd/4th Saturday rule_")