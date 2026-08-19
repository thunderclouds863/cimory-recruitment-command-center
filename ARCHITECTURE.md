# Architecture

```text
Microsoft / Local Login
        │
        ▼
Streamlit Recruitment App
        │
        ├── FPTK Workspace
        ├── Candidate & CV
        ├── Pipeline Model 1–4
        ├── Monitoring / Evidence
        ├── Transfer FPTK
        ├── Dashboard
        └── Reporting / Export
        │
        ▼
SQLAlchemy
        │
        ▼
SQLite (dev) / PostgreSQL (prod)
        │
        ├── Web dashboard
        ├── MASTER_COMPILE_FPTK.xlsx
        ├── PNG charts
        └── CEO UPDATE.pptx
```

## Source-of-truth rule

1. Transaction data: FPTK, Candidate, Application, PipelineEvent.
2. Master data: PositionMaster, MappingUser, SchemaConfig, Users.
3. Derived data: Funneling, monitoring, recruiter performance, weekly trend, SLA.
4. Outputs: web dashboard, Excel snapshot, PowerPoint.

The same metric layer is reused by dashboard and export modules to minimize inconsistent numbers between channels.
