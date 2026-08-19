from datetime import date
import streamlit as st
from sqlalchemy import select
from core.db import session_scope
from core.models import FPTK, Candidate, Application, Blacklist, PipelineEvent, SourceOwnership
from core.logic import derive_recruitment_model
from core.cv_parser import extract_pdf_text, parse_candidate_text
from core.audit import write_audit


def render(user):
    st.header("Candidate & CV")
    st.caption("Candidate database dapat dilihat semua user. Input/edit application hanya untuk FPTK milik source account atau Admin.")
    t1, t2 = st.tabs(["Candidate Database", "+ Input Candidate"])
    with t1:
        with session_scope() as s:
            c = s.scalars(select(Candidate).order_by(Candidate.created_at.desc())).all()
            data = [{"ID": x.id, "Name": x.name, "Email": x.email, "Phone": x.phone, "Domicile": x.domicile, "Last Company": x.last_company, "Last Position": x.last_position, "FMCG": x.fmcg_experience} for x in c]
        st.dataframe(data, use_container_width=True, hide_index=True, height=560)
    with t2:
        with session_scope() as s:
            q = select(FPTK, SourceOwnership).join(
                SourceOwnership,
                (SourceOwnership.entity_type == "FPTK") & (SourceOwnership.entity_id == FPTK.id),
            ).where(FPTK.status == "OP").order_by(FPTK.fptk_date)
            if user.get("role") != "admin":
                q = q.where(SourceOwnership.owner_user_id == user.get("id"))
            fptk_rows = s.execute(q).all()
        fptks = [x[0] for x in fptk_rows]
        if not fptks:
            st.info("Belum ada FPTK Open yang menjadi milik source account ini.")
            return
        options = {f"{f.kode_unik} | {f.position}": f.id for f in fptks}
        fsel = st.selectbox("Link to FPTK", list(options))
        uploaded = st.file_uploader("Upload CV PDF (optional)", type=["pdf"])
        pasted = st.text_area("Atau paste CV / LinkedIn / JobStreet text", height=180)
        parsed = {}
        if uploaded:
            try:
                parsed = parse_candidate_text(extract_pdf_text(uploaded.getvalue()))
            except Exception as e:
                st.warning(f"PDF extraction gagal: {e}")
        elif pasted:
            parsed = parse_candidate_text(pasted)
        with st.form("candidate_form"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Name *", parsed.get("name", ""))
            email = c2.text_input("Email", parsed.get("email", ""))
            phone = c3.text_input("Phone", parsed.get("phone", ""))
            c1, c2, c3 = st.columns(3)
            dom = c1.text_input("Domicile")
            edu = c2.text_input("Education Level")
            major = c3.text_input("Major")
            c1, c2, c3 = st.columns(3)
            uni = c1.text_input("University")
            gpa = c2.number_input("GPA", 0.0, 4.0, float(parsed.get("gpa") or 0.0), step=.01)
            fmcg = c3.checkbox("FMCG experience")
            c1, c2 = st.columns(2)
            lastco = c1.text_input("Last Company")
            lastpos = c2.text_input("Last Position")
            submit = st.form_submit_button("Save Candidate & Application", use_container_width=True)
        if submit:
            if not name:
                st.error("Name wajib.")
                return
            with session_scope() as s:
                f = s.get(FPTK, options[fsel])
                own = s.scalar(select(SourceOwnership).where(SourceOwnership.entity_type == "FPTK", SourceOwnership.entity_id == f.id))
                if user.get("role") != "admin" and (not own or own.owner_user_id != user.get("id")):
                    raise PermissionError("FPTK ini bukan milik source account kamu.")
                bl = s.scalar(select(Blacklist).where(Blacklist.active == True, Blacklist.candidate_name == name))
                if bl:
                    st.error(f"Candidate terdaftar blacklist: {bl.reason}")
                    return
                c = s.scalar(select(Candidate).where(Candidate.email == email)) if email else None
                if not c:
                    c = Candidate(name=name, email=email or None, phone=phone or None, domicile=dom, education_level=edu, major=major, university_other=uni, gpa=gpa or None, last_company=lastco, last_position=lastpos, fmcg_experience=fmcg, raw_cv_text=(parsed.get("raw_text") or pasted), cv_filename=(uploaded.name if uploaded else None))
                    s.add(c)
                    s.flush()
                a = s.scalar(select(Application).where(Application.fptk_id == f.id, Application.candidate_id == c.id))
                if not a:
                    a = Application(fptk_id=f.id, candidate_id=c.id, recruiter=f.pic_recruiter, model=derive_recruitment_model(f.position, f.level_fptk, f.filter_category), current_stage="Sourcing HR")
                    s.add(a)
                    s.flush()
                    s.add(PipelineEvent(application_id=a.id, stage="Sourcing HR", result="SOURCED", event_date=date.today(), created_by=user["email"]))
                app_own = s.scalar(select(SourceOwnership).where(SourceOwnership.entity_type == "Application", SourceOwnership.entity_id == a.id))
                if app_own is None:
                    s.add(SourceOwnership(entity_type="Application", entity_id=a.id, owner_user_id=user.get("id"), owner_email=user.get("email"), owner_name=user.get("display_name"), source_file="WEB", source_sheet="Candidate & CV"))
                aid = a.id
            write_audit(user["email"], "CREATE_CANDIDATE_APPLICATION", "Application", aid, fsel)
            st.success("Candidate saved and linked to FPTK.")
            st.rerun()
