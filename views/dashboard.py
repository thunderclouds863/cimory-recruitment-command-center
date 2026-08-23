import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from core.metrics import (
    fptk_dataframe,
    kpis,
    category_summary,
    recruiter_summary,
    directorate_summary,
    weekly_trend,
    aging_summary,
    funnel_summary
)


# ============================================================
# THEME
# ============================================================

BG = "#0B3142"
CARD = "#123F52"
CARD_LIGHT = "#174D63"

WHITE = "#F7FAFC"
TEXT_MUTED = "#A9C2CC"

BLUE = "#3AA6D0"
TEAL = "#37C6B1"
ORANGE = "#F4A261"
RED = "#E76F51"
GREEN = "#61C48D"
PURPLE = "#8E7DBE"


# ============================================================
# GLOBAL CSS
# ============================================================

def inject_css():

    st.markdown(
        f"""
        <style>

        .stApp {{
            background:
                radial-gradient(
                    circle at top right,
                    rgba(58,166,208,0.10),
                    transparent 35%
                ),
                {BG};
            color: {WHITE};
        }}

        .block-container {{
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1450px;
        }}

        /* HEADER */

        .dashboard-title {{
            font-size: 30px;
            font-weight: 800;
            letter-spacing: -0.8px;
            color: {WHITE};
            margin-bottom: 2px;
        }}

        .dashboard-subtitle {{
            color: {TEXT_MUTED};
            font-size: 13px;
            margin-bottom: 20px;
        }}

        /* SECTION */

        .section-title {{
            color: {WHITE};
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.8px;
            margin-top: 22px;
            margin-bottom: 10px;
            padding-left: 9px;
            border-left: 3px solid {TEAL};
        }}

        /* KPI */

        .kpi-card {{
            background: linear-gradient(
                145deg,
                {CARD_LIGHT},
                {CARD}
            );
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 15px 17px;
            min-height: 90px;
            box-shadow: 0 8px 22px rgba(0,0,0,0.12);
        }}

        .kpi-label {{
            color: {TEXT_MUTED};
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: .6px;
        }}

        .kpi-value {{
            color: {WHITE};
            font-size: 25px;
            font-weight: 800;
            margin-top: 5px;
        }}

        .kpi-description {{
            color: {TEXT_MUTED};
            font-size: 10px;
            margin-top: 2px;
        }}

        /* ALERT */

        .alert-card {{
            border-radius: 10px;
            padding: 12px 15px;
            background: {CARD};
            border: 1px solid rgba(255,255,255,.08);
        }}

        .alert-number {{
            font-size: 22px;
            font-weight: 800;
        }}

        .alert-label {{
            color: {TEXT_MUTED};
            font-size: 11px;
        }}

        /* CHART CARD */

        .chart-card {{
            background: {CARD};
            border-radius: 12px;
            padding: 8px 10px 2px 10px;
            border: 1px solid rgba(255,255,255,0.06);
        }}

        /* FILTER */

        div[data-testid="stExpander"] {{
            background: {CARD};
            border: 1px solid rgba(255,255,255,.07);
            border-radius: 10px;
        }}

        /* DATAFRAME */

        div[data-testid="stDataFrame"] {{
            border-radius: 10px;
            overflow: hidden;
        }}

        /* SELECT */

        label {{
            color: {TEXT_MUTED} !important;
        }}

        </style>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# PLOTLY THEME
# ============================================================

def chart_layout(fig, height=300):

    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Arial",
            color=WHITE,
            size=11
        ),
        margin=dict(
            l=10,
            r=10,
            t=35,
            b=20
        ),
        legend=dict(
            orientation="h",
            y=-0.15,
            font=dict(size=10)
        ),
        hoverlabel=dict(
            bgcolor=CARD,
            font_color=WHITE
        )
    )

    fig.update_xaxes(
        gridcolor="rgba(255,255,255,0.06)",
        zeroline=False,
        linecolor="rgba(255,255,255,0.08)"
    )

    fig.update_yaxes(
        gridcolor="rgba(255,255,255,0.06)",
        zeroline=False,
        linecolor="rgba(255,255,255,0.08)"
    )

    return fig


# ============================================================
# CARD
# ============================================================

def chart_container(title, fig, height=300):

    st.markdown(
        f"""
        <div class="chart-card">
            <div style="
                font-size:13px;
                font-weight:700;
                padding:5px 5px 0 5px;
                color:{WHITE};
            ">
                {title}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False
        }
    )


# ============================================================
# KPI CARD
# ============================================================

def metric_card(label, value, description=""):

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            <div class="kpi-description">{description}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# STATUS CHART
# ============================================================

def create_status_chart(df):

    data = (
        df["Status"]
        .value_counts()
        .rename_axis("Status")
        .reset_index(name="Count")
    )

    fig = px.bar(
        data,
        x="Count",
        y="Status",
        orientation="h",
        text="Count",
        color="Status",
        color_discrete_map={
            "Closed": TEAL,
            "OP": ORANGE,
            "Cancel": RED
        }
    )

    fig.update_traces(
        textposition="outside",
        marker_line_width=0
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None
    )

    return chart_layout(fig, 270)


# ============================================================
# DIRECTORATE
# ============================================================

def create_directorate_chart(df):

    data = (
        df["Direktorat"]
        .value_counts()
        .head(10)
        .sort_values()
        .reset_index()
    )

    data.columns = ["Directorate", "Count"]

    fig = px.bar(
        data,
        x="Count",
        y="Directorate",
        orientation="h",
        text="Count"
    )

    fig.update_traces(
        marker_color=BLUE,
        textposition="outside"
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None
    )

    return chart_layout(fig, 320)


# ============================================================
# RECRUITER
# ============================================================

def create_recruiter_chart(df):

    data = (
        df["PIC Recruiter"]
        .value_counts()
        .head(10)
        .sort_values()
        .reset_index()
    )

    data.columns = ["Recruiter", "FPTK"]

    fig = px.bar(
        data,
        x="FPTK",
        y="Recruiter",
        orientation="h",
        text="FPTK"
    )

    fig.update_traces(
        marker_color=TEAL,
        textposition="outside"
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None
    )

    return chart_layout(fig, 320)


# ============================================================
# LEVEL MIX
# ============================================================

def create_level_chart(df):

    data = (
        df["Filter Kategorisasi FPTK"]
        .value_counts()
        .reset_index()
    )

    data.columns = ["Category", "Count"]

    fig = px.pie(
        data,
        names="Category",
        values="Count",
        hole=.62,
        color_discrete_sequence=[
            BLUE,
            TEAL,
            ORANGE,
            PURPLE,
            RED
        ]
    )

    fig.update_traces(
        textposition="inside",
        textinfo="percent",
        hovertemplate="%{label}<br>%{value} FPTK<extra></extra>"
    )

    fig.update_layout(
        showlegend=True
    )

    return chart_layout(fig, 310)


# ============================================================
# DEMAND DRIVER
# ============================================================

def create_reason_chart(df):

    data = (
        df["Alasan Permintaan FPTK"]
        .value_counts()
        .head(6)
        .sort_values()
        .reset_index()
    )

    data.columns = ["Reason", "Count"]

    fig = px.bar(
        data,
        x="Count",
        y="Reason",
        orientation="h",
        text="Count"
    )

    fig.update_traces(
        marker_color=ORANGE,
        textposition="outside"
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None
    )

    return chart_layout(fig, 300)


# ============================================================
# WEEKLY TREND
# ============================================================

def create_weekly_chart(df):

    temp = df.copy()

    temp["FPTK Date"] = pd.to_datetime(
        temp["FPTK Date (Real)"],
        errors="coerce"
    )

    temp = temp.dropna(subset=["FPTK Date"])

    temp["Week"] = (
        temp["FPTK Date"]
        .dt.to_period("W")
        .apply(lambda x: x.start_time)
    )

    trend = (
        temp.groupby(["Week", "Status"])
        .size()
        .reset_index(name="Count")
    )

    fig = px.line(
        trend,
        x="Week",
        y="Count",
        color="Status",
        markers=True,
        color_discrete_map={
            "Closed": TEAL,
            "OP": ORANGE,
            "Cancel": RED
        }
    )

    fig.update_layout(
        xaxis_title=None,
        yaxis_title=None
    )

    return chart_layout(fig, 310)


# ============================================================
# AGING
# ============================================================

def create_aging_chart(df):

    temp = df.copy()

    temp["FPTK Date"] = pd.to_datetime(
        temp["FPTK Date (Real)"],
        errors="coerce"
    )

    temp = temp[
        (temp["Status"] == "OP") &
        temp["FPTK Date"].notna()
    ].copy()

    today = pd.Timestamp.today().normalize()

    temp["Age"] = (
        today - temp["FPTK Date"]
    ).dt.days

    def bucket(x):

        if x <= 7:
            return "0-7 Days"
        elif x <= 14:
            return "8-14 Days"
        elif x <= 30:
            return "15-30 Days"
        elif x <= 60:
            return "31-60 Days"
        return ">60 Days"

    temp["Aging"] = temp["Age"].apply(bucket)

    order = [
        "0-7 Days",
        "8-14 Days",
        "15-30 Days",
        "31-60 Days",
        ">60 Days"
    ]

    data = (
        temp["Aging"]
        .value_counts()
        .reindex(order, fill_value=0)
        .reset_index()
    )

    data.columns = ["Aging", "Count"]

    fig = px.bar(
        data,
        x="Aging",
        y="Count",
        text="Count",
        color="Aging",
        color_discrete_sequence=[
            GREEN,
            TEAL,
            BLUE,
            ORANGE,
            RED
        ]
    )

    fig.update_traces(
        textposition="outside"
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None
    )

    return chart_layout(fig, 300)


# ============================================================
# FUNNEL
# ============================================================

def create_funnel(user):

    try:

        data = funnel_summary(user)

        if data is None:
            return None

        data = pd.DataFrame(data)

        if data.empty:
            return None

        # Detect label and value columns
        label_col = None
        value_col = None

        for c in data.columns:

            if data[c].dtype == "object":
                label_col = c
                break

        numeric_cols = data.select_dtypes(
            include=np.number
        ).columns.tolist()

        if numeric_cols:
            value_col = numeric_cols[-1]

        if label_col is None or value_col is None:
            return None

        data = data[
            [label_col, value_col]
        ].dropna()

        data.columns = [
            "Stage",
            "Count"
        ]

        data = data[
            data["Count"] > 0
        ]

        if data.empty:
            return None

        fig = go.Figure(
            go.Funnel(
                y=data["Stage"],
                x=data["Count"],
                textinfo="value+percent initial",
                marker={
                    "color": [
                        BLUE,
                        TEAL,
                        GREEN,
                        ORANGE,
                        PURPLE,
                        RED
                    ]
                }
            )
        )

        return chart_layout(fig, 390)

    except Exception:
        return None


# ============================================================
# MAIN
# ============================================================

def render(user):

    inject_css()

    # ========================================================
    # HEADER
    # ========================================================

    st.markdown(
        """
        <div class="dashboard-title">
            Recruitment Command Center
        </div>

        <div class="dashboard-subtitle">
            Recruitment Performance & Pipeline Intelligence
        </div>
        """,
        unsafe_allow_html=True
    )

    # ========================================================
    # DATA
    # ========================================================

    df = fptk_dataframe(user)

    if df.empty:

        st.info(
            "Belum ada data. Admin dapat import "
            "MASTER_COMPILE/DB_FPTK_TEMPLATE atau menjalankan demo seed."
        )

        return

    # ========================================================
    # FILTER
    # ========================================================

    with st.expander(
        "FILTER & CONTROL",
        expanded=False
    ):

        c1, c2, c3, c4, c5 = st.columns(5)

        dirs = c1.multiselect(
            "Directorate",
            sorted(
                df["Direktorat"]
                .dropna()
                .astype(str)
                .unique()
            )
        )

        recruiters = c2.multiselect(
            "Recruiter",
            sorted(
                df["PIC Recruiter"]
                .dropna()
                .astype(str)
                .unique()
            )
        )

        levels = c3.multiselect(
            "Level",
            sorted(
                df["Level FPTK"]
                .dropna()
                .astype(str)
                .unique()
            )
        )

        categories = c4.multiselect(
            "Category",
            sorted(
                df["Category FPTK"]
                .dropna()
                .astype(str)
                .unique()
            )
        )

        statuses = c5.multiselect(
            "Status",
            sorted(
                df["Status"]
                .dropna()
                .astype(str)
                .unique()
            )
        )

    if dirs:
        df = df[
            df["Direktorat"].isin(dirs)
        ]

    if recruiters:
        df = df[
            df["PIC Recruiter"].isin(recruiters)
        ]

    if levels:
        df = df[
            df["Level FPTK"].isin(levels)
        ]

    if categories:
        df = df[
            df["Category FPTK"].isin(categories)
        ]

    if statuses:
        df = df[
            df["Status"].isin(statuses)
        ]

    # ========================================================
    # KPI
    # ========================================================

    m = kpis(df)

    st.markdown(
        '<div class="section-title">RECRUITMENT OVERVIEW</div>',
        unsafe_allow_html=True
    )

    cols = st.columns(7)

    metrics = [
        (
            "Total FPTK",
            f"{m['total']:,}",
            "Total manpower request"
        ),
        (
            "Open",
            f"{m['open']:,}",
            "Active recruitment"
        ),
        (
            "Closed",
            f"{m['closed']:,}",
            "Successfully closed"
        ),
        (
            "Cancel",
            f"{m['cancel']:,}",
            "Cancelled request"
        ),
        (
            "Fill Rate",
            f"{m['fill_rate']:.1f}%",
            "Fulfillment achievement"
        ),
        (
            "Closed SLA",
            f"{m['closed_sla']:.1f}%",
            "Closed within SLA"
        ),
        (
            "Over SLA",
            f"{m['over_sla']:,}",
            "Needs attention"
        )
    ]

    for col, metric in zip(
        cols,
        metrics
    ):

        with col:
            metric_card(*metric)

    # ========================================================
    # EXECUTIVE ALERT
    # ========================================================

    st.markdown(
        '<div class="section-title">EXECUTIVE SIGNALS</div>',
        unsafe_allow_html=True
    )

    a1, a2, a3, a4 = st.columns(4)

    with a1:
        st.markdown(
            f"""
            <div class="alert-card">
                <div class="alert-number" style="color:{RED}">
                    {m['over_sla']:,}
                </div>
                <div class="alert-label">
                    FPTK requiring SLA attention
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with a2:

        open_pct = (
            m["open"] / m["total"] * 100
            if m["total"]
            else 0
        )

        st.markdown(
            f"""
            <div class="alert-card">
                <div class="alert-number" style="color:{ORANGE}">
                    {open_pct:.1f}%
                </div>
                <div class="alert-label">
                    Current open pipeline
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with a3:

        replacement = (
            df["Category FPTK"]
            .astype(str)
            .str.upper()
            .eq("REPLACEMENT")
            .sum()
        )

        replacement_pct = (
            replacement / len(df) * 100
            if len(df)
            else 0
        )

        st.markdown(
            f"""
            <div class="alert-card">
                <div class="alert-number" style="color:{BLUE}">
                    {replacement_pct:.1f}%
                </div>
                <div class="alert-label">
                    Replacement demand
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with a4:

        top_department = (
            df["Department"]
            .value_counts()
            .index[0]
            if not df["Department"].dropna().empty
            else "-"
        )

        st.markdown(
            f"""
            <div class="alert-card">
                <div class="alert-number" style="color:{TEAL};font-size:17px">
                    {top_department}
                </div>
                <div class="alert-label">
                    Highest demand department
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ========================================================
    # STATUS + FUNNEL
    # ========================================================

    st.markdown(
        '<div class="section-title">PIPELINE HEALTH</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns([0.9, 1.6])

    with c1:

        fig = create_status_chart(df)

        st.markdown(
            '<div class="chart-card">',
            unsafe_allow_html=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

        st.markdown(
            '</div>',
            unsafe_allow_html=True
        )

    with c2:

        funnel_fig = create_funnel(user)

        if funnel_fig is not None:

            st.plotly_chart(
                funnel_fig,
                use_container_width=True,
                config={"displayModeBar": False}
            )

        else:

            st.info(
                "Funnel data belum tersedia."
            )

    # ========================================================
    # TREND + AGING
    # ========================================================

    c1, c2 = st.columns(2)

    with c1:

        fig = create_weekly_chart(df)

        st.markdown(
            '<div class="section-title">FPTK TREND</div>',
            unsafe_allow_html=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    with c2:

        fig = create_aging_chart(df)

        st.markdown(
            '<div class="section-title">OPEN FPTK AGING</div>',
            unsafe_allow_html=True
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    # ========================================================
    # DEMAND ANALYTICS
    # ========================================================

    st.markdown(
        '<div class="section-title">DEMAND ANALYTICS</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:

        fig = create_level_chart(df)

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    with c2:

        fig = create_reason_chart(df)

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    # ========================================================
    # ORGANIZATION ANALYTICS
    # ========================================================

    st.markdown(
        '<div class="section-title">ORGANIZATION & WORKLOAD</div>',
        unsafe_allow_html=True
    )

    c1, c2 = st.columns(2)

    with c1:

        fig = create_directorate_chart(df)

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    with c2:

        fig = create_recruiter_chart(df)

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    # ========================================================
    # EXECUTIVE TABLE
    # ========================================================

    st.markdown(
        '<div class="section-title">EXECUTIVE SUMMARY</div>',
        unsafe_allow_html=True
    )

    summary = category_summary(df)

    if summary is not None and not summary.empty:

        st.dataframe(
            summary,
            use_container_width=True,
            hide_index=True,
            height=300
        )
