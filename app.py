from __future__ import annotations
import streamlit as st

from core.config import APP_NAME, BRAND_LOGO
from core.db import init_db
from core.auth import seed_default_users, authenticate, logout, change_password
from core.upload_cycles import ensure_active_cycle
from views import dashboard, fptk, candidates, pipeline, monitoring, transfer, reports, admin, compile_upload

st.set_page_config(
    page_title=APP_NAME,
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()
seed_default_users()
ensure_active_cycle()
user = authenticate()

st.markdown(
    """
    <style>
    .block-container{padding-top:1.35rem;max-width:1500px}
    .stMetric{background:#f8fafc;border:1px solid #e5e7eb;padding:12px;border-radius:13px}
    .stTabs [data-baseweb=tab]{font-weight:750}
    .stButton>button,.stDownloadButton>button{border-radius:10px}
    [data-testid="stSidebar"]{border-right:1px solid #e5e7eb}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    if BRAND_LOGO.exists():
        st.image(str(BRAND_LOGO), width=165)
    st.markdown(f"**{user['display_name']}**")
    st.caption("ADMIN" if user["role"] == "admin" else "UPLOAD USER")

    pages = [
        "Dashboard",
        "Upload & Compile",
        "FPTK Database",
        "Candidate & CV",
        "Pipeline",
        "Monitoring & Funnel",
        "Reports & Export",
    ]
    if user["role"] == "admin":
        pages.extend(["Transfer FPTK", "Admin"])
    page = st.radio("Navigation", pages, label_visibility="collapsed")
    st.divider()

    with st.expander("🔐 Change Password"):
        with st.form("change_password_form"):
            old_pw = st.text_input("Password lama", type="password")
            new_pw = st.text_input("Password baru", type="password")
            new_pw2 = st.text_input("Ulangi password baru", type="password")
            change = st.form_submit_button("Update Password", use_container_width=True)
        if change:
            if new_pw != new_pw2:
                st.error("Konfirmasi password tidak sama.")
            else:
                try:
                    change_password(user["id"], old_pw, new_pw)
                    st.success("Password berhasil diubah.")
                except Exception as exc:
                    st.error(str(exc))

    st.caption("Central database · source ownership · strict validation")
    if st.button("Logout", use_container_width=True):
        logout()

ROUTES = {
    "Dashboard": dashboard.render,
    "Upload & Compile": compile_upload.render,
    "FPTK Database": fptk.render,
    "Candidate & CV": candidates.render,
    "Pipeline": pipeline.render,
    "Monitoring & Funnel": monitoring.render,
    "Transfer FPTK": transfer.render,
    "Reports & Export": reports.render,
    "Admin": admin.render,
}
ROUTES[page](user)
