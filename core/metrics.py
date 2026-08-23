from __future__ import annotations
from datetime import date
import pandas as pd
from sqlalchemy import select
from .db import session_scope
from .models import FPTK, Application, PipelineEvent, Candidate

FPTK_COLUMNS = [
    "id","kode_unik","position","business_unit","directorate","division","department","level_fptk","filter_category",
    "pic_recruiter","status","fptk_date","cancel_date","offering_date","vacancy","deadline_sla","sla_result","region","new_replacement"
]


def fptk_dataframe(user=None) -> pd.DataFrame:
    with session_scope() as s:
        q = select(FPTK)
        rows = s.scalars(q).all()
        data = [{c:getattr(r,c) for c in FPTK_COLUMNS} for r in rows]
    df = pd.DataFrame(data, columns=FPTK_COLUMNS)
    if not df.empty:
        for c in ["fptk_date","cancel_date","offering_date","deadline_sla"]: df[c]=pd.to_datetime(df[c], errors='coerce')
    return df


def application_dataframe(user=None) -> pd.DataFrame:
    with session_scope() as s:
        q = select(Application, Candidate, FPTK).join(Candidate, Candidate.id==Application.candidate_id).join(FPTK,FPTK.id==Application.fptk_id)
        rows=s.execute(q).all()
        data=[]
        for a,c,f in rows:
            data.append({
                "application_id":a.id,
                "candidate":c.name,
                "position":f.position,
                "kode_unik":f.kode_unik,
                "recruiter":a.recruiter,
                "model":a.model,
                "current_stage":a.current_stage,
                "application_created_at":a.created_at
            })
    return pd.DataFrame(data)


def pipeline_event_dataframe(user=None) -> pd.DataFrame:
    """
    Returns pipeline events joined with their application and fptk identifiers.
    Columns: application_id, stage, result, event_date, kode_unik, position, recruiter
    """
    with session_scope() as s:
        q=select(PipelineEvent, Application, FPTK).join(Application, Application.id==PipelineEvent.application_id).join(FPTK, FPTK.id==Application.fptk_id)
        rows = s.execute(q).all()
        data=[]
        for e,a,f in rows:
            data.append({
                "application_id": e.application_id,
                "stage": e.stage,
                "result": e.result,
                "event_date": e.event_date,
                "kode_unik": f.kode_unik,
                "position": f.position,
                "recruiter": a.recruiter
            })
    df = pd.DataFrame(data)
    if not df.empty:
        df["event_date"] = pd.to_datetime(df["event_date"], errors='coerce')
    return df


def apply_filters(df, filters):
    out=df.copy()
    for col, vals in filters.items():
        if vals and col in out.columns: out=out[out[col].fillna("").isin(vals)]
    return out


def kpis(df):
    if df.empty: return {"total":0,"open":0,"closed":0,"cancel":0,"fill_rate":0.0,"closed_sla":0.0,"over_sla":0}
    total=len(df); op=(df.status=="OP").sum(); closed=(df.status=="Closed").sum(); cancel=(df.status=="Cancel").sum()
    denom=max(total-cancel,1); fill=closed/denom*100
    closed_df=df[df.status=="Closed"]
    closed_sla=(closed_df.sla_result.fillna("").str.lower().eq("closed lulus sla").sum()/max(len(closed_df),1)*100) if len(closed_df) else 0
    today=pd.Timestamp(date.today()); over=((df.status=="OP") & df.deadline_sla.notna() & (df.deadline_sla<today)).sum()
    return {"total":int(total),"open":int(op),"closed":int(closed),"cancel":int(cancel),"fill_rate":fill,"closed_sla":closed_sla,"over_sla":int(over)}


def period_kpis(df, days=7):
    """
    Compute KPI values for the most recent `days` and the previous period of same length.
    Returns dict with 'current' and 'previous' KPI dicts and pct change fields.
    """
    if df.empty:
        empty = {"total":0,"open":0,"closed":0,"cancel":0}
        return {"current":empty, "previous":empty, "change":{}}
    today = pd.Timestamp.today().normalize()
    cur_start = today - pd.Timedelta(days=days-1)
    prev_start = cur_start - pd.Timedelta(days=days)
    prev_end = cur_start - pd.Timedelta(days=1)
    cur_df = df[df.fptk_date.notna() & (df.fptk_date >= cur_start) & (df.fptk_date <= today)]
    prev_df = df[df.fptk_date.notna() & (df.fptk_date >= prev_start) & (df.fptk_date <= prev_end)]
    cur = kpis(cur_df)
    prev = kpis(prev_df)
    change = {}
    for k in ["total","open","closed","fill_rate","over_sla"]:
        prev_v = prev.get(k,0) or 0.0
        cur_v = cur.get(k,0) or 0.0
        if prev_v==0:
            pct = None
        else:
            try:
                pct = (cur_v - prev_v)/abs(prev_v)*100
            except Exception:
                pct = None
        change[k] = pct
    return {"current":cur, "previous":prev, "change":change}


def category_summary(df):
    if df.empty:return pd.DataFrame(columns=["Category","FPTK","Open","Closed","Cancel","Fill Rate","Closed sesuai SLA"])
    x=df.assign(Category=df.filter_category.fillna("Uncategorized"))
    rows=[]
    for cat,g in x.groupby("Category",dropna=False):
        m=kpis(g); rows.append({"Category":cat,"FPTK":m["total"],"Open":m["open"],"Closed":m["closed"],"Cancel":m["cancel"],"Fill Rate":m["fill_rate"],"Closed sesuai SLA":m["closed_sla"]})
    return pd.DataFrame(rows).sort_values("FPTK",ascending=False)


def recruiter_summary(df):
    if df.empty:return pd.DataFrame(columns=["Recruiter","Total","Open","Closed","Cancel","Over SLA"])
    rows=[]
    for name,g in df.assign(pic_recruiter=df.pic_recruiter.fillna("Belum Ada PIC")).groupby("pic_recruiter"):
        m=kpis(g); rows.append({"Recruiter":name,"Total":m["total"],"Open":m["open"],"Closed":m["closed"],"Cancel":m["cancel"],"Over SLA":m["over_sla"],"Fill Rate":m["fill_rate"]})
    return pd.DataFrame(rows).sort_values(["Open","Total"],ascending=False)


def directorate_summary(df):
    if df.empty:return pd.DataFrame(columns=["Directorate","Total","Open","Closed"])
    x=df.assign(directorate=df.directorate.fillna("Unmapped"))
    return x.groupby("directorate").agg(Total=("id","count"),Open=("status",lambda s:(s=="OP").sum()),Closed=("status",lambda s:(s=="Closed").sum())).reset_index().rename(columns={"directorate":"Directorate"}).sort_values("Total",ascending=False)


def weekly_trend(df):
    if df.empty:return pd.DataFrame(columns=["Week","FPTK Processed","Closed"])
    x=df.copy(); x["FPTK Processed"]=1; x["ClosedFlag"]=(x.status=="Closed").astype(int)
    wk=x.fptk_date.dt.isocalendar(); x["YearWeek"]=wk.year.astype(str)+"-W"+wk.week.astype(str).str.zfill(2)
    return x.dropna(subset=["fptk_date"]).groupby("YearWeek").agg(**{"FPTK Processed":("FPTK Processed","sum"),"Closed":("ClosedFlag","sum")}).reset_index().rename(columns={"YearWeek":"Week"}).sort_values("Week")


def aging_summary(df):
    if df.empty:return pd.DataFrame(columns=["Aging","Open"])
    x=df[df.status=="OP"].copy(); x["days"]=(pd.Timestamp(date.today())-x.fptk_date).dt.days
    bins=[-1,30,60,90,120,10**6]; labels=["0-30","31-60","61-90","91-120",">120"]
    x["Aging"]=pd.cut(x.days,bins=bins,labels=labels)
    return x.groupby("Aging",observed=False).size().reset_index(name="Open")


def funnel_summary(user=None):
    ev=pipeline_event_dataframe(user)
    if ev.empty:return pd.DataFrame(columns=["Stage","Count"])
    passed={"OK","LOLOS","PASS","PASSED","KEEP","ACCEPTED","DONE","TERPAKAI","1","YES","YA"}
    ev["ok"]=ev.result.fillna("").str.upper().isin(passed) | ev.result.isna()
    # Count unique applications that passed each stage
    out = ev[ev.ok].groupby("stage")["application_id"].nunique().reset_index(name="Count").rename(columns={"stage":"Stage"})
    # Keep original ordering if available by event timestamp
    stage_order = ev.drop_duplicates("stage").sort_values("event_date").stage.tolist()
    if stage_order:
        out["Stage"] = pd.Categorical(out["Stage"], categories=stage_order, ordered=True)
        out = out.sort_values("Stage")
    return out


def time_to_fill_summary(df):
    """
    Compute time-to-fill (days) for closed FPTKs using offering_date - fptk_date.
    Returns dataframe with Week, avg_days, median_days
    """
    if df.empty: return pd.DataFrame(columns=["Week","avg_days","median_days"]) 
    closed = df[(df.status=="Closed") & df.offering_date.notna() & df.fptk_date.notna()].copy()
    if closed.empty: return pd.DataFrame(columns=["Week","avg_days","median_days"]) 
    closed["days_to_fill"] = (closed.offering_date - closed.fptk_date).dt.days
    wk = closed.fptk_date.dt.isocalendar()
    closed["YearWeek"] = wk.year.astype(str) + "-W" + wk.week.astype(str).str.zfill(2)
    out = closed.groupby("YearWeek").agg(avg_days=("days_to_fill","mean"), median_days=("days_to_fill","median"))
    out = out.reset_index().rename(columns={"YearWeek":"Week"}).sort_values("Week")
    return out


