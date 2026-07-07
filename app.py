# app.py — Jamboree Arrival Day Dashboard (Streamlit)
# Run with: python -m streamlit run app.py

import time
import pandas as pd
import streamlit as st
from datetime import datetime

from config import (
    GOOGLE_SHEET_ID,
    STATUS_COLORS,
    STATUS_ORDER,
    POLL_INTERVAL_SECONDS,
)
from data_loader import load_registry, fetch_checkins
from state_manager import build_unit_states, summary_stats, arrival_distribution, leg_durations
from charts import (
    arrival_distribution_chart,
    transport_donut,
    status_pipeline_bar,
    variance_histogram,
    leg_duration_chart,
)

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Jamboree Arrival Day",
    page_icon="⛺",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Minimal custom CSS ────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1200px; }
    .metric-card { background: #16233D; border-radius: 10px; padding: 14px 18px; }
    .metric-value { font-size: 2rem; font-weight: 500; line-height: 1.1; }
    .metric-label { font-size: 0.75rem; color: #A0AEC0; text-transform: uppercase;
                    letter-spacing: .06em; margin-bottom: 4px; }
    .status-pill { display: inline-block; padding: 2px 10px; border-radius: 999px;
                   font-size: 0.72rem; font-weight: 500; }
    .unmatched-banner { background: #7C1A1A; border-radius: 8px; padding: 10px 14px;
                        font-size: 0.82rem; color: #FCA5A5; margin-bottom: 1rem; }
    div[data-testid="stMetric"] { background: #16233D; border-radius: 10px;
                                   padding: 12px 16px; border: 1px solid #2D4068; }
    div[data-testid="stMetricLabel"] { color: #A0AEC0 !important; }
    hr { border-color: #2D4068; }
    .header-rule { border-top: 2px solid #C41230; margin: 0.5rem 0 1rem 0; }
</style>
""", unsafe_allow_html=True)


# ── Status badge helper ───────────────────────────────────────────────────────
STATUS_BG = {
    "Not arrived":   ("#F1EFE8", "#5F5E5A"),
    "At Ruby":       ("#FAEEDA", "#854F0B"),
    "At South Gate": ("#E6F1FB", "#185FA5"),
    "On-site":       ("#EAF3DE", "#3B6D11"),
    "Checked-in":    ("#F3E8FF", "#6B21A8"),
}

def status_badge(status: str) -> str:
    bg, fg = STATUS_BG.get(status, ("#F1EFE8", "#5F5E5A"))
    return (f'<span class="status-pill" style="background:{bg};color:{fg}">'
            f'{status}</span>')


def fmt_time(ts) -> str:
    if ts is None or (isinstance(ts, float) and pd.isna(ts)):
        return "—"
    if isinstance(ts, str):
        return ts
    try:
        return pd.Timestamp(ts).strftime("%-I:%M %p")
    except Exception:
        return str(ts)


def fmt_variance(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    sign = "+" if v > 0 else ""
    color = "#A32D2D" if v > 15 else "#3B6D11" if v < -5 else "#5F5E5A"
    return f'<span style="color:{color};font-weight:500">{sign}{v:.0f} min</span>'


# ── Data loading ─────────────────────────────────────────────────────────────
registry = load_registry()

if not registry:
    st.error("No roster loaded. Please import your unit roster JSON first.")
    st.stop()

checkins = fetch_checkins(GOOGLE_SHEET_ID)
unit_df, unmatched = build_unit_states(registry, checkins)
stats = summary_stats(unit_df)
leg_stats = leg_durations(unit_df)
dist_df = arrival_distribution(unit_df, registry)


# ── Header ────────────────────────────────────────────────────────────────────
logo_col, title_col, refresh_col = st.columns([1, 4, 1])

with logo_col:
    try:
        st.image("jambo_logo.png", width=110)
    except Exception:
        st.markdown("⛺")  # fallback if logo file isn't found

with title_col:
    st.markdown(
        "<h1 style='margin:0; padding-top:12px; font-size:1.7rem; "
        "color:#FFFFFF; font-weight:600; letter-spacing:0.01em;'>"
        "Arrival Day Dashboard</h1>",
        unsafe_allow_html=True
    )
    st.markdown(
        f"<p style='margin:0; color:#A0AEC0; font-size:0.82rem;'>"
        f"Summit Bechtel Reserve &nbsp;·&nbsp; "
        f"{datetime.now().strftime('%A, %B %d · %I:%M %p')} &nbsp;·&nbsp; "
        f"auto-refreshes every {POLL_INTERVAL_SECONDS}s</p>",
        unsafe_allow_html=True
    )

with refresh_col:
    st.markdown("<div style='padding-top:22px'>", unsafe_allow_html=True)
    if st.button("↺ Refresh now"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='header-rule'></div>", unsafe_allow_html=True)

st.divider()


# ── Unmatched alerts ──────────────────────────────────────────────────────────
if unmatched:
    with st.expander(f"⚠ {len(unmatched)} unmatched check-in(s) need attention", expanded=True):
        um_df = pd.DataFrame(unmatched)
        um_df["timestamp"] = um_df["timestamp"].apply(fmt_time)
        st.dataframe(um_df, use_container_width=True, hide_index=True)


# ── Metric cards ──────────────────────────────────────────────────────────────
m1, m2, m3, m4, m5 = st.columns(5)

with m1:
    st.metric("Checked-in", stats["checked_in"],
              delta=f"{round(stats['checked_in'] / stats['total'] * 100)}% of total" if stats["total"] else None)
with m2:
    st.metric("On-site", stats["on_site"],
              delta=f"{round(stats['on_site'] / stats['total'] * 100)}% of total" if stats["total"] else None)
with m3:
    st.metric("In transit", stats["in_transit"],
              delta="at Ruby or South Gate")
with m4:
    st.metric("Not arrived", stats["not_arrived"],
              delta=f"of {stats['total']} total units")
with m5:
    var = stats["avg_variance"]
    if var is not None:
        label = f"+{var} min (late)" if var > 0 else f"{var} min (early)"
    else:
        label = "No arrivals yet"
    st.metric("Avg variance", label)

st.divider()


# ── Charts row ────────────────────────────────────────────────────────────────
chart_left, chart_right = st.columns([3, 1])

with chart_left:
    st.markdown("##### Arrival Distribution")
    st.plotly_chart(arrival_distribution_chart(dist_df), use_container_width=True)


with chart_right:
    st.markdown("##### Transportation Type")
    st.plotly_chart(transport_donut(stats["motor_coach"], stats["personal_vehicle"]),
                    use_container_width=True)
    st.caption(
        f"Motor coach: **{stats['motor_coach']}**  ·  "
        f"Personal vehicle: **{stats['personal_vehicle']}**"
    )


st.markdown("##### Travel Time Between Checkpoints")
st.plotly_chart(leg_duration_chart(leg_stats), use_container_width=True)

leg_cols = st.columns(3)
leg_labels = {
    "ruby_to_southgate":     "Ruby → South Gate",
    "southgate_to_basecamp": "South Gate → Basecamp",
    "ruby_to_basecamp":      "Ruby → Basecamp",
}
for col, (key, label) in zip(leg_cols, leg_labels.items()):
    stat = leg_stats[key]
    with col:
        if stat["count"] > 0:
            st.metric(label, f"{stat['avg']:.0f} min",
                     delta=f"{stat['count']} units · range {stat['min']:.0f}–{stat['max']:.0f} min")
        else:
            st.metric(label, "No data yet")


st.markdown("##### Arrival Time Variance Distribution (on-site units)")
st.plotly_chart(variance_histogram(unit_df), use_container_width=True)


st.divider()


# ── Unit status table ─────────────────────────────────────────────────────────
st.markdown("##### Unit Status")

filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
with filter_col1:
    search = st.text_input("Search", placeholder="Unit number or council…", label_visibility="collapsed")
with filter_col2:
    status_filter = st.selectbox("Status", ["All statuses"] + STATUS_ORDER, label_visibility="collapsed")
with filter_col3:
    transport_filter = st.selectbox("Transport", ["All transport", "Motor coach", "Personal vehicle"],
                                    label_visibility="collapsed")

display_df = unit_df.copy()

if search:
    mask = (
        display_df["unit_number"].str.contains(search, case=False, na=False) |
        display_df["council"].str.contains(search, case=False, na=False)
    )
    display_df = display_df[mask]

if status_filter != "All statuses":
    display_df = display_df[display_df["status"] == status_filter]

if transport_filter != "All transport":
    keyword = "motor|coach|bus" if transport_filter == "Motor coach" else "personal|vehicle"
    display_df = display_df[
        display_df["transport"].str.lower().str.contains(keyword, na=False)
    ]

display_df = display_df.sort_values("status")

# Build HTML table for rich status badges
table_rows = []
for _, row in display_df.iterrows():
    table_rows.append({
        "Unit":       row["unit_number"],
        "Council":    row["council"],
        "Status":     status_badge(row["status"]),
        "Transport":  row["transport"],
        "Expected":   row["expected_time"],
        "Ruby":       fmt_time(row["ruby_time"]),
        "South Gate": fmt_time(row["south_gate_time"]),
        "On-site":    fmt_time(row["onsite_time"]),
        "Check-in":   fmt_time(row["checkin_time"]),
        "Variance":   fmt_variance(row["variance_minutes"]),
        "Notes":      row["last_checkin_notes"],
    })

if table_rows:
    table_df = pd.DataFrame(table_rows)
    st.write(
        table_df.to_html(escape=False, index=False, classes="dataframe"),
        unsafe_allow_html=True,
    )
    st.caption(f"Showing {len(display_df)} of {len(unit_df)} units")
else:
    st.info("No units match the current filters.")

st.divider()
st.caption(
    "Data source: Google Form → Google Sheets · "
    f"Sheet ID: `{GOOGLE_SHEET_ID[:12]}…` · "
    f"Roster: {len(registry)} units"
)

# ── Auto-rerun ────────────────────────────────────────────────────────────────
time.sleep(POLL_INTERVAL_SECONDS)
st.rerun()
