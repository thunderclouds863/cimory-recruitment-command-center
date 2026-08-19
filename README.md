# Recruitment Command Center — Compile-First V3

Streamlit recruitment database compiler rebuilt from the legacy Excel/VBA compile concept, with strict validation and central source ownership.

## Current priority

The active production workflow is:

```text
Recruiter / BU account
        ↓
Upload one or more Excel files
        ↓
Strict validation
        ↓
FAIL → 0 records compiled + correction report
PASS → Python compile
        ↓
Central Master
        ↓
All users can view
Owner/Admin can edit
```

Direct `Proses FPTK` input is intentionally still on hold. The active input channel for now is **Upload & Compile**.

## Account model

- 17 upload accounts: CMD, Brittney, Eli, Fiqra, Karin, Kenthansen, Kevin, Marta, Omega, Pauline, Salsa, Valendra, Victor, Zwei, JESS, MP, MS.
- 1 Admin account.
- Initial credentials are in `CREDENTIALS.md`.
- Password hashes are stored in the database.
- Users can change their password from the sidebar.
- Admin can reset passwords.

## Upload completion workflow

Every upload period is represented by an **Upload Cycle**.

Status per user:

```text
Belum Mulai
    ↓ first successful compile
Sedang Upload
    ↓ user clicks Done Uploading
Done
```

A user may upload multiple files. A successful file does **not** mean the user is done. Admin only sees `Done` after the user explicitly clicks **Done Uploading**.

If a user uploads another successful file after already being Done, the status automatically reopens to `Sedang Upload`.

Admin can create a new Upload Cycle at any time. The new cycle resets the 17 completion statuses while preserving Central Master and history.

## Strict FPTK validation

For normal recruiter files, blocking rules include:

- Kode PIC required.
- FPTK Date Real required and valid `dd/mm/yyyy`.
- Kode Unik required and unique within the uploaded file.
- Existing Kode Unik owned by another source account cannot be overwritten.
- Position required.
- Business Unit must use the approved canonical values.
- Directorate must use the approved new structure.
- Division and Department required.
- Level FPTK must follow codes such as `1A`, `2B`, `3A`, `4B`, etc.
- Level Number must match the numeric part of Level FPTK.
- Alasan Permintaan FPTK required and canonical.
- Category FPTK must agree with the reason.
- PIC Recruiter required.
- Vacancy must be numeric and greater than zero.
- Status only `OP`, `Closed`, or `Cancel`.
- `Closed` requires Offering Date.
- `Cancel` requires FPTK Cancel Date.
- DB Sourcing requires Sourcing Date for every populated sourcing row.

If one blocking error exists, that file is not compiled at all.

## Compile behavior

### FPTK

- Kode Unik is treated as the central identity for new validated uploads.
- Same owner's valid existing Kode Unik can update the existing record.
- Position or FPTK Date Real conflicts for the same Kode Unik block the upload.
- Week/Month fields are derived from dates instead of trusting user-entered week/month values.
- SLA:
  - Level 1–3 = 30 days
  - Level 4 = 45 days
  - Level 5 = 60 days
- Closed without Offering Date is treated as Data Incomplete as a calculation safeguard (normal validation should block it first).

### DB Sourcing

- Sourcing Date is mandatory.
- Blank source values do not overwrite existing nonblank candidate/application data.
- Candidate/application/pipeline records are linked back to FPTK.

### Blacklist

Blacklist source identity is:

```text
Source Owner + No
```

Therefore `No = 1` from different recruiter/source accounts remains separate.

### STO

Dedicated STO files use the STO compiler path and skip the normal recruiter FPTK validation rules. STO filenames beginning with `STO` (including names such as `STO(1).xlsm`) or containing `TULANG PUNGGUNG` are auto-detected.

`Y/V/Ya` and `N/X/Tidak` are normalized to availability and may insert/update STO records as required.

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Default local storage:

```text
data/recruitment.db
```

For cloud hosting use external PostgreSQL. See `HOSTING_STREAMLIT.md`.

## Important files

```text
app.py
core/auth.py
core/db.py
core/models.py
core/compile_rules.py
core/compile_engine.py
core/upload_cycles.py
views/compile_upload.py
views/admin.py
```

## Tests performed for this build

The build was smoke-tested against a fresh database for:

- 18 seeded accounts (17 upload users + Admin);
- 17 Upload Cycle members;
- `Belum Mulai → Sedang Upload → Done` state transition;
- successful upload after Done reopening the state to `Sedang Upload`;
- valid FPTK compile + ownership assignment;
- duplicate Kode Unik blocking validation;
- invalid upload producing zero Central Master FPTK records.
