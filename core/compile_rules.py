from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime
from collections import defaultdict
import re

from sqlalchemy import select

from .db import session_scope
from .models import FPTK, Application, SourceOwnership
from .logic import normalize_text

COMPILE_RULES_VERSION = "3.6.0-two-way-relation-warning"

BUSINESS_UNITS = [
    "PT CISARUA MOUNTAIN DAIRY, TBK",
    "PT MACROSENTRA NIAGABOGA",
    "PT JAVA EGG SPECIALITIES",
    "PT MACROPRIMA PANGANUTAMA",
    "PT ARTHA RASA CIMORY",
    "PT MACROTAMA BINASANTIKA",
]

DIRECTORATES = [
    "CEO Office",
    "CEO, Corsec, & Investor Relation",
    "Commercial CMD",
    "Commercial JES",
    "Commercial MP",
    "Finance & Business Support",
    "Logistic & Distribution",
    "Manufacture CMD",
    "Manufacture JESS",
    "Manufacture MP",
    "Procurement CMD & Corporate",
    "Procurement MP & JESS",
    "Sales General Trade CMD",
    "Sales General Trade JES",
    "Sales General Trade MP",
    "Sales International Market",
    "Sales Miss Cimory",
    "Sales Modern Trade",
]

# Source: Perubahan Nama Direktorat workbook. A legacy name can map to >1 new directorate.
OLD_DIRECTORATE_MAP = {
    "karimah jamal": ["CEO Office"],
    "sylvia": ["CEO Office"],
    "bharat": ["CEO, Corsec, & Investor Relation"],
    "farell sutantio": ["CEO, Corsec, & Investor Relation"],
    "pak farell dan pak axel": ["CEO, Corsec, & Investor Relation"],
    "cindy saraswaty": ["Commercial CMD"],
    "farell grandisuri (marketing)": ["Commercial CMD"],
    "ivan hartono": ["Commercial JES", "Manufacture JESS", "Sales General Trade JES"],
    "erica febrianti": ["Commercial MP"],
    "erica febrianti (fsi)": ["Commercial MP"],
    "martua parningotan sihaloho": ["Finance & Business Support", "Procurement CMD & Corporate"],
    "selvia yunita": ["Logistic & Distribution"],
    "pamungkas bayu triprasetyo": ["Manufacture CMD"],
    "axel sutantio - r&i": ["Manufacture MP"],
    "kholily": ["Manufacture MP"],
    "axel sutantio - procurement": ["Procurement MP & JESS"],
    "yadi haryadi": ["Sales General Trade CMD"],
    "johan": ["Sales General Trade MP"],
    "ivan hadinata": ["Sales International Market"],
    "hendri viarta": ["Sales Miss Cimory"],
    "hendro wibowo": ["Sales Modern Trade"],
}

REQUEST_REASONS = [
    "Karyawan Lama Keluar",
    "Penambahan Personil",
    "Jabatan Baru",
    "Karyawan Lama Mutasi",
    "Karyawan Lama Promosi",
]

REASON_TO_CATEGORY = {
    "karyawan lama keluar": "REPLACEMENT",
    "karyawan lama mutasi": "REPLACEMENT",
    "karyawan lama promosi": "REPLACEMENT",
    "penambahan personil": "NEW",
    "jabatan baru": "NEW",
}

CATEGORIES = ["NEW", "REPLACEMENT"]
STATUSES = ["OP", "Closed", "Cancel"]
AVAILABILITY_TRUE = {"v", "y", "ya", "yes", "true", "1"}
AVAILABILITY_FALSE = {"x", "n", "tidak", "no", "false", "0"}

HEADER_ALIASES = {
    # Mirrors the canonical-header tolerance used by the legacy VBA compiler.
    # Do not force recruiters to rename a header when the legacy compiler treats
    # that header as the same semantic field.
    "Kode PIC": ["Kode PIC", "Kode Recruiter", "PIC Code"],
    "FPTK Date (Real)": ["FPTK Date (Real)", "FPTK Date Real", "Tanggal FPTK", "Tanggal FPTK Asli"],
    "Kode Angka": ["Kode Angka", "KODE", "Position Code", "Kode Posisi"],
    "FPTK Date (Kode)": [
        "FPTK Date (Kode)", "FPTK Date Kode", "FPTK Date", "FPTK Date (Pake Ini)",
        "FPTK Date Pake Ini", "FPTK Date (Code)", "FPTK Date Code",
    ],
    "Kode Unik": ["Kode Unik", "Unique Code"],
    "Posisi": ["Posisi", "Position", "Posisi - Kebutuhan TA", "Posisi Kebutuhan TA", "Nama Posisi"],
    "Business Unit": [
        "Business Unit", "PT/Business Unit", "PT / Business Unit", "PT Business Unit",
        "PT Unit", "BU",
    ],
    "Direktorat": ["Direktorat", "Directorate"],
    "Divisi": [
        "Divisi", "Division", "Divisi (Sesuai SO)", "Divisi Sesuai SO",
        "Divisi (Sesuai SO) 2", "Divisi Sesuai SO 2", "Division Chris",
    ],
    "Department": ["Department", "Departemen", "Department Chris"],
    "Level FPTK": ["Level FPTK", "Level FPTK (Sesuai SO)", "Level FPTK Sesuai SO", "Level Posisi", "Level"],
    "Level Number": ["Level Number", "Level Numeric", "Level No", "Nomor Level"],
    # IMPORTANT: Status FPTK is intentionally NOT an alias here. In the current
    # recruiter template/business rule it is treated as FPTK Availability.
    "Alasan Permintaan FPTK": ["Alasan Permintaan FPTK", "Alasan FPTK", "Alasan", "Category"],
    "Category FPTK": ["Category FPTK", "CATEGORY FPTK"],
    "PIC Recruiter": ["PIC Recruiter", "PIC Rekruter", "PIC Recruitment", "PIC TA", "Nama Rekruter", "Recruiter", "Rekruter"],
    "Filter Kategorisasi FPTK": [
        "Filter Kategorisasi FPTK", "Filter Kategorisasi FPTK2", "Filter Kategorisasi FPTK 2",
        "Filter Kategori FPTK", "Kategorisasi FPTK",
    ],
    "Vacancy": ["Vacancy", "Jumlah Posisi", "Jumlah Permintaan", "Jumlah Posisi Yang Dicari"],
    "Status": ["Status", "Status Rekrutmen", "Status Vacancy"],
    "Week FPTK Date (Kode)": ["Week FPTK Date (Kode)", "Week FPTK Date (Code)", "Week FPTK Date", "Week FPTK Date CODE"],
    "Month FPTK Date": ["Month FPTK Date"],
    "FPTK Cancel Date": ["FPTK Cancel Date", "Cancel Date", "Tanggal Cancel"],
    "Week Cancel Date": ["Week Cancel Date"],
    "Month Cancel Date": ["Month Cancel Date"],
    "Offering Date": ["Offering Date", "Tanggal Offering"],
    "Week Offering Date": ["Week Offering Date"],
    "Month Offering": ["Month Offering"],
    "Jumlah SLA": ["Jumlah SLA", "SLA Days", "SLA"],
    "Deadline pemenuhan SLA": ["Deadline pemenuhan SLA", "Deadline SLA", "SLA Deadline"],
    "Detail SLA": ["Detail SLA", "SLA Status", "Status SLA"],
    "Keterangan Lulus SLA": ["Keterangan Lulus SLA", 'Keterangan "1"', "Keterangan 1"],
    "Keterangan Tidak Lulus SLA": ["Keterangan Tidak Lulus SLA", 'Keterangan "0"', "Keterangan 0"],
    "Keterangan Cancel": ["Keterangan Cancel", "Keterangan Cancel [Kosong]", "Keterangan Cancel Kosong"],
    "Nama Kandidat": ["Nama Kandidat", "Kandidat", "Candidate Name"],
    "Estimasi Join": ["Estimasi Join", "Estimated Join Date", "Tanggal Join"],
    "Kebutuhan Laptop": ["Kebutuhan Laptop", "Kebutuhan Laptop (V)", "Kebutuhan Laptop V", "Laptop"],
    "Lokasi Onboarding": ["Lokasi Onboarding"],
    "Tanggal Upload ke Website": ["Tanggal Upload ke Website", "Tgl Upload ke Website", "Tanggal Upload Website"],
    "User (Manager)": ["User (Manager)", "User Manager", "User", "Manager"],
    "Indirect User": ["Indirect User"],
    "Lokasi Kerja": ["Lokasi Kerja", "Location", "Lokasi", "Penempatan"],
    "Lokasi HR": ["Lokasi HR", "HR Location"],
    "Status Karyawan": ["Status Karyawan", "Employment Status", "Employee Status", "Status Employee"],
    "Kode BU": ["Kode BU", "Kode BU2", "Kode BU 2", "BU Code"],
    "FPTK Availability": ["FPTK Availability", "Status FPTK", "Availability FPTK", "FPTK Available"],
    "Region": ["Region"],
    "NEW/REPLACEMENT": ["NEW/REPLACEMENT", "NEW - REPLACEMENT"],
    "Detail Kategori": ["Detail Kategori"],
    "Remarks": ["Remarks", "Remark", "Recruitment Update"],
}

REQUIRED_FPTK_HEADERS = [
    "Kode PIC", "FPTK Date (Real)", "Kode Unik", "Posisi", "Business Unit",
    "Direktorat", "Divisi", "Department", "Level FPTK", "Level Number",
    "Alasan Permintaan FPTK", "Category FPTK", "PIC Recruiter", "Vacancy", "Status",
]



INSTRUCTION_MARKERS = [
    "dropdown",
    "sesuai detail fptk",
    "sesuai detail",
    "sesuai so",
    "sesuai detail posisi",
    "tanggal fptk asli",
    "diisi ketika",
    "diisi '1'",
    'diisi "1"',
    "diisi 1",
    "fptk 2025 ditulis",
    "fptk 2026",
    "tanggal valid",
    "read only",
    "readonly",
    "kolom bantu",
    "petunjuk",
    "guidance",
]


def _guidance_cell_score(raw) -> int:
    """Return a small score when a cell looks like template guidance, not business data."""
    raw_text = clean_text(raw)
    txt = key_text(raw)
    if not txt:
        return 0

    score = 0
    stripped = raw_text.lstrip()

    # The recruiter template frequently writes helper text as "> Dropdown",
    # "> Sesuai SO", etc. A leading chevron is a very strong signal.
    if stripped.startswith(">"):
        score += 3

    for marker in INSTRUCTION_MARKERS:
        if marker in txt:
            score += 1

    # Common instruction-like starts used by the workbook templates.
    if txt.startswith(("sesuai ", "diisi ", "isi ", "gunakan ", "pilih ", "contoh ")):
        score += 1

    return score


def is_instruction_helper_row(ws, row: int, mapping: dict[str, int], header_row: int) -> bool:
    """Detect the helper/instruction row immediately under the header.

    New compile rule requested for the Streamlit uploader:
    - helper rows are NEVER validated;
    - helper rows are NEVER compiled;
    - if headers are on Excel row 1, row 2 is skipped as soon as it contains
      a clear template-guidance signal such as ``> Dropdown``, ``> Sesuai SO``
      or ``Diisi ...``.

    We still avoid blindly deleting a legitimate first data row. A real row 2 with
    normal business values and no guidance signal continues to be validated.
    """
    if row != header_row + 1:
        return False

    populated = 0
    guidance_cells = 0
    guidance_score = 0
    values = []

    # Mapping values can contain the same physical column through aliases, so only
    # inspect each Excel column once.
    for col in sorted(set(mapping.values())):
        raw = ws.cell(row, col).value
        txt = clean_text(raw)
        if not txt:
            continue
        populated += 1
        values.append(txt)
        cell_score = _guidance_cell_score(raw)
        if cell_score > 0:
            guidance_cells += 1
            guidance_score += cell_score

    if populated == 0:
        return False

    # Exact case discussed in testing: header row = 1, helper row = 2.
    # One unmistakable helper cell is enough to suppress row 2 entirely.
    if header_row == 1 and row == 2 and guidance_score >= 2:
        return True

    # Other template layouts may have their header on row 2. Require multiple
    # guidance cells there to avoid hiding a broken but genuine first record.
    guidance_ratio = guidance_cells / populated
    if guidance_cells >= 2 and (guidance_score >= 4 or guidance_ratio >= 0.25):
        return True

    # Strong fallback for verbose instruction rows.
    blob = " | ".join(key_text(v) for v in values)
    marker_hits = sum(1 for marker in INSTRUCTION_MARKERS if marker in blob)
    return marker_hits >= 3

SOURCING_HEADER_ALIASES = {
    "Sourcing Date": ["Sourcing Date", "Tanggal Sourcing Date", "Tanggal Sourcing"],
    "Kode Unik": [
        "Kode Unik", "Kode Unik (copy value dari FPTK)", "Kode Unik Copy Value Dari FPTK",
    ],
    "Posisi": ["Posisi", "Position", "Posisi - Kebutuhan TA", "Posisi Kebutuhan TA"],
    "Nama": ["Nama", "Nama Kandidat", "Candidate Name"],
    "Email": ["Email", "Email Address"],
    "Nomor HP": ["Nomor HP", "No HP", "Phone", "Phone Number"],
    "Rekruter": ["Rekruter", "Recruiter", "PIC Recruiter", "PIC Rekruter"],
    "Model Rekrutmen": [
        "Model Rekrutmen", "Model Rekrutmen (Lihat di Sheet Flow Map Model)",
        "Model Rekrutmen (Lihat Dropdown)", "Model (Lihat Dropdown)", "Model", "Recruitment Model",
    ],
    "Sumber Sourcing": ["Sumber Sourcing", "Sourcing Source", "Source"],
}


@dataclass
class ValidationIssue:
    severity: str
    sheet: str
    row: int | None
    field: str
    current: str
    expected: str
    fix: str

    def as_dict(self):
        return asdict(self)


@dataclass
class ValidationResult:
    source_type: str
    issues: list[ValidationIssue]
    counts: dict
    normalized_fptk: list[dict]
    normalized_sourcing: list[dict]
    normalized_blacklist: list[dict]

    @property
    def errors(self):
        return [x for x in self.issues if x.severity == "ERROR"]

    @property
    def warnings(self):
        return [x for x in self.issues if x.severity == "WARNING"]

    @property
    def passed(self):
        return len(self.errors) == 0

    def issue_rows(self):
        return [x.as_dict() for x in self.issues]


def clean_text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def key_text(value) -> str:
    return clean_text(value).casefold()


def canonical_from(value, allowed: list[str]) -> str | None:
    k = key_text(value)
    for x in allowed:
        if key_text(x) == k:
            return x
    return None


def normalize_header(value) -> str:
    """Normalize headers like the VBA HeaderKeyText/SchemaNormalize layer.

    Punctuation, brackets, slashes, underscores, line breaks and repeated spaces
    must not make semantically identical legacy headers look different.
    """
    s = clean_text(value).upper().replace("_", " ")
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _split_aliases(raw) -> list[str]:
    """Split VBA Schema_Config alias text (normally pipe-delimited)."""
    text = clean_text(raw)
    if not text:
        return []
    # VBA registry commonly uses |, but tolerate ; and line breaks from copied sheets.
    parts = re.split(r"[|;\n\r]+", str(raw))
    return [clean_text(x) for x in parts if clean_text(x)]


def _schema_config_aliases(wb, database_key: str) -> dict[str, list[str]]:
    """Read canonical/header/aliases directly from uploaded workbook Schema_Config.

    This mirrors the VBA schema overlay: physical header names are resolved through
    Header Name + Canonical Header + Aliases rather than one exact header string.
    """
    if wb is None or "Schema_Config" not in wb.sheetnames:
        return {}

    ws = wb["Schema_Config"]
    # Find Schema_Config's own header row safely.
    header_row = None
    cols = {}
    for r in range(1, min(ws.max_row, 10) + 1):
        tmp = {}
        for c in range(1, ws.max_column + 1):
            k = normalize_header(ws.cell(r, c).value)
            if k:
                tmp[k] = c
        if "DATABASE" in tmp and ("HEADER NAME" in tmp or "CANONICAL HEADER" in tmp):
            header_row, cols = r, tmp
            break
    if not header_row:
        return {}

    db_col = cols.get("DATABASE")
    hn_col = cols.get("HEADER NAME")
    alias_col = cols.get("ALIASES")
    canonical_col = cols.get("CANONICAL HEADER")
    active_col = cols.get("ACTIVE")

    out: dict[str, list[str]] = {}
    target_db = normalize_header(database_key)
    for r in range(header_row + 1, ws.max_row + 1):
        db = normalize_header(ws.cell(r, db_col).value if db_col else None)
        if db != target_db:
            continue
        if active_col:
            active = key_text(ws.cell(r, active_col).value)
            if active in {"n", "no", "tidak", "false", "0", "x"}:
                continue

        header_name = clean_text(ws.cell(r, hn_col).value if hn_col else None)
        canonical = clean_text(ws.cell(r, canonical_col).value if canonical_col else None)
        aliases = _split_aliases(ws.cell(r, alias_col).value if alias_col else None)
        canonical = canonical or header_name
        if not canonical:
            continue

        bucket = out.setdefault(canonical, [])
        for value in [canonical, header_name, *aliases]:
            value = clean_text(value)
            if value and normalize_header(value) not in {normalize_header(x) for x in bucket}:
                bucket.append(value)
    return out


def merge_alias_maps(*maps: dict[str, list[str]]) -> dict[str, list[str]]:
    """Merge built-in + workbook schema aliases by normalized canonical name."""
    merged: dict[str, list[str]] = {}
    canonical_index: dict[str, str] = {}
    for amap in maps:
        for canonical, aliases in (amap or {}).items():
            norm_can = normalize_header(canonical)
            actual_can = canonical_index.get(norm_can)
            if actual_can is None:
                actual_can = canonical
                canonical_index[norm_can] = actual_can
                merged[actual_can] = []
            seen = {normalize_header(x) for x in merged[actual_can]}
            for alias in [canonical, *(aliases or [])]:
                alias = clean_text(alias)
                if alias and normalize_header(alias) not in seen:
                    merged[actual_can].append(alias)
                    seen.add(normalize_header(alias))
    return merged


def runtime_alias_map(wb, database_key: str, builtins: dict[str, list[str]]) -> dict[str, list[str]]:
    """Alias registry used by validation/compile for the current uploaded workbook."""
    schema = _schema_config_aliases(wb, database_key)

    # Schema_Config canonical names may differ in casing/wording from our Python
    # canonical keys. Fold schema aliases into the matching built-in canonical key
    # whenever normalized canonical/header names intersect.
    result = {k: list(v) for k, v in builtins.items()}
    builtin_lookup = {}
    for canonical, aliases in builtins.items():
        for x in [canonical, *aliases]:
            builtin_lookup[normalize_header(x)] = canonical

    for schema_canonical, aliases in schema.items():
        target = builtin_lookup.get(normalize_header(schema_canonical))
        if target is None:
            for alias in aliases:
                target = builtin_lookup.get(normalize_header(alias))
                if target:
                    break
        target = target or schema_canonical
        result.setdefault(target, [])
        seen = {normalize_header(x) for x in result[target]}
        for alias in [schema_canonical, *aliases]:
            if alias and normalize_header(alias) not in seen:
                result[target].append(alias)
                seen.add(normalize_header(alias))
    return result


def alias_lookup(alias_map: dict[str, list[str]]) -> dict[str, str]:
    out = {}
    for canonical, aliases in alias_map.items():
        for alias in [canonical, *(aliases or [])]:
            key = normalize_header(alias)
            if key:
                out[key] = canonical
    return out


def find_header_row(ws, required_any: list[str], alias_map: dict[str, list[str]], max_scan: int = 20) -> tuple[int, dict[str, int]]:
    """Find the physical header row using VBA-style canonical/alias matching.

    We score every recognized semantic header, not only the two identity fields.
    This prevents a guidance/title row from winning just because it contains one
    word such as 'Position'.
    """
    lookup = alias_lookup(alias_map)
    wanted = set(required_any)
    best_row = 1
    best_mapping: dict[str, int] = {}
    best_tuple = (-1, -1)

    for r in range(1, min(ws.max_row, max_scan) + 1):
        mapping: dict[str, int] = {}
        for c in range(1, ws.max_column + 1):
            canonical = lookup.get(normalize_header(ws.cell(r, c).value))
            if canonical and canonical not in mapping:
                mapping[canonical] = c

        required_score = len(wanted.intersection(mapping))
        semantic_score = len(mapping)
        score = (required_score, semantic_score)
        if score > best_tuple:
            best_row, best_mapping, best_tuple = r, mapping, score

        if wanted.issubset(mapping) and semantic_score >= max(3, len(wanted)):
            # Continue only if this is a very weak two-column row; otherwise this
            # is already a credible header row.
            return r, mapping

    return best_row, best_mapping

def raw_display(value) -> str:
    if value is None:
        return "[Blank]"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M:%S")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    s = clean_text(value)
    return s if s else "[Blank]"


def _date_format_order(number_format: str | None) -> str | None:
    """Return DMY/MDY when Excel's display format makes the order clear.

    Excel stores real dates as serial numbers, so a datetime value is already a
    resolved date. The number format is only used as a hint for text dates in the
    same column, never as a reason to reject an Excel-native date.
    """
    fmt = (number_format or "").lower()
    if not fmt:
        return None

    # Remove literals / locale decorations enough for common Excel formats.
    fmt = re.sub(r'"[^"]*"', '', fmt)
    fmt = re.sub(r'\[[^\]]*\]', '', fmt)
    fmt = fmt.replace('\\', '').split(';')[0].strip()

    # Ignore time suffixes when looking at date order.
    date_part = re.split(r'\s+[hHsS]', fmt, maxsplit=1)[0]
    d_pos = date_part.find('d')
    m_pos = date_part.find('m')
    y_pos = date_part.find('y')
    if d_pos < 0 or m_pos < 0 or y_pos < 0:
        return None
    return "DMY" if d_pos < m_pos else "MDY"


def _text_date_parts(value) -> tuple[int, int, int] | None:
    """Extract three numeric date components, tolerating an Excel-like time suffix."""
    text = clean_text(value)
    if not text:
        return None
    # e.g. "12/10/2025 00:00:00" -> "12/10/2025"
    text = re.split(r"\s+", text, maxsplit=1)[0]
    m = re.fullmatch(r"(\d{1,4})[\-/\.](\d{1,2})[\-/\.](\d{1,4})", text)
    if not m:
        return None
    return tuple(int(x) for x in m.groups())


def infer_date_order(ws, col: int | None, start_row: int, end_row: int, sample_limit: int = 250) -> str:
    """Infer whether a source date column is DMY or MDY.

    Priority:
    1. Excel cell number formats (strongest signal)
    2. Unambiguous text values (e.g. 25/01 => DMY, 01/25 => MDY)
    3. Recruitment default = DMY
    """
    if not col:
        return "DMY"

    scores = {"DMY": 0, "MDY": 0}
    checked = 0
    for r in range(start_row, end_row + 1):
        if checked >= sample_limit:
            break
        cell = ws.cell(r, col)
        value = cell.value
        if value is None or clean_text(value) == "":
            continue
        checked += 1

        fmt_order = _date_format_order(getattr(cell, "number_format", None))
        if fmt_order:
            scores[fmt_order] += 4

        # Real Excel datetime/date values are already resolved. We only use
        # their display format as an order hint and never reject them.
        if isinstance(value, (datetime, date)):
            continue

        parts = _text_date_parts(value)
        if not parts:
            continue
        a, b, _ = parts
        if a > 12 and b <= 12:
            scores["DMY"] += 3
        elif b > 12 and a <= 12:
            scores["MDY"] += 3

    if scores["MDY"] > scores["DMY"]:
        return "MDY"
    return "DMY"


def parse_excel_date(cell, date_order: str = "DMY") -> tuple[date | None, str | None]:
    """Parse an Excel date without falsely rejecting native datetime cells.

    - Excel-native date/datetime is always valid and normalized to a date.
    - Text may include a zero-time suffix.
    - Text is interpreted using the inferred column convention (DMY/MDY).
    - ISO yyyy-mm-dd is accepted as an unambiguous date.
    """
    if cell is None:
        return None, "blank"
    value = cell.value
    if value is None or clean_text(value) == "":
        return None, "blank"

    if isinstance(value, datetime):
        return value.date(), None
    if isinstance(value, date):
        return value, None

    text = clean_text(value)
    if not text:
        return None, "blank"
    date_text = re.split(r"\s+", text, maxsplit=1)[0]

    # ISO is unambiguous regardless of source convention.
    if re.fullmatch(r"\d{4}[\-/]\d{1,2}[\-/]\d{1,2}", date_text):
        normalized = date_text.replace('/', '-')
        try:
            return datetime.strptime(normalized, "%Y-%m-%d").date(), None
        except ValueError:
            return None, "invalid calendar date"

    parts = _text_date_parts(date_text)
    if not parts:
        return None, f"not a recognizable date ({date_order})"

    a, b, y = parts
    if y < 100:
        y += 2000 if y < 70 else 1900

    try:
        if date_order == "MDY":
            month, day = a, b
        else:
            day, month = a, b
        return date(y, month, day), None
    except ValueError:
        return None, f"invalid calendar date for {date_order}"


# Backwards-compatible name used by the rest of the compiler.
def strict_ddmmyyyy(cell, date_order: str = "DMY") -> tuple[date | None, str | None]:
    return parse_excel_date(cell, date_order)


def optional_strict_date(cell, date_order: str = "DMY") -> tuple[date | None, str | None]:
    if cell is None or cell.value is None or clean_text(cell.value) == "":
        return None, None
    return parse_excel_date(cell, date_order)

def cell_for(ws, row: int, mapping: dict[str, int], canonical: str):
    col = mapping.get(canonical)
    return ws.cell(row, col) if col else None


def value_for(ws, row: int, mapping: dict[str, int], canonical: str):
    cell = cell_for(ws, row, mapping, canonical)
    return cell.value if cell else None


def row_has_data(ws, row: int, mapping: dict[str, int]) -> bool:
    for col in mapping.values():
        v = ws.cell(row, col).value
        if v is not None and clean_text(v) != "":
            return True
    return False


def _issue(issues, sheet, row, field, current, expected, fix, severity="ERROR"):
    issues.append(ValidationIssue(severity, sheet, row, field, raw_display(current), expected, fix))


def normalize_availability_text(v) -> str | None:
    k = key_text(v)
    if not k:
        return None
    if k in AVAILABILITY_TRUE:
        return "Y"
    if k in AVAILABILITY_FALSE:
        return "N"
    return None


def _validate_headers(ws, mapping, required, issues):
    for field in required:
        if field not in mapping:
            _issue(
                issues, ws.title, 1, field, "Header tidak ditemukan", field,
                f"Tambahkan header '{field}' sesuai template sebelum upload.",
            )


def _add_two_way_relation_warnings(issues, normalized_fptk: list[dict], normalized_sourcing: list[dict]) -> None:
    """Add non-blocking integrity warnings between FPTK and DB Sourcing.

    Rules:
    - DB Sourcing code without any FPTK: keep as Unlinked; do not auto-create FPTK.
    - FPTK code without any DB Sourcing: FPTK still compiles, but funnel/progress can be zero.

    Central Master is considered so a re-upload does not warn when the relationship
    already exists from an earlier successful compile.
    """
    uploaded_codes = {key_text(x.get("Kode Unik")) for x in normalized_fptk if clean_text(x.get("Kode Unik"))}
    sourcing_codes = {key_text(x.get("Kode Unik")) for x in normalized_sourcing if clean_text(x.get("Kode Unik"))}

    with session_scope() as s:
        central_fptk = s.execute(select(FPTK.id, FPTK.kode_unik)).all()
        central_code_to_ids = defaultdict(list)
        for fptk_id, kode_unik in central_fptk:
            if clean_text(kode_unik):
                central_code_to_ids[key_text(kode_unik)].append(int(fptk_id))

        linked_fptk_ids = set(s.scalars(select(Application.fptk_id).distinct()).all())
        central_codes_with_sourcing = {
            code_key
            for code_key, ids in central_code_to_ids.items()
            if any(fptk_id in linked_fptk_ids for fptk_id in ids)
        }

    # Direction A: DB Sourcing exists but FPTK does not exist anywhere.
    missing_parent_codes = sourcing_codes - uploaded_codes - set(central_code_to_ids)
    if missing_parent_codes:
        for rec in normalized_sourcing:
            code = clean_text(rec.get("Kode Unik"))
            if key_text(code) in missing_parent_codes:
                _issue(
                    issues,
                    "DB Sourcing",
                    rec.get("__row__"),
                    "Kode Unik",
                    code,
                    "Kode Unik tidak ditemukan di FPTK (warning)",
                    "DB Sourcing tetap disimpan sebagai Unlinked dan TIDAK membuat FPTK baru. Akibatnya data kandidat ini belum bisa ditarik ke Funneling/Recruitment Progress sampai Kode Unik diperbaiki dan di-link ke FPTK yang benar.",
                    severity="WARNING",
                )

    # Direction B: FPTK exists but no sourcing exists in this upload or Central Master.
    fptk_without_sourcing = {
        code for code in uploaded_codes
        if code not in sourcing_codes and code not in central_codes_with_sourcing
    }
    if fptk_without_sourcing:
        for rec in normalized_fptk:
            code = clean_text(rec.get("Kode Unik"))
            if key_text(code) in fptk_without_sourcing:
                status = clean_text(rec.get("Status")) or "-"
                _issue(
                    issues,
                    "FPTK",
                    rec.get("__row__"),
                    "DB Sourcing",
                    f"Tidak ditemukan untuk Kode Unik {code}",
                    "Warning saja — FPTK tetap di-compile",
                    f"FPTK Status {status} tetap masuk Central Master. Namun belum ada DB Sourcing yang terhubung, sehingga Funneling/Recruitment Progress untuk FPTK ini dapat terlihat 0 semua sampai data sourcing tersedia.",
                    severity="WARNING",
                )


def validate_recruiter_workbook(wb, user: dict) -> ValidationResult:
    issues: list[ValidationIssue] = []
    normalized_fptk: list[dict] = []
    normalized_sourcing: list[dict] = []
    normalized_blacklist: list[dict] = []
    counts = {"fptk": 0, "sourcing": 0, "blacklist": 0}

    if "FPTK" not in wb.sheetnames:
        _issue(issues, "Workbook", None, "Sheet FPTK", "Tidak ditemukan", "Sheet FPTK", "Gunakan file database recruiter yang memiliki sheet FPTK.")
        return ValidationResult("RECRUITER", issues, counts, [], [], [])

    ws = wb["FPTK"]
    fptk_aliases = runtime_alias_map(wb, "FPTK", HEADER_ALIASES)
    header_row, mapping = find_header_row(ws, ["Kode Unik", "Posisi"], fptk_aliases)
    _validate_headers(ws, mapping, REQUIRED_FPTK_HEADERS, issues)
    if issues:
        return ValidationResult("RECRUITER", issues, counts, [], [], [])

    code_rows = defaultdict(list)

    # Detect the actual date convention used by each Excel date column.
    # Native Excel date/datetime values are accepted regardless of display format;
    # this order is mainly needed for textual dates.
    date_orders = {
        field: infer_date_order(ws, mapping.get(field), header_row + 1, ws.max_row)
        for field in [
            "FPTK Date (Real)", "FPTK Date (Kode)", "FPTK Cancel Date",
            "Offering Date", "Estimasi Join", "Tanggal Upload ke Website",
        ]
    }

    for r in range(header_row + 1, ws.max_row + 1):
        if not row_has_data(ws, r, mapping):
            continue
        if is_instruction_helper_row(ws, r, mapping, header_row):
            # Template helper/guidance row: not data, not an error, never compiled.
            continue
        counts["fptk"] += 1
        rec = {"__row__": r}

        # 1 Kode PIC
        kode_pic = clean_text(value_for(ws, r, mapping, "Kode PIC"))
        if not kode_pic:
            _issue(issues, "FPTK", r, "Kode PIC", None, "Wajib terisi", "Isi Kode PIC recruiter pada row ini.")
        rec["Kode PIC"] = kode_pic or None

        # 2 FPTK Date Real strict
        date_cell = cell_for(ws, r, mapping, "FPTK Date (Real)")
        fptk_date, err = strict_ddmmyyyy(date_cell, date_orders["FPTK Date (Real)"])
        if err:
            _issue(issues, "FPTK", r, "FPTK Date (Real)", date_cell.value if date_cell else None, "Tanggal Excel yang valid", "Isi tanggal yang valid. Sistem membaca format tanggal dari kolom Excel dan menormalkan hasil ke dd/mm/yyyy.")
        rec["FPTK Date (Real)"] = fptk_date

        # Optional code date, if populated must be strict.
        code_date_cell = cell_for(ws, r, mapping, "FPTK Date (Kode)")
        code_date, code_err = optional_strict_date(code_date_cell, date_orders["FPTK Date (Kode)"])
        if code_err:
            _issue(issues, "FPTK", r, "FPTK Date (Kode)", code_date_cell.value, "Tanggal Excel yang valid", "Isi tanggal FPTK Date (Kode) yang valid; sistem akan membaca convention tanggal dari Excel.")
        rec["FPTK Date (Kode)"] = code_date

        # 3 Kode Unik
        kode_unik = clean_text(value_for(ws, r, mapping, "Kode Unik"))
        if not kode_unik:
            _issue(issues, "FPTK", r, "Kode Unik", None, "Wajib terisi dan unique", "Generate/perbaiki Kode Unik sebelum upload.")
        else:
            code_rows[kode_unik.casefold()].append(r)
        rec["Kode Unik"] = kode_unik or None

        # 4 Position
        position = clean_text(value_for(ws, r, mapping, "Posisi"))
        if not position:
            _issue(issues, "FPTK", r, "Posisi", None, "Wajib terisi", "Isi nama posisi sebelum upload.")
        rec["Posisi"] = position or None

        # 5 BU
        raw_bu = clean_text(value_for(ws, r, mapping, "Business Unit"))
        bu = canonical_from(raw_bu, BUSINESS_UNITS)
        if not bu:
            _issue(issues, "FPTK", r, "Business Unit", raw_bu, "Salah satu Business Unit resmi", "Gunakan salah satu: " + " | ".join(BUSINESS_UNITS))
        rec["Business Unit"] = bu or raw_bu or None

        # 6 Directorate
        raw_dir = clean_text(value_for(ws, r, mapping, "Direktorat"))
        directorate = canonical_from(raw_dir, DIRECTORATES)
        if not directorate:
            suggestions = OLD_DIRECTORATE_MAP.get(key_text(raw_dir), [])
            expected = " | ".join(suggestions) if suggestions else "Salah satu Direktorat resmi"
            fix = ("Ganti nama Direktorat lama menjadi: " + " / ".join(suggestions)) if suggestions else ("Gunakan salah satu Direktorat resmi: " + " | ".join(DIRECTORATES))
            _issue(issues, "FPTK", r, "Direktorat", raw_dir, expected, fix)
        rec["Direktorat"] = directorate or raw_dir or None

        # 7 org + level
        for field in ["Divisi", "Department"]:
            val = clean_text(value_for(ws, r, mapping, field))
            if not val:
                _issue(issues, "FPTK", r, field, None, "Wajib terisi", f"Isi {field} sesuai struktur organisasi.")
            rec[field] = val or None

        raw_level = clean_text(value_for(ws, r, mapping, "Level FPTK")).upper()
        if not re.fullmatch(r"[1-5][A-Z]", raw_level):
            _issue(issues, "FPTK", r, "Level FPTK", raw_level, "Format level seperti 1A, 2B, 3A, 4B, dst.", "Gunakan kode level jabatan, bukan nama fungsi/department.")
        rec["Level FPTK"] = raw_level or None

        raw_level_num = value_for(ws, r, mapping, "Level Number")
        try:
            if raw_level_num is None or clean_text(raw_level_num) == "":
                raise ValueError
            level_num_float = float(raw_level_num)
            if not level_num_float.is_integer():
                raise ValueError
            level_num = int(level_num_float)
        except Exception:
            level_num = None
            _issue(issues, "FPTK", r, "Level Number", raw_level_num, "Angka level dari Level FPTK", "Contoh: Level FPTK 3A harus memiliki Level Number 3.")
        if level_num is not None and re.fullmatch(r"[1-5][A-Z]", raw_level) and level_num != int(raw_level[0]):
            _issue(issues, "FPTK", r, "Level Number", raw_level_num, raw_level[0], f"Ubah Level Number menjadi {raw_level[0]} agar sama dengan Level FPTK {raw_level}.")
        rec["Level Number"] = level_num

        # Reason + category cross validation
        raw_reason = clean_text(value_for(ws, r, mapping, "Alasan Permintaan FPTK"))
        reason = canonical_from(raw_reason, REQUEST_REASONS)
        if not reason:
            _issue(issues, "FPTK", r, "Alasan Permintaan FPTK", raw_reason, " | ".join(REQUEST_REASONS), "Pilih alasan dari daftar standar FPTK.")
        rec["Alasan Permintaan FPTK"] = reason or raw_reason or None

        raw_cat = clean_text(value_for(ws, r, mapping, "Category FPTK")).upper()
        cat = canonical_from(raw_cat, CATEGORIES)
        if not cat:
            _issue(issues, "FPTK", r, "Category FPTK", raw_cat, "NEW atau REPLACEMENT", "Gunakan Category FPTK NEW / REPLACEMENT.")
        expected_cat = REASON_TO_CATEGORY.get(key_text(reason or raw_reason))
        if cat and expected_cat and cat != expected_cat:
            _issue(issues, "FPTK", r, "Category FPTK", cat, expected_cat, f"Alasan '{reason}' harus masuk Category FPTK {expected_cat}.")
        rec["Category FPTK"] = cat or raw_cat or None

        pic = clean_text(value_for(ws, r, mapping, "PIC Recruiter"))
        if not pic:
            _issue(issues, "FPTK", r, "PIC Recruiter", None, "Wajib terisi", "Isi PIC Recruiter yang menangani FPTK.")
        rec["PIC Recruiter"] = pic or None

        vacancy_raw = value_for(ws, r, mapping, "Vacancy")
        try:
            vacancy_f = float(vacancy_raw)
            if not vacancy_f.is_integer() or vacancy_f <= 0:
                raise ValueError
            vacancy = int(vacancy_f)
        except Exception:
            vacancy = None
            _issue(issues, "FPTK", r, "Vacancy", vacancy_raw, "Bilangan bulat > 0", "Isi jumlah kebutuhan posisi, minimal 1.")
        rec["Vacancy"] = vacancy

        raw_status = clean_text(value_for(ws, r, mapping, "Status"))
        status = canonical_from(raw_status, STATUSES)
        if not status:
            _issue(issues, "FPTK", r, "Status", raw_status, "OP / Closed / Cancel", "Gunakan hanya OP, Closed, atau Cancel.")
        rec["Status"] = status or raw_status or None

        cancel_cell = cell_for(ws, r, mapping, "FPTK Cancel Date")
        cancel_date, cancel_err = optional_strict_date(cancel_cell, date_orders["FPTK Cancel Date"])
        if cancel_err:
            _issue(issues, "FPTK", r, "FPTK Cancel Date", cancel_cell.value, "Tanggal Excel yang valid", "Isi tanggal Cancel yang valid; sistem akan membaca convention tanggal dari Excel.")
        offering_cell = cell_for(ws, r, mapping, "Offering Date")
        offering_date, offering_err = optional_strict_date(offering_cell, date_orders["Offering Date"])
        if offering_err:
            _issue(issues, "FPTK", r, "Offering Date", offering_cell.value, "Tanggal Excel yang valid", "Isi Offering Date yang valid; sistem akan membaca convention tanggal dari Excel.")
        if status == "Cancel" and not cancel_date:
            _issue(issues, "FPTK", r, "FPTK Cancel Date", cancel_cell.value if cancel_cell else None, "Wajib diisi karena Status = Cancel", "Isi tanggal FPTK dibatalkan dengan format dd/mm/yyyy.")
        if status == "Closed" and not offering_date:
            _issue(issues, "FPTK", r, "Offering Date", offering_cell.value if offering_cell else None, "Wajib diisi karena Status = Closed", "Isi Offering Date dengan format dd/mm/yyyy.")
        if status == "OP" and cancel_date:
            _issue(issues, "FPTK", r, "Status", status, "Cancel", "Cancel Date sudah terisi. Ubah Status menjadi Cancel atau hapus Cancel Date jika memang masih OP.")
        if status == "OP" and offering_date:
            _issue(issues, "FPTK", r, "Status", status, "Closed", "Offering Date sudah terisi. Ubah Status menjadi Closed atau hapus Offering Date jika belum closed.")
        rec["FPTK Cancel Date"] = cancel_date
        rec["Offering Date"] = offering_date

        # Extra mapped fields are preserved for compile.
        for field in [
            "Kode Angka", "Filter Kategorisasi FPTK", "Nama Kandidat", "Estimasi Join",
            "Kebutuhan Laptop", "Lokasi Onboarding", "Tanggal Upload ke Website", "User (Manager)",
            "Indirect User", "Lokasi Kerja", "Lokasi HR", "Status Karyawan", "Kode BU",
            "Region", "NEW/REPLACEMENT", "Detail Kategori", "Remarks",
        ]:
            if field in mapping:
                rec[field] = value_for(ws, r, mapping, field)

        if "FPTK Availability" in mapping:
            raw_av = value_for(ws, r, mapping, "FPTK Availability")
            av = normalize_availability_text(raw_av)
            if clean_text(raw_av) and not av:
                _issue(issues, "FPTK", r, "FPTK Availability", raw_av, "Y/N (V/X, Ya/Tidak juga dikenali)", "Perbaiki nilai availability.")
            rec["FPTK Availability"] = av

        normalized_fptk.append(rec)

    # Duplicate Kode Unik inside uploaded file = hard fail.
    for code, rows in code_rows.items():
        if len(rows) > 1:
            row_text = ", ".join(map(str, rows))
            for r in rows:
                _issue(issues, "FPTK", r, "Kode Unik", value_for(ws, r, mapping, "Kode Unik"), "Unique di seluruh file", f"Kode Unik ini muncul di row {row_text}. Perbaiki Kode PIC / Kode Angka / FPTK Date (Kode), lalu generate ulang Kode Unik.")

    # Check collision against Central Master.
    codes = [x["Kode Unik"] for x in normalized_fptk if x.get("Kode Unik")]
    if codes:
        with session_scope() as s:
            central = s.scalars(select(FPTK).where(FPTK.kode_unik.in_(codes))).all()
            by_code = defaultdict(list)
            for obj in central:
                by_code[obj.kode_unik.casefold()].append(obj)
            own_by_entity = {
                x.entity_id: x
                for x in s.scalars(select(SourceOwnership).where(SourceOwnership.entity_type == "FPTK", SourceOwnership.entity_id.in_([x.id for x in central] or [-1]))).all()
            }
            source_by_code = {x["Kode Unik"].casefold(): x for x in normalized_fptk if x.get("Kode Unik")}
            for code_key, objs in by_code.items():
                src = source_by_code.get(code_key)
                if not src:
                    continue
                if len(objs) > 1:
                    _issue(issues, "FPTK", src["__row__"], "Kode Unik", src["Kode Unik"], "Satu record saja di Central Master", "Central Master masih memiliki duplicate legacy untuk Kode Unik ini. Minta Admin membersihkan duplicate sebelum upload.")
                    continue
                obj = objs[0]
                owner = own_by_entity.get(obj.id)
                if owner and owner.owner_user_id not in (None, user.get("id")):
                    _issue(issues, "FPTK", src["__row__"], "Kode Unik", src["Kode Unik"], f"Kode Unik milik source owner {owner.owner_name or owner.owner_email}", "Gunakan Kode Unik lain atau minta owner/admin melakukan transfer ownership. Data user lain tidak boleh ditimpa.")
                    continue
                if key_text(obj.position) != key_text(src.get("Posisi")):
                    _issue(issues, "FPTK", src["__row__"], "Posisi", src.get("Posisi"), obj.position, f"Kode Unik {src['Kode Unik']} sudah terdaftar untuk posisi '{obj.position}'. Perbaiki Kode Unik atau Posisi.")
                if obj.fptk_date and src.get("FPTK Date (Real)") and obj.fptk_date != src["FPTK Date (Real)"]:
                    _issue(issues, "FPTK", src["__row__"], "FPTK Date (Real)", src["FPTK Date (Real)"], obj.fptk_date.strftime("%d/%m/%Y"), f"Kode Unik {src['Kode Unik']} sudah ada dengan FPTK Date Real berbeda. Perbaiki source; compiler tidak akan insert duplicate Kode Unik.")

    # DB Sourcing: every populated row must have Sourcing Date.
    if "DB Sourcing" in wb.sheetnames:
        sws = wb["DB Sourcing"]
        sourcing_builtins = merge_alias_maps(HEADER_ALIASES, SOURCING_HEADER_ALIASES)
        sourcing_aliases = runtime_alias_map(wb, "DB Sourcing", sourcing_builtins)
        sh, smap = find_header_row(sws, ["Kode Unik", "Nama"], sourcing_aliases)
        if "Sourcing Date" not in smap:
            _issue(issues, "DB Sourcing", 1, "Sourcing Date", "Header tidak ditemukan", "Sourcing Date", "Tambahkan kolom Sourcing Date sesuai template.")
        else:
            sourcing_date_order = infer_date_order(
                sws, smap.get("Sourcing Date"), sh + 1, sws.max_row
            )
            for r in range(sh + 1, sws.max_row + 1):
                # A sourcing row counts when it has any nonblank cells in mapped/core area.
                if not row_has_data(sws, r, smap):
                    continue
                counts["sourcing"] += 1
                date_cell = cell_for(sws, r, smap, "Sourcing Date")
                sourcing_date, serr = strict_ddmmyyyy(date_cell, sourcing_date_order)
                if serr:
                    _issue(issues, "DB Sourcing", r, "Sourcing Date", date_cell.value if date_cell else None, "Tanggal Excel yang valid", "Setiap row DB Sourcing wajib memiliki Sourcing Date yang valid; sistem membaca convention tanggal dari kolom Excel.")
                # Preserve all columns by actual header for compile; normalized keys added for core fields.
                actual = {}
                for c in range(1, sws.max_column + 1):
                    h = clean_text(sws.cell(sh, c).value)
                    if h:
                        actual[h] = sws.cell(r, c).value

                # Also write canonical core keys resolved through VBA-compatible
                # aliases. This allows e.g. "Kode Unik (copy value dari FPTK)"
                # and "Posisi - Kebutuhan TA" to compile without renaming.
                for canonical, col in smap.items():
                    if col and canonical not in actual:
                        actual[canonical] = sws.cell(r, col).value

                actual["__row__"] = r
                actual["Sourcing Date"] = sourcing_date
                code = clean_text(actual.get("Kode Unik"))
                name = clean_text(actual.get("Nama"))
                if not code:
                    _issue(issues, "DB Sourcing", r, "Kode Unik", None, "Wajib terisi", "DB Sourcing harus terhubung ke FPTK melalui Kode Unik.")
                if not name:
                    _issue(issues, "DB Sourcing", r, "Nama", None, "Wajib terisi", "Isi nama kandidat agar record sourcing dapat di-compile.")
                normalized_sourcing.append(actual)



    # Blacklist: key is owner + No. Any populated row needs No + Candidate Name.
    if "Blacklist Candidate" in wb.sheetnames:
        bws = wb["Blacklist Candidate"]
        bh = 1
        headers = {normalize_header(bws.cell(bh, c).value): c for c in range(1, bws.max_column + 1)}
        def bcol(*names):
            for n in names:
                if normalize_header(n) in headers:
                    return headers[normalize_header(n)]
            return None
        no_col = bcol("No")
        name_col = bcol("Nama Kandidat", "Nama")
        for r in range(2, bws.max_row + 1):
            vals = [bws.cell(r, c).value for c in range(1, min(bws.max_column, 9) + 1)]
            if not any(v is not None and clean_text(v) != "" for v in vals):
                continue
            counts["blacklist"] += 1
            source_no = clean_text(bws.cell(r, no_col).value) if no_col else ""
            name = clean_text(bws.cell(r, name_col).value) if name_col else ""
            if not source_no:
                _issue(issues, "Blacklist Candidate", r, "No", None, "Wajib terisi", "Isi nomor blacklist. Nomor boleh sama dengan recruiter lain karena key-nya Owner + No.")
            if not name:
                _issue(issues, "Blacklist Candidate", r, "Nama Kandidat", None, "Wajib terisi", "Isi Nama Kandidat pada row blacklist.")
            rec = {"__row__": r, "No": source_no, "Nama Kandidat": name}
            for canonical, names in {
                "Last Update": ["Last Update"], "Business Unit": ["Business Unit"], "Posisi": ["Posisi"],
                "Lokasi": ["Lokasi"], "Kategori": ["Kategori"], "Alasan Tidak Proceed": ["Alasan Tidak Proceed"],
                "PIC Rekruter": ["PIC Rekruter", "PIC Recruiter"],
            }.items():
                col = bcol(*names)
                rec[canonical] = bws.cell(r, col).value if col else None
            normalized_blacklist.append(rec)

    # Non-blocking relation integrity check is intentionally last, after both
    # sheets have been normalized. It also runs when DB Sourcing sheet is absent.
    _add_two_way_relation_warnings(issues, normalized_fptk, normalized_sourcing)

    return ValidationResult("RECRUITER", issues, counts, normalized_fptk, normalized_sourcing, normalized_blacklist)


def validate_sto_workbook(wb, user: dict) -> ValidationResult:
    """STO is intentionally excluded from the strict recruiter validation rules.
    Only structural sanity required by the VBA STO sync is blocking.
    """
    issues: list[ValidationIssue] = []
    counts = {"fptk": 0, "sourcing": 0, "blacklist": 0}
    rows: list[dict] = []
    if "FPTK" not in wb.sheetnames:
        _issue(issues, "Workbook", None, "Sheet FPTK", "Tidak ditemukan", "Sheet FPTK", "File STO harus memiliki sheet FPTK.")
        return ValidationResult("STO", issues, counts, [], [], [])
    ws = wb["FPTK"]
    sto_aliases = runtime_alias_map(wb, "FPTK", HEADER_ALIASES)
    hr, mapping = find_header_row(ws, ["Posisi", "FPTK Availability"], sto_aliases)
    for field in ["Posisi", "FPTK Availability"]:
        if field not in mapping:
            _issue(issues, "FPTK", 1, field, "Header tidak ditemukan", field, "File STO membutuhkan Posisi dan Status FPTK/FPTK Availability.")
    if issues:
        return ValidationResult("STO", issues, counts, [], [], [])
    for r in range(hr + 1, ws.max_row + 1):
        if not row_has_data(ws, r, mapping):
            continue
        raw_av = value_for(ws, r, mapping, "FPTK Availability")
        av = normalize_availability_text(raw_av)
        if av not in {"Y", "N"}:
            continue
        pos = clean_text(value_for(ws, r, mapping, "Posisi"))
        if not pos:
            _issue(issues, "FPTK", r, "Posisi", None, "Wajib untuk row STO Y/N", "Isi Posisi pada row STO ini.")
            continue
        rec = {"__row__": r, "Posisi": pos, "FPTK Availability": av}
        for field in HEADER_ALIASES:
            if field in mapping:
                rec[field] = value_for(ws, r, mapping, field)
        rows.append(rec)
    counts["fptk"] = len(rows)
    return ValidationResult("STO", issues, counts, rows, [], [])
