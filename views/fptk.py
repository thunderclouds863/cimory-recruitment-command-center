from __future__ import annotations
from datetime import timedelta
import re
import streamlit as st
from sqlalchemy import select

from core.db import session_scope
from core.models import FPTK, SourceOwnership
from core.compile_rules import BUSINESS_UNITS, DIRECTORATES, REQUEST_REASONS, CATEGORIES, STATUSES, REASON_TO_CATEGORY, key_text
from core.compile_engine import _sla_days, _sla_result
from core.audit import write_audit


def render(user):
    st.header("FPTK Database")
    st.caption("Semua user dapat melihat Central Master. Edit hanya bisa dilakukan oleh source owner atau Admin.")

    with session_scope() as s:
        rows = s.execute(
            select(FPTK, SourceOwnership)
            .outerjoin(SourceOwnership, (SourceOwnership.entity_type == "FPTK") & (SourceOwnership.entity_id == FPTK.id))
            .order_by(FPTK.updated_at.desc())
        ).all()

    data = []
    for f, own in rows:
        can_edit = user.get("role") == "admin" or (own and own.owner_user_id == user.get("id"))
        data.append({
            "ID": f.id,
            "Kode Unik": f.kode_unik,
            "FPTK Date": f.fptk_date,
            "Position": f.position,
            "Business Unit": f.business_unit,
            "Directorate": f.directorate,
            "Division": f.division,
            "Department": f.department,
            "Level": f.level_fptk,
            "PIC Recruiter": f.pic_recruiter,
            "Vacancy": f.vacancy,
            "Status": f.status,
            "SLA": f.sla_result,
            "Source Owner": (own.owner_name or own.owner_email) if own else "Legacy / belum diklaim",
            "Access": "EDIT" if can_edit else "VIEW ONLY",
        })
    st.dataframe(data, use_container_width=True, hide_index=True, height=600)

    editable = [(f, own) for f, own in rows if user.get("role") == "admin" or (own and own.owner_user_id == user.get("id"))]
    if editable:
        with st.expander("✏ Edit FPTK yang saya miliki", expanded=False):
            options = {f"{f.kode_unik} | {f.position}": f.id for f, _ in editable}
            label = st.selectbox("Pilih FPTK", list(options))
            fid = options[label]
            with session_scope() as s:
                f = s.get(FPTK, fid)
                snapshot = {k: getattr(f, k) for k in [
                    "business_unit","directorate","division","department","level_fptk","level_number",
                    "request_reason","category_fptk","pic_recruiter","vacancy","status","cancel_date",
                    "offering_date","remarks","fptk_date"
                ]}
                identity = (f.kode_unik, f.position, f.fptk_date)
            st.caption(f"Identity dikunci: **{identity[0]}** · {identity[1]} · {identity[2] or '-'}")
            with st.form(f"owned_fptk_{fid}"):
                c1, c2 = st.columns(2)
                bu = c1.selectbox("Business Unit", BUSINESS_UNITS, index=BUSINESS_UNITS.index(snapshot["business_unit"]) if snapshot["business_unit"] in BUSINESS_UNITS else 0)
                direct = c2.selectbox("Direktorat", DIRECTORATES, index=DIRECTORATES.index(snapshot["directorate"]) if snapshot["directorate"] in DIRECTORATES else 0)
                c1, c2 = st.columns(2)
                div = c1.text_input("Divisi", snapshot["division"] or "")
                dep = c2.text_input("Department", snapshot["department"] or "")
                c1, c2 = st.columns(2)
                level = c1.text_input("Level FPTK", snapshot["level_fptk"] or "")
                level_no = c2.number_input("Level Number", 1, 5, int(snapshot["level_number"] or 1))
                c1, c2 = st.columns(2)
                reason = c1.selectbox("Alasan Permintaan FPTK", REQUEST_REASONS, index=REQUEST_REASONS.index(snapshot["request_reason"]) if snapshot["request_reason"] in REQUEST_REASONS else 0)
                expected_cat = REASON_TO_CATEGORY[key_text(reason)]
                category = c2.selectbox("Category FPTK", CATEGORIES, index=CATEGORIES.index(snapshot["category_fptk"]) if snapshot["category_fptk"] in CATEGORIES else CATEGORIES.index(expected_cat))
                c1, c2, c3 = st.columns(3)
                pic = c1.text_input("PIC Recruiter", snapshot["pic_recruiter"] or "")
                vacancy = c2.number_input("Vacancy", 1, 999, int(snapshot["vacancy"] or 1))
                status = c3.selectbox("Status", STATUSES, index=STATUSES.index(snapshot["status"]) if snapshot["status"] in STATUSES else 0)
                c1, c2 = st.columns(2)
                cancel = c1.date_input("FPTK Cancel Date", value=snapshot["cancel_date"])
                offering = c2.date_input("Offering Date", value=snapshot["offering_date"])
                remarks = st.text_area("Remarks", snapshot["remarks"] or "")
                save = st.form_submit_button("Simpan perubahan", type="primary", use_container_width=True)
            if save:
                errs = []
                level = level.strip().upper()
                if not re.fullmatch(r"[1-5][A-Z]", level):
                    errs.append("Level FPTK harus format 1A/2B/3A/dst.")
                elif int(level[0]) != int(level_no):
                    errs.append("Level Number harus sama dengan angka Level FPTK.")
                if category != expected_cat:
                    errs.append(f"Alasan {reason} harus Category {expected_cat}.")
                if status == "Cancel" and not cancel:
                    errs.append("Status Cancel wajib FPTK Cancel Date.")
                if status == "Closed" and not offering:
                    errs.append("Status Closed wajib Offering Date.")
                if errs:
                    for e in errs:
                        st.error(e)
                else:
                    with session_scope() as s:
                        f = s.get(FPTK, fid)
                        own = s.scalar(select(SourceOwnership).where(SourceOwnership.entity_type == "FPTK", SourceOwnership.entity_id == fid))
                        if user.get("role") != "admin" and (not own or own.owner_user_id != user.get("id")):
                            raise PermissionError("Data ini bukan milik source account kamu.")
                        f.business_unit = bu
                        f.directorate = direct
                        f.division = div.strip()
                        f.department = dep.strip()
                        f.level_fptk = level
                        f.level_number = int(level_no)
                        f.request_reason = reason
                        f.category_fptk = category
                        f.pic_recruiter = pic.strip()
                        f.vacancy = int(vacancy)
                        f.status = status
                        f.cancel_date = cancel
                        f.offering_date = offering
                        f.remarks = remarks.strip() or None
                        days = _sla_days(level)
                        f.sla_days = days
                        f.deadline_sla = f.fptk_date + timedelta(days=days) if f.fptk_date else None
                        f.sla_result = _sla_result(status, f.deadline_sla, offering)
                    write_audit(user.get("email"), "UPDATE_FPTK", "FPTK", fid, label)
                    st.success("FPTK berhasil diperbarui.")
                    st.rerun()

    st.divider()
    st.info("**Proses FPTK / input langsung** masih di-hold sesuai scope sekarang. Fokus aktif saat ini adalah Upload & Compile dari file Excel dengan validation ketat.")
