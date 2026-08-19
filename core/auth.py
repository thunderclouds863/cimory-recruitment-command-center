from __future__ import annotations
import hashlib
import hmac
import secrets
from sqlalchemy import select

from .config import AUTH_MODE
from .db import session_scope
from .models import User

# Requested initial accounts. Passwords are case-sensitive.
DEFAULT_ACCOUNTS = [
    ("CMD", "1CMD"),
    ("Brittney", "2Brittney"),
    ("Eli", "3Eli"),
    ("Fiqra", "4Fiqra"),
    ("Karin", "5Karin"),
    ("Kenthansen", "6Kenthansen"),
    ("Kevin", "7Kevin"),
    ("Marta", "8Marta"),
    ("Omega", "9Omega"),
    ("Pauline", "10Pauline"),
    ("Salsa", "11Salsa"),
    ("Valendra", "12Valendra"),
    ("Victor", "13Victor"),
    ("Zwei", "14Zwei"),
    ("JESS", "15JESS"),
    ("MP", "16MP"),
    ("MS", "17MS"),
]
ADMIN_ACCOUNT = ("admin", "admin123")


def hash_password(password: str, salt_hex: str | None = None):
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 240_000)
    return salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, expected_hex: str):
    _, actual = hash_password(password, salt_hex)
    return hmac.compare_digest(actual, expected_hex)


def seed_default_users():
    """Create missing requested accounts. Existing passwords are never reset on restart."""
    with session_scope() as s:
        existing = {u.email.casefold(): u for u in s.scalars(select(User)).all()}
        username, password = ADMIN_ACCOUNT
        if username.casefold() not in existing:
            salt, ph = hash_password(password)
            s.add(
                User(
                    email=username,
                    display_name="Admin",
                    role="admin",
                    recruiter_name=None,
                    password_salt=salt,
                    password_hash=ph,
                    active=True,
                )
            )
        for username, password in DEFAULT_ACCOUNTS:
            if username.casefold() in existing:
                # Keep password but ensure role/name mapping is correct.
                u = existing[username.casefold()]
                u.display_name = username
                u.role = "recruiter"
                u.recruiter_name = username
                u.active = True
                continue
            salt, ph = hash_password(password)
            s.add(
                User(
                    email=username,
                    display_name=username,
                    role="recruiter",
                    recruiter_name=username,
                    password_salt=salt,
                    password_hash=ph,
                    active=True,
                )
            )


def _lookup_user(username: str):
    with session_scope() as s:
        rows = s.scalars(select(User).where(User.active == True)).all()
        u = next((x for x in rows if x.email.casefold() == (username or "").casefold()), None)
        if not u:
            return None
        return {
            "id": u.id,
            "username": u.email,
            "email": u.email,  # compatibility with existing audit/ownership code
            "display_name": u.display_name,
            "role": u.role,
            "recruiter_name": u.recruiter_name,
        }


def authenticate():
    import streamlit as st
    if "user" in st.session_state:
        return st.session_state.user

    # OIDC is kept for future Microsoft login, but local username/password is the requested mode.
    if AUTH_MODE == "oidc":
        try:
            if not st.user.is_logged_in:
                st.title("Recruitment Command Center")
                st.button("Sign in with Microsoft", on_click=st.login, use_container_width=True)
                st.stop()
            login_key = getattr(st.user, "preferred_username", None) or getattr(st.user, "email", None)
            user = _lookup_user(login_key) if login_key else None
            if not user:
                st.error("Microsoft account berhasil login tetapi belum terdaftar di aplikasi.")
                st.stop()
            st.session_state.user = user
            return user
        except Exception as exc:
            st.error(f"OIDC belum terkonfigurasi: {exc}")
            st.stop()

    st.markdown(
        """
        <div style="max-width:520px;margin:3rem auto 1.2rem auto;padding:28px 30px;border:1px solid #e5e7eb;border-radius:18px;background:white;box-shadow:0 12px 35px rgba(15,23,42,.08)">
          <div style="font-size:.78rem;font-weight:800;letter-spacing:.14em;color:#64748b">CIMORY TALENT ACQUISITION</div>
          <div style="font-size:2rem;font-weight:800;color:#111827;margin-top:6px">Recruitment Command Center</div>
          <div style="color:#64748b;margin-top:6px">Login menggunakan username yang sudah diberikan oleh Admin.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("login", clear_on_submit=False):
        username = st.text_input("Username", placeholder="Contoh: Brittney")
        password = st.text_input("Password", type="password")
        ok = st.form_submit_button("Login", type="primary", use_container_width=True)
    if ok:
        with session_scope() as s:
            rows = s.scalars(select(User).where(User.active == True)).all()
            u = next((x for x in rows if x.email.casefold() == (username or "").strip().casefold()), None)
            if u and u.password_hash and u.password_salt and verify_password(password, u.password_salt, u.password_hash):
                st.session_state.user = {
                    "id": u.id,
                    "username": u.email,
                    "email": u.email,
                    "display_name": u.display_name,
                    "role": u.role,
                    "recruiter_name": u.recruiter_name,
                }
                st.rerun()
            st.error("Username atau password tidak sesuai.")
    st.stop()


def change_password(user_id: int, old_password: str, new_password: str):
    if len(new_password or "") < 8:
        raise ValueError("Password baru minimal 8 karakter.")
    with session_scope() as s:
        u = s.get(User, user_id)
        if not u or not u.password_hash or not u.password_salt:
            raise ValueError("User tidak ditemukan.")
        if not verify_password(old_password, u.password_salt, u.password_hash):
            raise ValueError("Password lama tidak sesuai.")
        salt, ph = hash_password(new_password)
        u.password_salt = salt
        u.password_hash = ph


def admin_reset_password(user_id: int, new_password: str):
    if len(new_password or "") < 6:
        raise ValueError("Password minimal 6 karakter.")
    with session_scope() as s:
        u = s.get(User, user_id)
        if not u:
            raise ValueError("User tidak ditemukan.")
        salt, ph = hash_password(new_password)
        u.password_salt = salt
        u.password_hash = ph


def logout():
    import streamlit as st
    st.session_state.pop("user", None)
    if AUTH_MODE == "oidc":
        try:
            st.logout()
        except Exception:
            pass
    st.rerun()
