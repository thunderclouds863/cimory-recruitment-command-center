from __future__ import annotations
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
ASSET_DIR = ROOT / "assets"
TEMPLATE_DIR = ROOT / "templates"
DATA_DIR.mkdir(exist_ok=True)


def _secret_or_env(name: str, default: str | None = None):
    if os.getenv(name):
        return os.getenv(name)
    try:
        import streamlit as st
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default


APP_NAME = _secret_or_env("APP_NAME", "Recruitment Command Center")
AUTH_MODE = (_secret_or_env("AUTH_MODE", "local") or "local").lower()
DATABASE_URL = _secret_or_env("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'recruitment.db').as_posix()}")
PPT_TEMPLATE = TEMPLATE_DIR / "CEO_UPDATE_TEMPLATE.pptx"
BRAND_LOGO = ASSET_DIR / "rising_with_cimory.png"

BRAND_BLUE = "27358F"
BRAND_RED = "EF233C"
BRAND_LIGHT = "F4F6FB"
TEXT_DARK = "111827"
TEXT_MUTED = "667085"
