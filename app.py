"""Streamlit UI for the Monthly Leave / Overtime Calculator.

All pure logic lives in `leavecalc.py`. This file only renders UI and calls
`compute_month(...)` from user inputs.
"""

from __future__ import annotations

import calendar
import datetime as dt

import streamlit as st

from leavecalc import compute_month

# Region: user-facing label → backend state code (for holiday lib)
REGION_OPTIONS = ["Hyderabad", "Bangalore"]
REGION_CODES = {"Hyderabad": "TG", "Bangalore": "KA"}

st.set_page_config(page_title="Leave Calculator", page_icon="📅", layout="centered")

# ---------- Helpers ----------
def _fmt_date(d: dt.date) -> str:
    """User-facing format: 'Mon 11 May'."""
    return f"{calendar.day_name[d.weekday()][:3]} {d.day} {calendar.month_name[d.month][:3]}"


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
# Row 1: Month (narrow), Year (narrow), Region (narrow), Shift timing (wider)
r1c1, r1c2, r1c3, r1c4 = st.columns([1.3, 1, 1.5, 2])
with r1c1:
    month = st.selectbox(
        "Month",
        options=list(range(1, 13)),
        index=default_month - 1,
        format_func=calendar.month_name.__getitem__,
        label_visibility="visible",
    )
with r1c2:
    year = st.number_input(
        "Year",
        min_value=2020,
        max_value=2100,
        value=default_year,
        step=1,
    )
with r1c3:
    region = st.selectbox("Region", options=REGION_OPTIONS, index=0)
    state = REGION_CODES[region]
with r1c4:
    SHIFT_OPTIONS = ["13:30 – 22:30 IST", "08:00 – 17:00 IST"]
    shift_time = st.selectbox(
        "Shift timing (IST)",
        options=SHIFT_OPTIONS,
        index=0,
    )

month_start = dt.date(int(year), int(month), 1)
month_end = (month_start.replace(day=1) + dt.timedelta(days=31)).replace(day=1) - dt.timedelta(days=1)

# ---------- Step 2: pick leave dates (accumulating) ----------
st.subheader("2 · Pick leave dates")

# Sub-UI: pick one date at a time, add to session_state list
picker_cols = st.columns([2, 1, 1])
with picker_cols[0]:
    new_date = st.date_input(
        "Add a leave date",
        value=None,
        min_value=month_start,
        max_value=month_end,
    )
with picker_cols[1]:
    st.write("")  # vertical spacer to align button with date input
    if st.button("＋ Add", use_container_width=True):
        if new_date is not None:
            d = dt.date(int(year), int(month), new_date.day)
            if d not in st.session_state.leaves:
                st.session_state.leaves.append(d)
                st.session_state.leaves.sort()
            st.rerun()
with picker_cols[2]:
    st.write("")
    if st.button("✕ Clear", use_container_width=True):
        st.session_state.leaves = []
        st.rerun()

# Show currently accumulated leaves as tickable checkboxes (untick to remove)
confirmed_leaves: list[dt.date] = []
if st.session_state.leaves:
    st.write("**Selected leave dates**  ·  _untick to remove_")
    for d in st.session_state.leaves:
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

    # ----- Result: hero card -----
    st.write("")
    st.markdown(
        f"""
        <div style="
            text-align:center;
            padding:2rem 1rem 1.5rem;
            background:linear-gradient(135deg,#f8f9fa,#eef2f7);
            border-radius:16px;
            border:1px solid #e0e4ea;
        ">
            <p style="font-size:0.85rem;letter-spacing:0.08em;text-transform:uppercase;
                     color:#6b7280;margin:0 0 0.3rem 0;">Net working days</p>
            <h1 style="font-size:4.5rem;font-weight:800;margin:0;line-height:1;
                       color:#1a1a2e;">{result.working_days:.0f}</h1>
            <p style="font-size:1rem;color:#6b7280;margin:0.5rem 0 0 0;">
                {calendar.month_name[month]} {year}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Compact one-line breakdown — inline stats, no boxes
    working_days_pre_leave = result.total_days - len(result.weekend_days) - len(result.public_holidays)
    st.markdown("&nbsp;")
    bd = st.columns(4)
    stats = [
        ("Calendar days", str(result.total_days)),
        ("Holidays", str(len(result.public_holidays))),
        ("Leaves", str(len(result.leave_days_used))),
        ("Weekends", str(len(result.weekend_days))),
    ]
    for col, (label, val) in zip(bd, stats):
        col.markdown(
            f'<div style="text-align:center;">'
            f'<p style="font-size:2rem;font-weight:700;margin:0;color:#1a1a2e;">{val}</p>'
            f'<p style="font-size:0.8rem;color:#6b7280;margin:0;text-transform:uppercase;'
            f'letter-spacing:0.05em;">{label}</p>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Warnings — compact, only if needed
    if result.leave_on_nonworking:
        st.markdown("&nbsp;")
        with st.expander(f"⚠️ {len(result.leave_on_nonworking)} leave(s) on non-working days — not counted"):
            ph_dates = {pd for pd, _ in result.public_holidays}
            for d in result.leave_on_nonworking:
                tags = []
                if d.weekday() in (5, 6):
                    tags.append(calendar.day_name[d.weekday()][:3])
                if d in ph_dates:
                    tags.append("holiday")
                st.write(f"- {_fmt_date(d)}  ·  _{' / '.join(tags)}_")

    # ---------- Summary (forwardable note) ----------
    st.write("")
    st.markdown("---")

    # Compute working days = calendar days - weekends - public holidays
    working_days_pre_leave = result.total_days - len(result.weekend_days) - len(result.public_holidays)

    # Build aligned note — label width fixed for clean column alignment
    LABEL_W = 28  # width of left label column

    def _row(label: str, value: str) -> str:
        return f"{label.ljust(LABEL_W)}: {value}"

    def _row_eq(label: str, value: str) -> str:
        return f"{label.ljust(LABEL_W)} = {value}"

    note_lines = [
        f"Subject: Leave summary — {calendar.month_name[month]} {year}",
        "",
        "Hi [Manager],",
        "",
        f"Please find below my leave summary for {calendar.month_name[month]} {year}:",
        "",
        _row("Shift timing", shift_time),
        _row("Total calendar days", str(result.total_days)),
        _row("Weekends (Sat + Sun)", str(len(result.weekend_days))),
        _row("Public / gazetted holidays", str(len(result.public_holidays))),
        "",
        _row_eq("Working days (pre-leave)", str(working_days_pre_leave)),
        _row("Leaves taken", str(len(result.leave_days_used))),
        "",
        _row_eq("Net working days", str(int(result.working_days))),
        "",
    ]
    if result.public_holidays:
        note_lines.append("Public holidays:")
        for d, n in result.public_holidays:
            note_lines.append(f"  - {_fmt_date(d)} · {n}")
        note_lines.append("")
    if result.leave_days_used:
        note_lines.append("Leave dates:")
        for d in result.leave_days_used:
            note_lines.append(f"  - {_fmt_date(d)}")
        note_lines.append("")
    note_lines += ["Thanks,", "[Your name]"]
    note_text = "\n".join(note_lines)

    # Prominent copy button using HTML/JS to put note on clipboard
    import streamlit.components.v1 as components
    escaped = note_text.replace("`", "\\`").replace("${", "\\${")
    copy_html = f"""
    <style>
      .copy-btn {{
        background: #1a1a2e;
        color: white;
        border: none;
        padding: 0.6rem 1.2rem;
        border-radius: 8px;
        font-size: 0.95rem;
        font-weight: 500;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin: 0 auto;
      }}
      .copy-btn:hover {{ background: #2a2a4e; }}
      .copy-feedback {{
        text-align:center;
        color:#10a010;
        font-size:0.85rem;
        margin-top:0.4rem;
        opacity:0;
        transition: opacity 0.3s;
      }}
      .copy-feedback.show {{ opacity:1; }}
    </style>
    <div style="text-align:center;">
      <button class="copy-btn" onclick="
        const text = `{escaped}`;
        navigator.clipboard.writeText(text).then(() => {{
          const fb = document.querySelector('.copy-feedback');
          fb.classList.add('show');
          setTimeout(() => fb.classList.remove('show'), 2000);
        }});
      ">📋 Copy summary to clipboard</button>
      <div class="copy-feedback">Copied!</div>
    </div>
    """
    components.html(copy_html, height=80)

    # Note content shown below the button for preview
    st.text(note_text)

st.write("")
st.caption("_Holidays: `holidays` lib (India) + RBI 2nd/4th Saturday rule_")