from __future__ import annotations
import base64
import io
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components
from typing import Optional

NAVY = "#0B3142"
CARD = "#123F52"
WHITE = "#F5F8FA"
MUTED = "#9FB7C1"
BLUE = "#3AA6D0"
TEAL = "#37C6B1"
ORANGE = "#F4A261"
RED = "#E76F51"
GREEN = "#61C48D"
PURPLE = "#8E7DBE"
GRID = "rgba(255,255,255,.07)"


def style(fig, height=300, title=None):
    if title:
        fig.update_layout(title=dict(text=title, x=0.02, xanchor="left", font=dict(size=13, color=WHITE)))
    fig.update_layout(
        height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial", color=WHITE, size=10), margin=dict(l=8, r=8, t=42, b=20),
        legend=dict(font=dict(color=MUTED, size=9), orientation="h", y=-0.14),
        hoverlabel=dict(bgcolor=CARD, font_color=WHITE),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, title=None, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=None, tickfont=dict(color=MUTED))
    return fig


def _download_df_csv(df: pd.DataFrame, key: str, label: str = "Download CSV"):
    if df is None or df.empty:
        return
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(label, data=csv, file_name=f"{key}.csv", mime="text/csv", key=f"dl_{key}")


def show_chart(fig, key: str, copyable: bool = False, data: Optional[pd.DataFrame] = None):
    """Render a plotly figure and provide export buttons.
    If copyable is True we'll attempt to produce a PNG via Kaleido; on failure we show a helpful message.
    If `data` is provided, we render a CSV download button as fallback/export.
    """
    if fig is None:
        return
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "displayModeBar": False})

    try:
        if copyable:
            png = fig.to_image(format="png", scale=2)
            c1, c2 = st.columns([1, 1])
            c1.download_button("Download PNG", png, file_name=f"{key}.png", mime="image/png", key=f"dl_png_{key}")
            # small helper to open image in new tab
            b64 = base64.b64encode(png).decode()
            html = f"""
            <div style='display:flex;gap:8px'>
            <a href='data:image/png;base64,{b64}' download='{key}.png' style='text-decoration:none'><button style='padding:8px;border-radius:8px;border:1px solid #d0d5dd;background:#ffffff;color:#0b3142;cursor:pointer'>Open PNG</button></a>
            </div>
            """
            with c2:
                components.html(html, height=46)
    except Exception as e:
        st.warning(
            "PNG export tidak tersedia: Kaleido belum terpasang atau environment tidak mendukung menjalankan binary. "
            "Untuk memperbaiki secara lokal jalankan `pip install kaleido`. Untuk deployment (Streamlit Cloud / Docker) tambahkan `kaleido` ke requirements.txt dan redeploy."
        )
        st.caption(f"Detail error: {str(e)}")

    # CSV export if data provided
    if data is not None:
        try:
            _download_df_csv(data, key)
        except Exception:
            st.caption("Gagal menyiapkan CSV export untuk chart ini.")


def status_chart(df: pd.DataFrame):
    x = df.status.fillna("Unknown").value_counts().rename_axis("Status").reset_index(name="Count")
    # normalize known codes
    mapping = {"OP": "Open", "Closed": "Closed", "Cancel": "Cancel"}
    x["Status"] = x["Status"].map(mapping).fillna(x["Status"])
    fig = px.bar(x.sort_values("Count"), x="Count", y="Status", orientation="h", text="Count",
                 color="Status", color_discrete_map={"Closed": TEAL, "Open": ORANGE, "Cancel": RED})
    fig.update_traces(textposition="outside", marker_line_width=0)
    fig.update_layout(showlegend=False, xaxis_showgrid=False)
    return style(fig, 300, "FPTK Status")


def directorate_chart(summary: pd.DataFrame):
    if summary is None or summary.empty:
        return style(go.Figure(), 300, "FPTK by Directorate")
    x = summary.head(10).sort_values("Total")
    fig = px.bar(x, x="Total", y="Directorate", orientation="h", text="Total", color_discrete_sequence=[TEAL])
    fig.update_traces(textposition="outside", marker_line_width=0)
    fig.update_layout(showlegend=False)
    return style(fig, 320, "FPTK by Directorate")


def recruiter_chart(summary: pd.DataFrame):
    if summary is None or summary.empty:
        return style(go.Figure(), 300, "Recruiter Workload")
    x = summary.head(15).sort_values("Open")
    fig = px.bar(x, x="Open", y="Recruiter", orientation="h", text="Open", color_discrete_sequence=[TEAL])
    fig.update_traces(textposition="outside", marker_line_width=0)
    fig.update_layout(showlegend=False)
    return style(fig, 340, "Open FPTK by Recruiter")


def weekly_chart(summary: pd.DataFrame):
    if summary is None or summary.empty:
        return style(go.Figure(), 300, "Weekly FPTK Trend")
    fig = px.line(summary, x="Week", y=["FPTK Processed", "Closed"], markers=True,
                  color_discrete_map={"FPTK Processed": BLUE, "Closed": TEAL})
    fig.update_traces(line=dict(width=2.5))
    return style(fig, 320, "FPTK Inflow vs Closure")


def funnel_chart(summary: pd.DataFrame):
    if summary is None or summary.empty:
        return style(go.Figure(), 360, "Recruitment Funnel")
    x = summary.copy()
    # compute percent of initial stage
    initial = x.iloc[0]["Count"] if not x.empty else 0
    x["Pct of initial"] = (x["Count"] / initial * 100).round(1) if initial else 0
    hover = x.apply(lambda r: f"{r['Stage']}: {r['Count']} ({r['Pct of initial']}% of initial)", axis=1)
    fig = go.Figure(go.Funnel(
        y=x["Stage"], x=x["Count"], textinfo="value+percent initial",
        marker=dict(color=[BLUE, TEAL, GREEN, ORANGE, PURPLE, RED][:len(x)]),
        hoverinfo="text",
        text=hover
    ))
    return style(fig, 420, "Recruitment Funnel")


def aging_chart(summary: pd.DataFrame):
    if summary is None or summary.empty:
        return style(go.Figure(), 300, "Open FPTK Aging")
    x = summary.copy()
    colors = [GREEN, TEAL, BLUE, ORANGE, RED][:len(x)]
    fig = px.bar(x, x="Aging", y="Open", text="Open", color="Aging", color_discrete_sequence=colors)
    fig.update_traces(textposition="outside", marker_line_width=0)
    fig.update_layout(showlegend=False)
    return style(fig, 300, "Open FPTK Aging")


def time_to_fill_chart(summary: pd.DataFrame):
    """summary: dataframe with Week, avg_days, median_days"""
    if summary is None or summary.empty:
        return style(go.Figure(), 340, "Time to Fill (avg & median)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=summary["Week"], y=summary["avg_days"], mode="lines+markers", name="Avg days", line=dict(color=ORANGE, width=2.5)))
    fig.add_trace(go.Scatter(x=summary["Week"], y=summary["median_days"], mode="lines+markers", name="Median days", line=dict(color=TEAL, width=2.5)))
    return style(fig, 340, "Time to Fill (days)")


def time_to_fill_boxplot(closed_df: pd.DataFrame):
    """closed_df must contain a numeric column 'days_to_fill'"""
    if closed_df is None or closed_df.empty or "days_to_fill" not in closed_df.columns:
        return style(go.Figure(), 300, "Time to Fill Distribution")
    fig = px.box(closed_df, y="days_to_fill", points="outliers", color_discrete_sequence=[ORANGE])
    fig.update_layout(yaxis_title="Days to Fill")
    return style(fig, 300, "Time to Fill Distribution")


def recruiter_heatmap(df: pd.DataFrame):
    if df is None or df.empty:
        return style(go.Figure(), 360, "Recruiter Workload Heatmap")
    x = df[df.status == "OP"].copy()
    if x.empty:
        return style(go.Figure(), 360, "Recruiter Workload Heatmap")
    x["days"] = (pd.Timestamp(pd.Timestamp.today().date()) - x.fptk_date).dt.days
    bins = [-1, 30, 60, 90, 120, 10 ** 6]
    labels = ["0-30", "31-60", "61-90", "91-120", ">120"]
    x["Aging"] = pd.cut(x["days"], bins=bins, labels=labels)
    pivot = x.groupby(["pic_recruiter", "Aging"]).size().unstack(fill_value=0)
    # keep top recruiters by total workload
    pivot["total"] = pivot.sum(axis=1)
    pivot = pivot.sort_values("total", ascending=False).head(20).drop(columns="total")
    fig = px.imshow(pivot, labels=dict(x="Aging", y="Recruiter", color="Open"), aspect="auto", color_continuous_scale="Teal")
    fig.update_xaxes(side="top")
    return style(fig, 420, "Recruiter × Aging Heatmap")


def category_growth_chart(current: pd.DataFrame, previous: pd.DataFrame):
    """Expect dataframes with columns Category and FPTK"""
    if current is None or current.empty:
        return style(go.Figure(), 320, "Category Demand")
    cur = current.set_index("Category")["FPTK"]
    prev = previous.set_index("Category")["FPTK"] if (previous is not None and not previous.empty) else pd.Series(dtype=int)
    df = pd.DataFrame({"current": cur, "previous": prev}).fillna(0)
    df["change_pct"] = ((df["current"] - df["previous"]) / df["previous"].replace(0, pd.NA) * 100).fillna(0)
    df = df.sort_values("current")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["current"], y=df.index, orientation="h", name="Current", marker_color=TEAL))
    fig.add_trace(go.Bar(x=df["change_pct"], y=df.index, orientation="h", name="Change %", marker_color=ORANGE, xaxis="x2"))
    # create secondary x-axis for change %
    fig.update_layout(xaxis2=dict(overlaying="x", side="top", position=0.95, showgrid=False, tickformat=".0f"), barmode="relative")
    return style(fig, 420, "Category Demand & Change")
