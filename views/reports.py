from datetime import date
import streamlit as st
from core.metrics import fptk_dataframe
from exports.excel_export import build_master_compile_xlsx
from exports.ppt_export import build_ceo_update_pptx

def render(user):
    st.header("Reports & Export")
    st.write("Semua output memakai data dan calculation layer yang sama dengan dashboard, supaya angka Excel, web, dan PowerPoint konsisten.")
    df=fptk_dataframe(user)
    c1,c2=st.columns(2)
    with c1:
        if st.button("Generate Master Compile Excel",use_container_width=True):
            with st.spinner("Building workbook..."): st.session_state['master_xlsx']=build_master_compile_xlsx(user)
        if 'master_xlsx' in st.session_state: st.download_button("Download MASTER_COMPILE_FPTK.xlsx",st.session_state['master_xlsx'],file_name=f"MASTER_COMPILE_FPTK_{date.today():%Y%m%d}.xlsx",mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
    with c2:
        if st.button("Generate CEO Update PPT",use_container_width=True):
            with st.spinner("Building PowerPoint..."): st.session_state['ceo_ppt']=build_ceo_update_pptx(df,user,title_date=date.today().strftime("%d.%m.%y"))
        if 'ceo_ppt' in st.session_state: st.download_button("Download CEO UPDATE.pptx",st.session_state['ceo_ppt'],file_name=f"CEO_UPDATE_{date.today():%Y%m%d}.pptx",mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",use_container_width=True)
    st.subheader("Export design")
    st.markdown("- **Master Compile:** FPTK, DB Sourcing, Candidate Master, Funneling, Recruiter Performance, Mapping FPTK Recruiter, Grafik MPP, Log DB Sourcing.\n- **CEO Update:** executive summary, category summary, directorate, recruiter workload, funnel, aging/SLA risk, weekly trend, Manager, Level 3, Level 2C Below, STO, CLAP/FGDP.")
