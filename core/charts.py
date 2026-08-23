from __future__ import annotations
import base64
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

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
        font=dict(family="Arial", color=WHITE, size=10), margin=dict(l=8,r=8,t=42,b=20),
        legend=dict(font=dict(color=MUTED, size=9), orientation="h", y=-0.14),
        hoverlabel=dict(bgcolor=CARD, font_color=WHITE),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, title=None, tickfont=dict(color=MUTED))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, title=None, tickfont=dict(color=MUTED))
    return fig


def show_chart(fig, key: str, copyable=False):
    if fig is None:
        return
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo": False, "displayModeBar": False})
    if not copyable:
        return
    try:
        png = fig.to_image(format="png", scale=2)
        c1, c2 = st.columns(2)
        c1.download_button("Download PNG", png, file_name=f"{key}.png", mime="image/png", key=f"dl_{key}", use_container_width=True)
        b64 = base64.b64encode(png).decode()
        html = f"""<button id='copy_{key}' style='width:100%;padding:8px;border:1px solid #d0d5dd;border-radius:8px;background:white;cursor:pointer'>Copy PNG</button><script>document.getElementById('copy_{key}').onclick=async()=>{{try{{const r=await fetch('data:image/png;base64,{b64}');const blob=await r.blob();await navigator.clipboard.write([new ClipboardItem({{'image/png':blob}})]);document.getElementById('copy_{key}').innerText='Copied ✓';}}catch(e){{document.getElementById('copy_{key}').innerText='Clipboard blocked';}}}};</script>"""
        with c2: components.html(html, height=46)
    except Exception:
        st.caption("PNG export membutuhkan Kaleido.")


def status_chart(df):
    x = df.status.fillna("Unknown").value_counts().rename_axis("Status").reset_index(name="Count")
    fig = px.bar(x.sort_values("Count"), x="Count", y="Status", orientation="h", text="Count",
                 color="Status", color_discrete_map={"Closed":TEAL,"OP":ORANGE,"Cancel":RED})
    fig.update_traces(textposition="outside", marker_line_width=0)
    fig.update_layout(showlegend=False, xaxis_showgrid=False)
    return style(fig, 285, "FPTK Status")


def directorate_chart(summary):
    if summary is None or summary.empty: return style(go.Figure(), 300, "FPTK by Directorate")
    x = summary.head(10).sort_values("Total")
    fig = px.bar(x, x="Total", y="Directorate", orientation="h", text="Total")
    fig.update_traces(marker_color=BLUE, textposition="outside", marker_line_width=0)
    fig.update_layout(showlegend=False)
    return style(fig, 310, "FPTK by Directorate")


def recruiter_chart(summary):
    if summary is None or summary.empty: return style(go.Figure(), 300, "Recruiter Workload")
    x = summary.head(10).sort_values("Open")
    fig = px.bar(x, x="Open", y="Recruiter", orientation="h", text="Open")
    fig.update_traces(marker_color=TEAL, textposition="outside", marker_line_width=0)
    fig.update_layout(showlegend=False)
    return style(fig, 310, "Open FPTK by Recruiter")


def weekly_chart(summary):
    if summary is None or summary.empty: return style(go.Figure(), 300, "Weekly FPTK Trend")
    fig = px.line(summary, x="Week", y=["FPTK Processed", "Closed"], markers=True,
                  color_discrete_map={"FPTK Processed":BLUE,"Closed":TEAL})
    fig.update_traces(line=dict(width=2.5))
    return style(fig, 300, "FPTK Inflow vs Closure")


def funnel_chart(summary):
    if summary is None or summary.empty: return style(go.Figure(), 360, "Recruitment Funnel")
    x = summary.copy()
    fig = go.Figure(go.Funnel(
        y=x["Stage"], x=x["Count"], textinfo="value+percent initial",
        marker=dict(color=[BLUE,TEAL,GREEN,ORANGE,PURPLE,RED]))
    )
    return style(fig, 390, "Recruitment Funnel")


def aging_chart(summary):
    if summary is None or summary.empty: return style(go.Figure(), 300, "Open FPTK Aging")
    x = summary.copy()
    colors = [GREEN,TEAL,BLUE,ORANGE,RED][:len(x)]
    fig = px.bar(x, x="Aging", y="Open", text="Open", color="Aging", color_discrete_sequence=colors)
    fig.update_traces(textposition="outside", marker_line_width=0)
    fig.update_layout(showlegend=False)
    return style(fig, 300, "Open FPTK Aging")
