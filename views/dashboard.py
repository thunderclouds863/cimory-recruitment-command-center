from __future__ import annotations
from pathlib import Path
import pandas as pd
import streamlit as st

from core.metrics import (
    fptk_dataframe, kpis, category_summary, recruiter_summary,
    directorate_summary, weekly_trend, aging_summary, funnel_summary
)
from core.charts import (
    show_chart, status_chart, directorate_chart, recruiter_chart,
    weekly_chart, funnel_chart, aging_chart
)

CSS_PATH = Path(__file__).resolve().parents[1] / "assets" / "dashboard.css"


def _css():
    # Prefer external CSS if present so designers can tweak without changing code
    if CSS_PATH.exists():
        st.markdown(f"<style>{CSS_PATH.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

    # Inline CSS fallback / additions for richer visuals
    st.markdown("""
    <style>
    :root{
      --bg:#08303a;        /* deep teal background */
      --card:#0e3f4a;      /* card bg */
      --muted:#9fb7c1;     /* labels */
      --accent:#37c6b1;    /* accent */
      --accent-2:#3aa6d0;  /* secondary accent */
      --danger:#e76f51;    /* alert */
      --glass: rgba(255,255,255,0.03);
    }
    .stApp{background:var(--bg); color:#F5F8FA}
    .block-container{padding-top:1rem;padding-bottom:2rem;max-width:1500px}
    [data-testid="stSidebar"]{background:linear-gradient(180deg,#05272e,#07353e)}

    /* Header */
    .dashboard-header{display:flex;align-items:center;gap:12px}
    .dashboard-title{font-size:24px;font-weight:700;margin-bottom:0}
    .dashboard-subtitle{font-size:12px;color:var(--muted);margin-top:0}

    /* KPI row */
    .kpi-row{display:flex;gap:12px}
    .kpi{background:var(--card);padding:12px;border-radius:10px;flex:1;box-shadow:0 2px 8px rgba(0,0,0,0.3);min-width:110px}
    .kpi .label{font-size:12px;color:var(--muted)}
    .kpi .value{font-size:20px;font-weight:700;margin-top:6px}
    .kpi .hint{font-size:11px;color:var(--muted);margin-top:4px}

    /* Signals */
    .signals{display:flex;gap:10px}
    .signal{background:var(--glass);padding:10px;border-radius:8px;display:flex;flex-direction:column;align-items:flex-start}
    .signal .number{font-size:18px;font-weight:700}
    .signal .text{font-size:12px;color:var(--muted)}

    /* Section labels */
    .section-label{font-size:13px;color:var(--muted);margin-top:18px;margin-bottom:6px}

    /* Insight box */
    .insight{background:linear-gradient(90deg,rgba(55,198,177,0.06),rgba(58,166,208,0.03));padding:10px;border-radius:8px;margin-bottom:8px}

    /* Table tweaks */
    div[data-testid="stDataFrame"] table{background:transparent}

    /* Small helpers */
    .muted{color:var(--muted)}
    </style>
    """, unsafe_allow_html=True)


def _kpi(label, value, hint):
    st.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div><div class="hint">{hint}</div></div>', unsafe_allow_html=True)


def _signal(number, text, color):
    st.markdown(f'<div class="signal"><div class="number" style="color:{color}">{number}</div><div class="text">{text}</div></div>', unsafe_allow_html=True)


def _insight(title, body):
    st.markdown(f'<div class="insight"><b>{title}</b><br><span>{body}</span></div>', unsafe_allow_html=True)


def render(user):
    _css()

    # Header
    st.markdown('<div class="dashboard-header"><div><div class="dashboard-title">Recruitment Command Center</div><div class="dashboard-subtitle">Recruitment Performance & Pipeline Intelligence</div></div></div>', unsafe_allow_html=True)

    df = fptk_dataframe(user)
    if df.empty:
        st.info("Belum ada data. Admin dapat import MASTER_COMPILE/DB_FPTK_TEMPLATE atau jalankan demo seed.")
        return

    # quick download
    csv = df.to_csv(index=False)
    st.download_button("Download CSV", data=csv, file_name="fptk_data.csv", mime="text/csv")

    # Filters (kept in expander to save vertical real estate)
    with st.expander("FILTER & CONTROL", expanded=False):
        c1, c2, c3, c4, c5 = st.columns(5)
        dirs = c1.multiselect("Directorate", sorted(df.directorate.dropna().astype(str).unique()))
        recs = c2.multiselect("Recruiter", sorted(df.pic_recruiter.dropna().astype(str).unique()))
        levels = c3.multiselect("Level", sorted(df.level_fptk.dropna().astype(str).unique()))
        cats = c4.multiselect("Category", sorted(df.filter_category.dropna().astype(str).unique()))
        stats = c5.multiselect("Status", sorted(df.status.dropna().astype(str).unique()))
    if dirs: df = df[df.directorate.isin(dirs)]
    if recs: df = df[df.pic_recruiter.isin(recs)]
    if levels: df = df[df.level_fptk.isin(levels)]
    if cats: df = df[df.filter_category.isin(cats)]
    if stats: df = df[df.status.isin(stats)]

    # KPI overview (bigger, more visual)
    m = kpis(df)
    st.markdown('<div class="section-label">RECRUITMENT OVERVIEW</div>', unsafe_allow_html=True)
    cols = st.columns([1.2,1,1,1,1,1,1])
    vals = [
        ("Total FPTK", f"{m['total']:,}", "Manpower requests"),
        ("Open", f"{m['open']:,}", "Active pipeline"),
        ("Closed", f"{m['closed']:,}", "Fulfilled requests"),
        ("Cancel", f"{m['cancel']:,}", "Cancelled requests"),
        ("Fill Rate", f"{m['fill_rate']:.1f}%", "Fulfillment"),
        ("Closed SLA", f"{m['closed_sla']:.1f}%", "Within SLA"),
        ("Over SLA", f"{m['over_sla']:,}", "Past deadline"),
    ]
    st.markdown('<div class="kpi-row">', unsafe_allow_html=True)
    for item in vals:
        _kpi(*item)
    st.markdown('</div>', unsafe_allow_html=True)

    # Signals
    st.markdown('<div class="section-label">EXECUTIVE SIGNALS</div>', unsafe_allow_html=True)
    today = pd.Timestamp.today().normalize()
    open_df = df[df.status.eq("OP")].copy()
    due7 = int(((open_df.deadline_sla.notna()) & (open_df.deadline_sla >= today) & (open_df.deadline_sla <= today + pd.Timedelta(days=7))).sum())
    missing_pic = int(df.pic_recruiter.fillna("").str.strip().eq("").sum())
    repl = int(df.new_replacement.fillna("").astype(str).str.upper().str.contains("REPLACE").sum())
    repl_pct = repl / max(len(df), 1) * 100
    s1, s2, s3, s4 = st.columns([1,1,1,1])
    with s1: _signal(f"{m['over_sla']:,}", "FPTK already over SLA", "#E76F51")
    with s2: _signal(f"{due7:,}", "Open FPTK due within 7 days", "#F4A261")
    with s3: _signal(f"{repl_pct:.1f}%", "Replacement demand share", "#3AA6D0")
    with s4: _signal(f"{missing_pic:,}", "FPTK without recruiter PIC", "#8E7DBE")

    # Pipeline health (charts)
    st.markdown('<div class="section-label">PIPELINE HEALTH</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.1, 1.6])
    with c1:
        show_chart(status_chart(df), "status")
        st.markdown("<div class='muted' style='margin-top:6px'>Status distribution shows volumes per pipeline stage. Click segments to filter where supported.</div>", unsafe_allow_html=True)
    with c2:
        # funnel uses all users' funnel summary (keeps existing behaviour)
        show_chart(funnel_chart(funnel_summary(user)), "funnel")

    # Trend + Aging
    st.markdown('<div class="section-label">TRENDS & AGING</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        show_chart(weekly_chart(weekly_trend(df)), "weekly")
        st.markdown("<div class='muted' style='margin-top:6px'>Weekly trend for pipeline growth and closures.</div>", unsafe_allow_html=True)
    with c2:
        show_chart(aging_chart(aging_summary(df)), "aging")
        st.markdown("<div class='muted' style='margin-top:6px'>Aging distribution highlights SLA exposure.</div>", unsafe_allow_html=True)

    # Demand & Organization
    st.markdown('<div class="section-label">DEMAND & ORGANIZATION</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        summary = category_summary(df)
        if summary is not None and not summary.empty:
            x = summary.set_index("Category")["FPTK"].sort_values()
            import plotly.express as px
            fig = px.bar(x.reset_index(), x="FPTK", y="Category", orientation="h", text="FPTK", color_discrete_sequence=["#37C6B1"])
            fig.update_traces(textposition="outside", marker_line_width=0)
            fig.update_layout(showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#F5F8FA"), margin=dict(l=8, r=8, t=32, b=12), height=320, title=dict(text="FPTK by Category"))
            fig.update_xaxes(gridcolor="rgba(255,255,255,.07)"); fig.update_yaxes(gridcolor="rgba(255,255,255,.07)")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    with c2:
        show_chart(directorate_chart(directorate_summary(df)), "directorate")

    # Workload & insights
    st.markdown('<div class="section-label">WORKLOAD & RISK</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.3, 0.7])
    with c1:
        show_chart(recruiter_chart(recruiter_summary(df)), "recruiter")
    with c2:
        rs = recruiter_summary(df)
        if rs is not None and not rs.empty:
            top = rs.iloc[0]
            _insight("Highest open workload", f"{top['Recruiter']} currently carries {int(top['Open']):,} open FPTK.")
            risk = rs.sort_values("Over SLA", ascending=False).iloc[0]
            _insight("Highest SLA exposure", f"{risk['Recruiter']} has {int(risk['Over SLA']):,} FPTK over SLA.")
        ds = directorate_summary(df)
        if ds is not None and not ds.empty:
            dtop = ds.iloc[0]
            _insight("Largest demand area", f"{dtop['Directorate']} contributes {int(dtop['Total']):,} FPTK.")
        if missing_pic:
            _insight("Data quality", f"{missing_pic:,} FPTK have no recruiter PIC assigned.")

    # Quick tables for decision makers
    st.markdown('<div class="section-label">EXECUTIVE TABLES</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1, 0.8])
    with c1:
        summary = category_summary(df)
        if summary is not None and not summary.empty:
            display = summary.copy()
            for col in ["Fill Rate", "Closed sesuai SLA"]:
                if col in display.columns:
                    display[col] = display[col].round(1).astype(str) + "%"
            st.dataframe(display, use_container_width=True, hide_index=True, height=300)
    with c2:
        # Top 5 recruiters table
        rs = recruiter_summary(df)
        if rs is not None and not rs.empty:
            top5 = rs.head(5)[["Recruiter", "Open", "Over SLA"]].copy()
            top5.columns = ["Recruiter", "Open", "Over SLA"]
            st.table(top5)
        else:
            st.info("No recruiter summary available")

    # Footer insights + tips
    st.markdown('<div class="section-label">NOTES & ACTIONS</div>', unsafe_allow_html=True)
    st.markdown("""
    - Use filters to focus on a directorate or recruiter.
    - Drill into charts (where supported) to filter items.
    - Export data for deeper analysis.
    """)

