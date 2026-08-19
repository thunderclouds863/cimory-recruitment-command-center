from __future__ import annotations
from datetime import timedelta
import json
import pandas as pd
import streamlit as st
from sqlalchemy import select

from core.db import session_scope
from core.models import FPTK, SourceOwnership, UploadBatch
from core.compile_engine import process_upload, _sla_days, _sla_result
from core.compile_rules import (
    BUSINESS_UNITS, DIRECTORATES, REQUEST_REASONS, CATEGORIES, STATUSES,
    REASON_TO_CATEGORY, key_text,
)
from core.upload_cycles import (
    get_active_cycle, get_member_state, register_upload_result, mark_done,
)


def _style():
    st.markdown(
        """
        <style>
        .compile-hero{padding:24px 26px;border-radius:20px;background:linear-gradient(125deg,#172554,#27358F 64%,#4456be);color:white;margin-bottom:18px;box-shadow:0 12px 30px rgba(39,53,143,.18)}
        .compile-hero .eyebrow{font-size:.72rem;font-weight:800;letter-spacing:.16em;opacity:.78}.compile-hero h2{margin:.2rem 0 .25rem;font-size:1.85rem}.compile-hero p{margin:0;opacity:.86}
        .guide{border:1px solid #dbe3ff;background:#f7f9ff;padding:16px 18px;border-radius:14px;margin:.6rem 0 1rem}.guide b{color:#27358F}
        .ok-banner{padding:15px 18px;border-radius:13px;background:#ecfdf3;border:1px solid #b7ebc8;color:#166534;font-weight:700}
        .bad-banner{padding:15px 18px;border-radius:13px;background:#fff1f2;border:1px solid #fecdd3;color:#9f1239;font-weight:700}
        .cycle-card{padding:16px 18px;border-radius:14px;border:1px solid #e5e7eb;background:#fff}
        .status-done{color:#166534;font-weight:800}.status-progress{color:#9a6700;font-weight:800}.status-not{color:#64748b;font-weight:800}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _cycle_header(user):
    if user.get("role") == "admin":
        return
    cycle = get_active_cycle()
    state = get_member_state(user["id"])
    status_class = {"DONE": "status-done", "UPLOADING": "status-progress"}.get(state["status"], "status-not")
    st.markdown(
        f"""
        <div class="cycle-card">
          <div style="display:flex;justify-content:space-between;gap:18px;align-items:center;flex-wrap:wrap">
            <div><div style="font-size:.72rem;font-weight:800;letter-spacing:.12em;color:#64748b">UPLOAD CYCLE AKTIF</div>
            <div style="font-size:1.08rem;font-weight:800;color:#111827">{cycle['name']}</div></div>
            <div style="text-align:right"><div style="font-size:.75rem;color:#64748b">Status kamu</div>
            <div class="{status_class}">{state['status_label']}</div></div>
          </div>
          <div style="margin-top:8px;color:#64748b;font-size:.88rem">File berhasil: <b>{state['successful_file_count']}</b> · Gagal validasi/compile: <b>{state['failed_file_count']}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    if state["status"] == "DONE":
        st.success("Kamu sudah menandai upload cycle ini sebagai **Done**. Kalau upload file baru lagi, status otomatis kembali menjadi **Sedang Upload** dan kamu perlu klik Done lagi.")
    elif state["successful_file_count"] > 0:
        st.info("Semua file yang diperlukan sudah berhasil di-compile? Klik **Done Uploading**. Selama tombol itu belum diklik, Admin akan melihat status kamu sebagai **Sedang Upload**.")
        if st.button("✅ Done Uploading — Saya Selesai Upload", type="primary", use_container_width=True):
            try:
                count = mark_done(user["id"])
                st.success(f"Selesai. {count} file berhasil tercatat untuk cycle ini.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    else:
        st.caption("Status tetap **Belum Mulai** sampai minimal satu file berhasil melewati validation dan compile.")


def _guidance():
    st.markdown(
        """
        <div class="guide"><b>Sebelum upload</b><br>
        Pastikan file sudah dirapikan. Sistem tidak akan memperbaiki data yang salah secara diam-diam. Kalau ada satu blocking issue, file tersebut <b>tidak di-compile sama sekali</b> dan sistem akan menunjukkan sheet, row, nilai sekarang, nilai yang seharusnya, serta cara memperbaikinya.</div>
        """,
        unsafe_allow_html=True,
    )
    a, b = st.columns(2)
    with a:
        st.markdown("""
**FPTK**
- Kode PIC, FPTK Date Real, Kode Unik, Posisi wajib terisi
- Kode Unik harus unique di file dan tidak boleh bentrok dengan owner lain
- Business Unit & Direktorat harus menggunakan nama standar
- Divisi, Department, Level FPTK, Level Number wajib benar
- Alasan FPTK, Category, PIC Recruiter, Vacancy wajib terisi
""")
    with b:
        st.markdown("""
**Status & Sourcing**
- Status hanya `OP`, `Closed`, `Cancel`
- `Closed` wajib memiliki Offering Date
- `Cancel` wajib memiliki FPTK Cancel Date
- Week/Month dihitung ulang dari tanggal oleh sistem
- Setiap row DB Sourcing wajib memiliki Sourcing Date
- File STO menggunakan flow compiler STO khusus
""")


def _validation_table(validation, filename):
    rows = validation.issue_rows()
    if not rows:
        return
    df = pd.DataFrame(rows)
    preferred = ["severity", "sheet", "row", "field", "current", "expected", "fix"]
    st.dataframe(df[preferred], use_container_width=True, hide_index=True, height=min(560, 80 + 34 * len(df)))
    st.download_button(
        "⬇ Download Validation Report (CSV)",
        data=df[preferred].to_csv(index=False).encode("utf-8-sig"),
        file_name=f"validation_{filename.rsplit('.',1)[0]}.csv",
        mime="text/csv",
        use_container_width=True,
    )


def _process_files(files, source_mode, user):
    if not files:
        return
    explicit = None if source_mode == "Auto detect" else ("STO" if source_mode == "STO" else "RECRUITER")
    success_count = 0
    fail_count = 0
    for i, up in enumerate(files, start=1):
        st.markdown(f"### {i}. {up.name}")
        st.caption(f"{up.size/1024/1024:.2f} MB")
        bar = st.progress(0)
        status_box = st.empty()

        def progress(stage, pct, message):
            bar.progress(int(pct))
            status_box.caption(f"{stage} · {message}")

        try:
            result = process_upload(up.getvalue(), up.name, user, explicit, progress_callback=progress)
            validation = result["validation"]
            if user.get("role") != "admin":
                register_upload_result(user["id"], result["batch_id"], bool(result.get("compiled")))
            if not validation.passed:
                fail_count += 1
                bar.progress(100)
                status_box.caption("Validation gagal — 0 record dari file ini masuk ke Central Master")
                st.markdown(
                    f'<div class="bad-banner">File belum bisa diproses. Ditemukan {len(validation.errors)} blocking issue. Perbaiki file sumber lalu upload ulang.</div>',
                    unsafe_allow_html=True,
                )
                _validation_table(validation, up.name)
            else:
                success_count += 1
                st.markdown('<div class="ok-banner">Validation passed dan compile selesai.</div>', unsafe_allow_html=True)
                cols = st.columns(4)
                cols[0].metric("FPTK", validation.counts.get("fptk", 0))
                cols[1].metric("DB Sourcing", validation.counts.get("sourcing", 0))
                cols[2].metric("Blacklist", validation.counts.get("blacklist", 0))
                cols[3].metric("Warning", len(validation.warnings))
                if validation.warnings:
                    st.warning(
                        f"Compile berhasil, tetapi ada {len(validation.warnings)} warning yang perlu dicek. "
                        "Warning tidak memblok data masuk, namun dapat memengaruhi Funneling/Recruitment Progress."
                    )
                    _validation_table(validation, up.name)
                with st.expander("Compile detail", expanded=False):
                    st.json(result["stats"])
        except Exception as exc:
            fail_count += 1
            status_box.caption("Compile gagal")
            st.exception(exc)
        st.divider()
    if success_count or fail_count:
        st.subheader("Ringkasan proses")
        c1, c2 = st.columns(2)
        c1.metric("File berhasil", success_count)
        c2.metric("File perlu diperbaiki", fail_count)
        if user.get("role") != "admin" and success_count:
            st.info("Upload file tambahan jika masih ada. Kalau seluruh file untuk cycle ini sudah selesai, klik **Done Uploading** di bagian atas halaman.")


def _upload_tab(user):
    _cycle_header(user)
    _guidance()
    st.write("")
    c1, c2 = st.columns([1.65, .55])
    with c1:
        files = st.file_uploader(
            "Upload file Excel",
            type=["xlsx", "xlsm"],
            accept_multiple_files=True,
            help="Boleh pilih lebih dari satu file. Setiap file divalidasi dan di-compile secara terpisah.",
        )
    with c2:
        source_mode = st.selectbox("Tipe file", ["Auto detect", "Recruiter File", "STO"])
    if files:
        st.caption(f"{len(files)} file dipilih. Kamu masih bisa upload file lain setelah proses ini selesai.")
    if st.button("🔍 Validasi & Compile File", type="primary", use_container_width=True, disabled=not files):
        _process_files(files, source_mode, user)


def _compiled_data_tab(user):
    st.subheader("Central Master · FPTK")
    st.caption("Semua akun dapat melihat hasil compile. Yang bisa mengubah data hanya source owner dan Admin.")
    with session_scope() as s:
        rows = s.execute(
            select(FPTK, SourceOwnership)
            .outerjoin(
                SourceOwnership,
                (SourceOwnership.entity_type == "FPTK") & (SourceOwnership.entity_id == FPTK.id),
            )
            .order_by(FPTK.updated_at.desc())
        ).all()
    data = []
    for f, o in rows:
        mine = user.get("role") == "admin" or (o and o.owner_user_id == user.get("id"))
        data.append(
            {
                "ID": f.id,
                "Kode Unik": f.kode_unik,
                "FPTK Date": f.fptk_date,
                "Posisi": f.position,
                "Business Unit": f.business_unit,
                "Direktorat": f.directorate,
                "Divisi": f.division,
                "Department": f.department,
                "Level": f.level_fptk,
                "PIC Recruiter": f.pic_recruiter,
                "Vacancy": f.vacancy,
                "Status": f.status,
                "SLA": f.sla_result,
                "Source Owner": (o.owner_name or o.owner_email) if o else "Legacy / belum diklaim",
                "Source File": f.source_file,
                "Hak Akses": "EDIT" if mine else "VIEW ONLY",
            }
        )
    st.dataframe(data, use_container_width=True, hide_index=True, height=520)

    editable = [(f, o) for f, o in rows if user.get("role") == "admin" or (o and o.owner_user_id == user.get("id"))]
    if not editable:
        return
    with st.expander("✏ Edit data yang saya miliki", expanded=False):
        options = {f"{f.kode_unik} | {f.position}": f.id for f, _ in editable}
        selected = st.selectbox("Pilih FPTK", list(options))
        fid = options[selected]
        with session_scope() as s:
            f = s.get(FPTK, fid)
            snapshot = {
                k: getattr(f, k)
                for k in [
                    "business_unit", "directorate", "division", "department", "level_fptk", "level_number",
                    "request_reason", "category_fptk", "pic_recruiter", "vacancy", "status", "cancel_date",
                    "offering_date", "remarks", "fptk_date",
                ]
            }
            identity = (f.kode_unik, f.position, f.fptk_date)
        st.caption(f"Identity dikunci: **{identity[0]}** · {identity[1]} · {identity[2] or '-'}")
        with st.form(f"edit_owned_{fid}"):
            c1, c2 = st.columns(2)
            bu = c1.selectbox("Business Unit", BUSINESS_UNITS, index=BUSINESS_UNITS.index(snapshot["business_unit"]) if snapshot["business_unit"] in BUSINESS_UNITS else 0)
            direct = c2.selectbox("Direktorat", DIRECTORATES, index=DIRECTORATES.index(snapshot["directorate"]) if snapshot["directorate"] in DIRECTORATES else 0)
            c1, c2 = st.columns(2)
            div = c1.text_input("Divisi", snapshot["division"] or "")
            dep = c2.text_input("Department", snapshot["department"] or "")
            c1, c2 = st.columns(2)
            lvl = c1.text_input("Level FPTK", snapshot["level_fptk"] or "")
            level_num = c2.number_input("Level Number", 1, 5, int(snapshot["level_number"] or 1))
            c1, c2 = st.columns(2)
            reason = c1.selectbox("Alasan Permintaan FPTK", REQUEST_REASONS, index=REQUEST_REASONS.index(snapshot["request_reason"]) if snapshot["request_reason"] in REQUEST_REASONS else 0)
            expected_cat = REASON_TO_CATEGORY[key_text(reason)]
            cat = c2.selectbox("Category FPTK", CATEGORIES, index=CATEGORIES.index(snapshot["category_fptk"]) if snapshot["category_fptk"] in CATEGORIES else CATEGORIES.index(expected_cat))
            c1, c2, c3 = st.columns(3)
            pic = c1.text_input("PIC Recruiter", snapshot["pic_recruiter"] or "")
            vacancy = c2.number_input("Vacancy", 1, 999, int(snapshot["vacancy"] or 1))
            status_v = c3.selectbox("Status", STATUSES, index=STATUSES.index(snapshot["status"]) if snapshot["status"] in STATUSES else 0)
            c1, c2 = st.columns(2)
            cancel = c1.date_input("FPTK Cancel Date", value=snapshot["cancel_date"])
            offer = c2.date_input("Offering Date", value=snapshot["offering_date"])
            remarks = st.text_area("Remarks", snapshot["remarks"] or "")
            save = st.form_submit_button("Simpan perubahan", type="primary", use_container_width=True)
        if save:
            import re
            errors = []
            normalized_level = lvl.strip().upper()
            if not re.fullmatch(r"[1-5][A-Z]", normalized_level):
                errors.append("Level FPTK harus format 1A/2B/3A/dst.")
            elif int(normalized_level[0]) != int(level_num):
                errors.append("Level Number harus sama dengan angka Level FPTK.")
            if cat != expected_cat:
                errors.append(f"Alasan {reason} harus Category {expected_cat}.")
            if status_v == "Cancel" and not cancel:
                errors.append("Status Cancel wajib FPTK Cancel Date.")
            if status_v == "Closed" and not offer:
                errors.append("Status Closed wajib Offering Date.")
            if errors:
                for e in errors:
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
                    f.level_fptk = normalized_level
                    f.level_number = int(level_num)
                    f.request_reason = reason
                    f.category_fptk = cat
                    f.pic_recruiter = pic.strip()
                    f.vacancy = int(vacancy)
                    f.status = status_v
                    f.cancel_date = cancel
                    f.offering_date = offer
                    f.remarks = remarks.strip() or None
                    days = _sla_days(f.level_fptk)
                    f.sla_days = days
                    f.deadline_sla = f.fptk_date + timedelta(days=days) if f.fptk_date else None
                    f.sla_result = _sla_result(f.status, f.deadline_sla, f.offering_date)
                st.success("Data berhasil diperbarui.")
                st.rerun()


def _history_tab(user):
    st.subheader("Upload History")
    with session_scope() as s:
        q = select(UploadBatch).order_by(UploadBatch.created_at.desc()).limit(500)
        if user.get("role") != "admin":
            q = q.where(UploadBatch.owner_user_id == user.get("id"))
        rows = s.scalars(q).all()
    data = []
    for x in rows:
        data.append(
            {
                "Date": x.created_at,
                "Owner": x.owner_name or x.owner_email,
                "File": x.source_file,
                "Type": x.source_type,
                "Status": x.status,
                "FPTK": x.fptk_rows,
                "Sourcing": x.sourcing_rows,
                "Blacklist": x.blacklist_rows,
                "Issues": x.validation_issue_count,
            }
        )
    st.dataframe(data, use_container_width=True, hide_index=True, height=520)


def render(user):
    _style()
    st.markdown(
        """
        <div class="compile-hero"><div class="eyebrow">CENTRAL COMPILER</div><h2>Upload & Compile Recruitment Database</h2>
        <p>Validasi file sebelum masuk Central Master. Data user lain tetap terlihat, tetapi hanya source owner dan Admin yang dapat mengubahnya.</p></div>
        """,
        unsafe_allow_html=True,
    )
    tab1, tab2, tab3 = st.tabs(["📤 Upload File", "🗂 Central Master", "🕘 Upload History"])
    with tab1:
        _upload_tab(user)
    with tab2:
        _compiled_data_tab(user)
    with tab3:
        _history_tab(user)
