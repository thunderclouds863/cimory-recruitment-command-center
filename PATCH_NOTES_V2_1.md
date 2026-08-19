# Recruitment Command Center V2.1 — Legacy Import Fix

## Fixed
- Fixed `UNIQUE constraint failed: fptk.kode_unik, fptk.position` during Master Compile import.
- Root cause: SQLAlchemy session uses `autoflush=False`; FPTKs queued from the FPTK sheet were not visible when DB Sourcing began, so the importer could queue the same FPTK a second time.
- FPTK import now uses an in-memory composite-key cache and an explicit flush before DB Sourcing.
- DB Sourcing links to FPTK using `(Kode Unik, Posisi)` first and only falls back to `Kode Unik` when it is unambiguous.
- DB Sourcing no longer creates phantom/stub FPTKs when the source FPTK does not exist; unmatched sourcing rows are counted as `sourcing_no_fptk`.
- Candidate/Application/Pipeline import is idempotent: re-importing the same workbook reuses existing core records.
- Reference tables (`DB Kode Posisi`, `Schema_Config`) avoid uncontrolled duplication on re-import.
- `Blacklist Candidate` is now imported.
- Temporary upload files are cleaned up after import.

## Performance / UX
- Header lookup is pre-normalized once per sheet rather than rebuilt for every field lookup.
- Large DB Sourcing imports run in batches.
- Admin Legacy Import now shows a progress bar while processing FPTK and DB Sourcing.

## Validation
- Regression case verified: one FPTK referenced repeatedly by DB Sourcing can be imported twice without duplicate FPTK/Application/Event rows.
- Tested against the real Master Compile structure on a 20,000-row DB Sourcing subset.
- The full Master Compile has ~85,750 DB Sourcing rows and may take several minutes on SQLite depending on laptop/storage speed; progress is now visible.
