import streamlit as st
from core.metrics import fptk_dataframe, kpis, category_summary, recruiter_summary, directorate_summary, weekly_trend, aging_summary, funnel_summary
from core.charts import show_chart, status_chart, directorate_chart, recruiter_chart, weekly_chart, funnel_chart, aging_chart

def render(user):
    st.header("Recruitment Command Center")
    df=fptk_dataframe(user)
    if df.empty:
        st.info("Belum ada data. Admin dapat import MASTER_COMPILE/DB_FPTK_TEMPLATE atau jalankan demo seed.")
        return
    with st.expander("Global filters",expanded=False):
        c1,c2,c3,c4=st.columns(4)
        dirs=c1.multiselect("Directorate",sorted([x for x in df.directorate.dropna().unique()]))
        recs=c2.multiselect("Recruiter",sorted([x for x in df.pic_recruiter.dropna().unique()]))
        levels=c3.multiselect("Level",sorted([x for x in df.level_fptk.dropna().unique()]))
        stats=c4.multiselect("Status",sorted([x for x in df.status.dropna().unique()]))
        if dirs:df=df[df.directorate.isin(dirs)]
        if recs:df=df[df.pic_recruiter.isin(recs)]
        if levels:df=df[df.level_fptk.isin(levels)]
        if stats:df=df[df.status.isin(stats)]
    m=kpis(df); cols=st.columns(7)
    for col,(lab,val) in zip(cols,[('Total FPTK',m['total']),('Open',m['open']),('Closed',m['closed']),('Cancel',m['cancel']),('Fill Rate',f"{m['fill_rate']:.1f}%"),('Closed SLA',f"{m['closed_sla']:.1f}%"),('Over SLA',m['over_sla'])]): col.metric(lab,val)
    c1,c2=st.columns([1,1.35]);
    with c1: show_chart(status_chart(df),"status")
    with c2: show_chart(directorate_chart(directorate_summary(df)),"directorate")
    c1,c2=st.columns(2)
    with c1: show_chart(recruiter_chart(recruiter_summary(df)),"recruiter")
    with c2: show_chart(aging_chart(aging_summary(df)),"aging")
    show_chart(weekly_chart(weekly_trend(df)),"weekly")
    show_chart(funnel_chart(funnel_summary(user)),"funnel")
    st.subheader("Executive summary by category"); st.dataframe(category_summary(df),use_container_width=True,hide_index=True)
