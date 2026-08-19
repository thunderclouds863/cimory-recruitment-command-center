from datetime import date
import streamlit as st
from sqlalchemy import select
from core.db import session_scope
from core.models import Application, Candidate, FPTK, PipelineEvent, SourceOwnership
from core.logic import FLOW_MAP
from core.audit import write_audit


def render(user):
    st.header("Candidate Pipeline")
    with session_scope() as s:
        q = select(Application, Candidate, FPTK, SourceOwnership).join(Candidate, Candidate.id == Application.candidate_id).join(FPTK, FPTK.id == Application.fptk_id).outerjoin(
            SourceOwnership,
            (SourceOwnership.entity_type == "Application") & (SourceOwnership.entity_id == Application.id),
        ).where(Application.status == "ACTIVE")
        rows = s.execute(q).all()
    if not rows:
        st.info("Belum ada application aktif.")
        return
    labels = {f"{c.name} | {f.position} | {f.kode_unik}": a.id for a, c, f, o in rows}
    sel = st.selectbox("Candidate / FPTK", list(labels))
    aid = labels[sel]
    a, c, f, own = next(x for x in rows if x[0].id == aid)
    can_edit = user.get("role") == "admin" or (own and own.owner_user_id == user.get("id"))
    flow = FLOW_MAP.get(a.model, FLOW_MAP["Model 1"])
    st.caption(f"Model: {a.model} · Recruiter: {a.recruiter} · Current: {a.current_stage or '-'} · Access: {'EDIT' if can_edit else 'VIEW ONLY'}")
    with session_scope() as s:
        events = s.scalars(select(PipelineEvent).where(PipelineEvent.application_id == aid).order_by(PipelineEvent.event_date, PipelineEvent.id)).all()
    done = {e.stage: e for e in events}
    cols = st.columns(min(max(len(flow), 1), 6))
    for i, stage in enumerate(flow):
        e = done.get(stage)
        cols[i % len(cols)].markdown(f"**{'✅' if e else '○'} {stage}**  \n{(e.result or '') if e else ''}")
    if not can_edit:
        st.info("Data ini berasal dari file user lain, jadi hanya dapat dilihat.")
        return
    with st.form("advance"):
        stage = st.selectbox("Stage", flow, index=min(flow.index(a.current_stage) if a.current_stage in flow else 0, len(flow) - 1))
        result = st.selectbox("Result", ["LOLOS", "KEEP", "DROP", "WITHDRAW", "PENDING", "DONE"])
        edate = st.date_input("Date", date.today())
        detail = st.text_area("Detail / Notes")
        submit = st.form_submit_button("Save stage update", use_container_width=True)
    if submit:
        with session_scope() as s:
            aa = s.get(Application, aid)
            own2 = s.scalar(select(SourceOwnership).where(SourceOwnership.entity_type == "Application", SourceOwnership.entity_id == aid))
            if user.get("role") != "admin" and (not own2 or own2.owner_user_id != user.get("id")):
                raise PermissionError("Application ini bukan milik source account kamu.")
            s.add(PipelineEvent(application_id=aid, stage=stage, result=result, detail=detail, event_date=edate, created_by=user["email"]))
            aa.current_stage = stage
            if result in ("DROP", "WITHDRAW"):
                aa.status = result
        write_audit(user["email"], "PIPELINE_UPDATE", "Application", aid, f"{stage}: {result}")
        st.success("Pipeline updated")
        st.rerun()
