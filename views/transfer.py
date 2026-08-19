from datetime import datetime
import uuid
import streamlit as st
from sqlalchemy import select
from core.db import session_scope
from core.models import FPTK, User, TransferHistory
from core.audit import write_audit

def render(user):
    st.header("Transfer FPTK")
    with session_scope() as s:
        q=select(FPTK).where(FPTK.status=="OP")
        if user['role']=='recruiter':q=q.where(FPTK.pic_recruiter==user.get('recruiter_name'))
        fptks=s.scalars(q).all(); recs=s.scalars(select(User).where(User.active==True,User.recruiter_name.is_not(None))).all()
    if not fptks: st.info("Tidak ada FPTK open yang dapat ditransfer."); return
    fm={f"{f.kode_unik} | {f.position} | {f.pic_recruiter}":f.id for f in fptks}; rm={f"{r.display_name} ({r.recruiter_name})":r.recruiter_name for r in recs}; sel=st.selectbox("FPTK",list(fm)); to=st.selectbox("Transfer to",list(rm)); reason=st.text_area("Reason / handover note")
    if st.button("Transfer FPTK",use_container_width=True):
        with session_scope() as s:
            f=s.get(FPTK,fm[sel]); old=f.pic_recruiter or "Belum Ada PIC"; new=rm[to]; f.pic_recruiter=new; tid=f"TRF-{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6].upper()}"; s.add(TransferHistory(transfer_id=tid,fptk_id=f.id,transfer_from=old,transfer_to=new,reason=reason,status="TRANSFERRED",transferred_by=user['email']))
        write_audit(user['email'],'TRANSFER_FPTK','FPTK',fm[sel],f"{old} -> {new}"); st.success(f"Transferred: {old} → {new}"); st.rerun()
    with session_scope() as s:
        hist=s.scalars(select(TransferHistory).order_by(TransferHistory.transferred_at.desc()).limit(100)).all(); st.dataframe([{"Transfer ID":h.transfer_id,"Date":h.transferred_at,"From":h.transfer_from,"To":h.transfer_to,"Reason":h.reason,"Status":h.status} for h in hist],use_container_width=True,hide_index=True)
