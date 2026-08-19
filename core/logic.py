from __future__ import annotations
from datetime import date, datetime, timedelta
import re

TRUE_SET = {"v", "y", "yes", "ya", "true", "1", "available", "aktif"}
FALSE_SET = {"x", "n", "no", "tidak", "false", "0", "not available", "inactive"}

def normalize_text(v):
    if v is None: return None
    s = str(v).replace("\xa0", " ").strip()
    return re.sub(r"\s+", " ", s) or None

def normalize_status(v):
    s = (normalize_text(v) or "").lower()
    if s in {"op", "open", "ongoing", "on going"}: return "OP"
    if s in {"closed", "close", "done", "filled"}: return "Closed"
    if s in {"cancel", "cancelled", "canceled"}: return "Cancel"
    return normalize_text(v) or "OP"

def normalize_availability(v, default=True):
    s = (normalize_text(v) or "").lower()
    if s in TRUE_SET: return True
    if s in FALSE_SET: return False
    return default

def to_int(v, default=None):
    try:
        if v is None or str(v).strip()=="": return default
        return int(float(v))
    except Exception: return default

def to_float(v, default=None):
    try:
        if v is None or str(v).strip()=="": return default
        return float(v)
    except Exception: return default

def excel_date(v):
    if v is None or v == "": return None
    if isinstance(v, datetime): return v.date()
    if isinstance(v, date): return v
    if isinstance(v, (int, float)):
        if 20000 < float(v) < 80000:
            return (datetime(1899, 12, 30) + timedelta(days=float(v))).date()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y"):
        try: return datetime.strptime(s, fmt).date()
        except ValueError: pass
    return None

def derive_level_number(level):
    s = normalize_text(level) or ""
    m = re.search(r"([1-5])", s)
    return int(m.group(1)) if m else None

def sla_days_for_level(level):
    n = derive_level_number(level)
    return 60 if n == 5 else (45 if n == 4 else 30)

def derive_filter_category(position, level, explicit=None, model=None):
    if normalize_text(explicit): return normalize_text(explicit)
    p = (position or "").lower()
    if "fgdp" in p or "clap" in p: return "CLAP & FGDP"
    if "sales taking order" in p or (model or "").lower() == "model 4": return "STO"
    n = derive_level_number(level)
    if n == 4: return "Manager"
    if n == 3: return "Level 3"
    return "Level 2C Below"

def compute_deadline(fptk_date, level):
    return fptk_date + timedelta(days=sla_days_for_level(level)) if fptk_date else None

def compute_sla_result(status, deadline, offering_date=None, cancel_date=None, today=None):
    today = today or date.today()
    status = normalize_status(status)
    if status == "Cancel": return "Cancel FPTK"
    if status == "Closed":
        if not offering_date: return "Data Incomplete - Offering Date Missing"
        if not deadline: return "Data Incomplete - SLA Deadline Missing"
        return "Closed lulus SLA" if offering_date <= deadline else "Closed tidak lulus SLA"
    if status == "OP":
        if not deadline: return "OP - SLA unknown"
        return "OP belum lewat SLA" if today <= deadline else "OP tidak lulus SLA"
    return None

def derive_recruitment_model(position, level, filter_category=None):
    p=(position or "").lower(); c=(filter_category or "").lower()
    if "sales taking order" in p or "sto" == c: return "Model 4"
    if "area sales supervisor" in p: return "Model 3"
    if derive_level_number(level) == 4 or "clap" in p: return "Model 2"
    return "Model 1"

FLOW_MAP = {
    "Model 1": ["Sourcing FL","Sourcing HR","Shortlist CV","Psikotes","HR Interview","Technical Test / Case Study","Market Visit","User Interview","Reference Check","MCU","Offering","Day 1"],
    "Model 2": ["Sourcing FL","Sourcing HR","Shortlist CV","Psikotes","Technical Test / Case Study","Panel Interview","Reference Check","MCU","Offering","Day 1"],
    "Model 3": ["Sourcing FL","Sourcing HR","Shortlist CV","Psikotes","HR Interview","Shortcall User Interview","Technical Test / Case Study","Market Visit","User Interview","Reference Check","Offering","Day 1"],
    "Model 4": ["Sourcing FL","Sourcing HR","Shortlist CV","User Interview","HR Interview","Reference Check","Offering","Day 1"],
}
