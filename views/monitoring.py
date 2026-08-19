from datetime import date
import streamlit as st
import pandas as pd
from sqlalchemy import select, func

from core.db import session_scope
from core.models import FPTK, Application, PipelineEvent, Evidence, UnlinkedSourcing
from core.metrics import fptk_dataframe, funnel_summary
from core.compile_engine import resolve_unlinked_sourcing


def _unlinked_rows():
    with session_scope() as s:
        items = s.scalars(
            select(UnlinkedSourcing)
            .where(UnlinkedSourcing.status == "UNLINKED")
            .order_by(UnlinkedSourcing.created_at.desc())
        ).all()
        return [
            {
                "ID": x.id,
                "Kode Unik": x.kode_unik,
                "Candidate": x.candidate_name,
                "Position": x.position,
                "Recruiter": x.recruiter,
                "Sourcing Date": x.sourcing_date,
                "Owner": x.owner_name or x.owner_email,
                "Owner User ID": x.owner_user_id,
                "Source File": x.source_file,
                "Source Row": x.source_row,
                "Reason": "FPTK tidak ditemukan" if x.reason == "FPTK_NOT_FOUND" else "Kode Unik memiliki lebih dari satu FPTK",
            }
            for x in items
        ]


def _fptk_without_sourcing_rows():
    with session_scope() as s:
        rows = s.execute(
            select(FPTK, func.count(Application.id).label("application_count"))
            .outerjoin(Application, Application.fptk_id == FPTK.id)
            .group_by(FPTK.id)
            .having(func.count(Application.id) == 0)
            .order_by(FPTK.status, FPTK.kode_unik)
        ).all()
        return [
            {
                "Kode Unik": f.kode_unik,
                "Position": f.position,
                "Status": f.status,
                "PIC Recruiter": f.pic_recruiter,
                "Source File": f.source_file,
                "Impact": "Funneling/Progress dapat tampil 0",
            }
            for f, _ in rows
        ]


def _render_fptk_without_sourcing_warning():
    rows = _fptk_without_sourcing_rows()
    if not rows:
        st.success("Semua FPTK di Central Master sudah memiliki minimal satu DB Sourcing yang terhubung.")
        return

    open_count = sum(1 for r in rows if str(r.get("Status") or "").upper() == "OP")
    st.warning(
        f"⚠️ **{len(rows)} FPTK belum memiliki DB Sourcing terhubung** ({open_count} berstatus OP). "
        "FPTK tetap valid dan tetap masuk Central Master, tetapi Funneling/Recruitment Progress dapat terlihat 0 semua sampai sourcing tersedia."
    )
    with st.expander("Lihat FPTK tanpa DB Sourcing", expanded=False):
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)



def _render_unlinked_warning(user):
    rows = _unlinked_rows()
    if not rows:
        st.success("Semua DB Sourcing sudah terhubung ke FPTK. Tidak ada data sourcing yang tertinggal dari Funneling.")
        return

    st.warning(
        f"⚠️ **{len(rows)} DB Sourcing belum terhubung ke FPTK.** "
        "Datanya tetap tersimpan, tetapi **tidak dihitung di Funneling/Progress** karena Kode Unik belum menemukan parent FPTK. "
        "Perbaiki Kode Unik lalu link ke FPTK yang valid agar progress kandidat mulai terbaca."
    )

    display = pd.DataFrame(rows).drop(columns=["Owner User ID"])
    st.dataframe(display, use_container_width=True, hide_index=True)

    editable = [r for r in rows if user.get("role") == "admin" or r["Owner User ID"] == user.get("id")]
    if not editable:
        st.caption("Data di atas dapat dilihat oleh semua user. Hanya source owner atau Admin yang dapat memperbaiki Kode Unik.")
        return

    with st.expander("🔧 Perbaiki Kode Unik & Link ke FPTK", expanded=False):
        st.caption(
            "Gunakan ini kalau Kode Unik pada DB Sourcing salah/obsolete. Sistem **tidak membuat FPTK baru**. "
            "Kode yang dimasukkan harus sudah ada di Central FPTK. Setelah berhasil, kandidat otomatis masuk kembali ke Funneling."
        )
        options = {
            f"#{r['ID']} · {r['Candidate']} · {r['Kode Unik']} · {r['Source File']} row {r['Source Row']}": r
            for r in editable
        }
        selected_label = st.selectbox("Pilih DB Sourcing yang mau diperbaiki", list(options), key="unlinked_pick")
        selected = options[selected_label]

        c1, c2 = st.columns([1, 1])
        with c1:
            st.text_input("Kode Unik saat ini", value=selected["Kode Unik"], disabled=True, key="unlinked_old_code")
        with c2:
            new_code = st.text_input("Kode Unik yang benar", placeholder="Paste Kode Unik dari Central FPTK", key="unlinked_new_code")

        if st.button("Link ke FPTK", type="primary", use_container_width=True, key="resolve_unlinked_btn"):
            try:
                stats = resolve_unlinked_sourcing(selected["ID"], new_code, user)
                st.success("Berhasil di-link. Candidate/Application/Pipeline sudah dibuat dan sekarang akan terbaca di Funneling.")
                if stats:
                    st.caption("Compile result: " + ", ".join(f"{k}={v}" for k, v in stats.items()))
                st.rerun()
            except Exception as exc:
                st.error(str(exc))


def render(user):
    st.header("Monitoring, Funneling & Evidence")
    t1, t2, t3 = st.tabs(["Daily Sourcing", "Funneling", "Evidence"])

    with t1:
        with session_scope() as s:
            q = (
                select(PipelineEvent, Application, FPTK)
                .join(Application, Application.id == PipelineEvent.application_id)
                .join(FPTK, FPTK.id == Application.fptk_id)
                .where(PipelineEvent.stage.in_(["Sourcing HR", "Sourcing FL"]))
            )
            rows = s.execute(q).all()
        data = [
            {
                "Date": e.event_date,
                "Kode Unik": f.kode_unik,
                "Position": f.position,
                "Recruiter": a.recruiter,
                "Candidate": e.application_id,
            }
            for e, a, f in rows
            if e.event_date
        ]
        df = pd.DataFrame(data)
        if df.empty:
            st.info("Belum ada sourcing event yang sudah terhubung ke FPTK.")
        else:
            piv = (
                df.groupby(["Kode Unik", "Position", "Recruiter", "Date"])["Candidate"]
                .nunique()
                .reset_index(name="CV")
                .pivot_table(index=["Kode Unik", "Position", "Recruiter"], columns="Date", values="CV", fill_value=0)
                .reset_index()
            )
            st.dataframe(piv, use_container_width=True, hide_index=True)

    with t2:
        _render_unlinked_warning(user)
        _render_fptk_without_sourcing_warning()
        st.markdown("### Funneling")
        st.caption("Hanya DB Sourcing yang sudah memiliki parent FPTK valid yang dihitung di tabel ini.")
        st.dataframe(funnel_summary(user), use_container_width=True, hide_index=True)

    with t3:
        df = fptk_dataframe(user)
        opens = df[df.status == "OP"]
        if opens.empty:
            st.info("Tidak ada FPTK open.")
        else:
            mapping = {f"{r.kode_unik} | {r.position}": int(r.id) for _, r in opens.iterrows()}
            sel = st.selectbox("FPTK", list(mapping))
            d = st.date_input("Evidence date", date.today())
            total = st.number_input("Total CV", 0, 1000, 0)
            file = st.file_uploader("Evidence file", type=["xlsx", "xls", "pdf", "png", "jpg", "jpeg"])
            url = st.text_input("External / OneDrive URL (optional)")
            if st.button("Save Evidence", use_container_width=True) and (file or url):
                path = None
                if file:
                    from core.config import DATA_DIR
                    p = DATA_DIR / "evidence"
                    p.mkdir(exist_ok=True)
                    target = p / f"{date.today().isoformat()}_{file.name}"
                    target.write_bytes(file.getvalue())
                    path = str(target)
                with session_scope() as s:
                    s.add(
                        Evidence(
                            fptk_id=mapping[sel],
                            evidence_date=d,
                            file_name=file.name if file else "External link",
                            storage_path=path,
                            external_url=url or None,
                            total_cv=int(total),
                            uploaded_by=user["email"],
                        )
                    )
                st.success("Evidence saved")
