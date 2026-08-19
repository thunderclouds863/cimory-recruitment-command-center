from __future__ import annotations
from io import BytesIO
import pandas as pd
from core.metrics import fptk_dataframe, application_dataframe, pipeline_event_dataframe, recruiter_summary, category_summary, weekly_trend
from core.db import session_scope
from core.models import Candidate
from sqlalchemy import select

FPTK_EXPORT_ORDER = ["kode_unik","position","business_unit","directorate","division","department","level_fptk","filter_category","pic_recruiter","status","fptk_date","cancel_date","offering_date","vacancy","deadline_sla","sla_result","region","new_replacement"]

def _funneling(user=None):
    apps=application_dataframe(user); ev=pipeline_event_dataframe(user)
    if apps.empty:return apps
    if ev.empty:return apps
    piv=ev.assign(v=1).pivot_table(index="application_id",columns="stage",values="v",aggfunc="sum",fill_value=0).reset_index()
    return apps.merge(piv,on="application_id",how="left")

def build_master_compile_xlsx(user=None) -> bytes:
    f=fptk_dataframe(user); apps=application_dataframe(user); events=pipeline_event_dataframe(user); fun=_funneling(user)
    with session_scope() as s:
        cands=s.scalars(select(Candidate)).all()
        cand=pd.DataFrame([{"Nama":c.name,"Email":c.email,"Nomor HP":c.phone,"Domisili":c.domicile,"Jenjang Pendidikan":c.education_level,"Jurusan":c.major,"IPK":c.gpa,"Last Position":c.last_position,"Last Company":c.last_company,"Pernah di FMCG?":c.fmcg_experience} for c in cands])
    out=BytesIO()
    with pd.ExcelWriter(out,engine="xlsxwriter",datetime_format="dd-mmm-yyyy") as writer:
        wb=writer.book; header_fmt=wb.add_format({"bold":True,"bg_color":"#27358F","font_color":"#FFFFFF","border":1,"align":"center","valign":"vcenter"}); pct=wb.add_format({"num_format":"0.00%"})
        f.to_excel(writer,sheet_name="FPTK",index=False)
        apps.to_excel(writer,sheet_name="DB Sourcing",index=False)
        cand.to_excel(writer,sheet_name="Candidate Master",index=False)
        fun.to_excel(writer,sheet_name="Funneling",index=False)
        recruiter_summary(f).to_excel(writer,sheet_name="Recruiter Performance",index=False)
        category_summary(f).to_excel(writer,sheet_name="Mapping FPTK Recruiter",index=False)
        weekly_trend(f).to_excel(writer,sheet_name="Grafik MPP",index=False)
        events.to_excel(writer,sheet_name="Log DB Sourcing",index=False)
        for name in writer.sheets:
            ws=writer.sheets[name]; ws.freeze_panes(1,0); ws.autofilter(0,0,max(0,writer.sheets[name].dim_rowmax),max(0,writer.sheets[name].dim_colmax))
            ws.set_row(0,28,header_fmt); ws.set_column(0,60,18)
    return out.getvalue()
