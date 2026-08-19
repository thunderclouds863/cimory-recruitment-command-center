from __future__ import annotations
import base64
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

BLUE="#27358F"; RED="#EF233C"

def show_chart(fig, key: str, copyable=True):
    fig.update_layout(margin=dict(l=15,r=15,t=55,b=20), font=dict(family="Raleway, Arial",size=12), paper_bgcolor="white", plot_bgcolor="white")
    st.plotly_chart(fig, use_container_width=True, config={"displaylogo":False,"toImageButtonOptions":{"format":"png","scale":2}})
    if not copyable: return
    try:
        png=fig.to_image(format="png",scale=2)
        c1,c2=st.columns(2)
        c1.download_button("Download PNG", png, file_name=f"{key}.png", mime="image/png", key=f"dl_{key}", use_container_width=True)
        b64=base64.b64encode(png).decode()
        html=f"""
        <button id='copy_{key}' style='width:100%;padding:8px 12px;border:1px solid #d0d5dd;border-radius:8px;background:white;cursor:pointer'>Copy PNG to clipboard</button>
        <script>
        document.getElementById('copy_{key}').onclick=async()=>{{
          try{{const r=await fetch('data:image/png;base64,{b64}');const blob=await r.blob();await navigator.clipboard.write([new ClipboardItem({{'image/png':blob}})]);document.getElementById('copy_{key}').innerText='Copied ✓';}}
          catch(e){{document.getElementById('copy_{key}').innerText='Clipboard blocked — use Download PNG';}}
        }};
        </script>"""
        with c2: components.html(html,height=46)
    except Exception:
        st.caption("PNG export membutuhkan package `kaleido`; Plotly modebar tetap bisa Download PNG.")

def status_chart(df):
    x=df.status.value_counts().rename_axis("Status").reset_index(name="Count")
    return px.pie(x,names="Status",values="Count",hole=.62,title="FPTK Status")

def directorate_chart(summary):
    return px.bar(summary.head(15).sort_values("Total"),x="Total",y="Directorate",orientation="h",title="FPTK by Directorate")

def recruiter_chart(summary):
    return px.bar(summary.head(15).sort_values("Open"),x="Open",y="Recruiter",orientation="h",title="Open FPTK by Recruiter")

def weekly_chart(summary):
    return px.line(summary,x="Week",y=["FPTK Processed","Closed"],markers=True,title="Weekly FPTK Inflow vs Closure")

def funnel_chart(summary):
    if summary.empty: return go.Figure().update_layout(title="Recruitment Funnel")
    x=summary.sort_values("Count",ascending=False)
    return go.Figure(go.Funnel(y=x.Stage,x=x.Count)).update_layout(title="Recruitment Funnel")

def aging_chart(summary):
    return px.bar(summary,x="Aging",y="Open",title="Open FPTK Aging")
