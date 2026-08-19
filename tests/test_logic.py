from datetime import date
from core.logic import normalize_availability, derive_filter_category, compute_deadline, compute_sla_result, derive_recruitment_model

def test_availability_aliases():
    assert normalize_availability('V') is True
    assert normalize_availability('Ya') is True
    assert normalize_availability('Y') is True
    assert normalize_availability('X') is False
    assert normalize_availability('Tidak') is False
    assert normalize_availability('N') is False

def test_categories():
    assert derive_filter_category('Brand Manager','4A')=='Manager'
    assert derive_filter_category('Head of Area','3A')=='Level 3'
    assert derive_filter_category('Sales Taking Order Staff (Chilled) - Bekasi','2A')=='STO'

def test_sla():
    d=date(2026,1,1)
    assert (compute_deadline(d,'4A')-d).days==45
    assert (compute_deadline(d,'3A')-d).days==30
    assert compute_sla_result('Closed',date(2026,1,31),date(2026,1,20))=='Closed lulus SLA'

def test_models():
    assert derive_recruitment_model('Area Sales Supervisor - Jakarta','3A')=='Model 3'
    assert derive_recruitment_model('Sales Taking Order Staff (Chilled) - Bekasi','2A')=='Model 4'
