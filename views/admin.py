from __future__ import annotations
from datetime import datetime
import streamlit as st
from sqlalchemy import select

from core.db import session_scope
from core.models import User, SchemaConfig, ImportRun, AuditLog
from core.auth import DEFAULT_ACCOUNTS, ADMIN_ACCOUNT, admin_reset_password
from core.legacy_import import import_workbook
from core.upload_cycles import (
    get_active_cycle, cycle_monitor_rows, cycle_summary, create_cycle,
    reopen_member, list_cycles,
)


def _monitor_tab(user):
    cycle = get_active_cycle()
    summary = cycle_summary(cycle["id"])
    st.subheader("Upload Completion Monitor")
    st.caption("User baru dianggap selesai setelah minimal satu file berhasil di-compile dan user menekan tombol **Done Uploading**.")
    st.info(f"Cycle aktif: **{cycle['name']}** · dibuka {cycle['opened_at']:%d/%m/%Y %H:%M}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total User", summary["total"])
    c2.metric("Belum Mulai", summary["not_started"])
    c3.metric("Sedang Upload", summary["uploading"])
    c4.metric("Done", summary["done"])

    rows = cycle_monitor_rows(cycle["id"])
    st.dataframe(
        [{k: v for k, v in r.items() if k != "member_id"} for r in rows],
        use_container_width=True,
        hide_index=True,
        height=580,
    )

    with st.expander("Admin action", expanded=False):
        left, right = st.columns(2)
        with left:
            st.markdown("**Buka upload cycle baru**")
            cycle_name = st.text_input("Nama cycle", placeholder="Contoh: Compile Week 34 - Aug 2026")
            st.caption("Saat cycle baru dibuat, semua 17 akun kembali ke status Belum Mulai untuk cycle baru. History cycle lama tetap tersimpan.")
            if st.button("Buka Cycle Baru", type="primary", use_container_width=True):
                if not cycle_name.strip():
                    st.error("Nama cycle wajib diisi.")
                else:
                    create_cycle(cycle_name.strip(), user.get("username") or user.get("email") or "admin")
                    st.success("Cycle baru berhasil dibuka.")
                    st.rerun()
        with right:
            st.markdown("**Reopen status user**")
            done_or_progress = {f"{r['Username']} · {r['Status']}": r["member_id"] for r in rows}
            selected = st.selectbox("Pilih user", list(done_or_progress)) if done_or_progress else None
            if st.button("Reopen / Set Belum Selesai", use_container_width=True, disabled=not selected):
                reopen_member(done_or_progress[selected])
                st.success("Status user dibuka kembali.")
                st.rerun()

    with st.expander("History upload cycle", expanded=False):
        st.dataframe(list_cycles(), use_container_width=True, hide_index=True)


def _users_tab():
    st.subheader("Account Management")
    st.caption("17 account upload + 1 Admin. Username disimpan case-insensitive, password tetap case-sensitive.")
    with session_scope() as s:
        users = s.scalars(select(User).order_by(User.id)).all()
    requested_order = [x[0] for x in DEFAULT_ACCOUNTS]
    rows = []
    for u in users:
        initial = "admin123" if u.role == "admin" and u.email.casefold() == "admin" else ""
        if u.email in requested_order:
            idx = requested_order.index(u.email)
            initial = DEFAULT_ACCOUNTS[idx][1]
        rows.append({
            "ID": u.id,
            "Username": u.email,
            "Name": u.display_name,
            "Role": u.role,
            "Owner Mapping": u.recruiter_name or "-",
            "Active": u.active,
            "Initial Password": initial,
        })
    st.dataframe(rows, use_container_width=True, hide_index=True, height=600)
    st.warning("Initial password ditampilkan untuk setup/testing. Untuk penggunaan production, minta tiap user mengganti password setelah login dan simpan repository GitHub sebagai **private**.")

    with st.expander("Reset password user", expanded=False):
        options = {f"{u.email} · {u.display_name}": u.id for u in users}
        selected = st.selectbox("User", list(options))
        new_password = st.text_input("Password baru", type="password")
        if st.button("Reset Password", use_container_width=True):
            try:
                admin_reset_password(options[selected], new_password)
                st.success("Password berhasil di-reset.")
            except Exception as exc:
                st.error(str(exc))


def _legacy_tab():
    st.warning("Legacy Import hanya untuk migrasi awal MASTER_COMPILE lama. Upload rutin wajib lewat menu **Upload & Compile** agar validation, ownership, dan upload tracking berjalan.")
    up = st.file_uploader("Upload MASTER_COMPILE .xlsx / .xlsm", type=["xlsx", "xlsm"], key="legacy_master")
    if st.button("Import Legacy Master", use_container_width=True, disabled=up is None):
        with st.spinner("Reading workbook and upserting legacy data..."):
            bar = st.progress(0)
            status_box = st.empty()
            def _progress(stage, current, total, message):
                pct = int(min(max(current / max(total, 1), 0), 1) * 100)
                bar.progress(pct)
                status_box.caption(f"{stage}: {message}")
            try:
                result = import_workbook(up, "MASTER_COMPILE", progress_callback=_progress)
                bar.progress(100)
                status_box.caption("Import complete")
                st.success(result)
            except Exception as exc:
                st.exception(exc)
    with session_scope() as s:
        runs = s.scalars(select(ImportRun).order_by(ImportRun.created_at.desc()).limit(30)).all()
    st.dataframe([
        {"Date": r.created_at, "File": r.source_file, "Type": r.source_type, "Inserted": r.inserted, "Updated": r.updated, "Skipped": r.skipped}
        for r in runs
    ], use_container_width=True, hide_index=True)


def _schema_tab():
    with session_scope() as s:
        cfg = s.scalars(select(SchemaConfig).order_by(SchemaConfig.database_name, SchemaConfig.position)).all()
    st.dataframe([
        {"Database": c.database_name, "Field ID": c.field_id, "Header Name": c.header_name, "Position": c.position, "Active": c.active, "Type": c.data_type, "Required": c.required, "Aliases": c.aliases, "Key Field": c.key_field, "Custom": c.custom_field}
        for c in cfg
    ], use_container_width=True, hide_index=True, height=600)


def _audit_tab():
    with session_scope() as s:
        logs = s.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)).all()
    st.dataframe([
        {"Date": x.created_at, "User": x.user_email, "Action": x.action, "Entity": x.entity_type, "ID": x.entity_id, "Detail": x.detail}
        for x in logs
    ], use_container_width=True, hide_index=True, height=620)


def render(user):
    if user.get("role") != "admin":
        st.error("Admin only")
        return
    st.header("Admin Control Center")
    tabs = st.tabs(["📌 Upload Monitor", "👥 Users", "🧳 Legacy Import", "⚙ Schema", "🕘 Audit"])
    with tabs[0]:
        _monitor_tab(user)
    with tabs[1]:
        _users_tab()
    with tabs[2]:
        _legacy_tab()
    with tabs[3]:
        _schema_tab()
    with tabs[4]:
        _audit_tab()
