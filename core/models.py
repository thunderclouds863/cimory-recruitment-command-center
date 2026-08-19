from __future__ import annotations
from datetime import datetime, date
from sqlalchemy import String, Integer, Float, Date, DateTime, Boolean, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(30), default="recruiter")
    recruiter_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    password_salt: Mapped[str | None] = mapped_column(String(128), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(256), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class FPTK(Base):
    __tablename__ = "fptk"
    __table_args__ = (UniqueConstraint("kode_unik", "position", name="uq_fptk_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kode_unik: Mapped[str] = mapped_column(String(120), index=True)
    kode_pic: Mapped[str | None] = mapped_column(String(50), nullable=True)
    kode_angka: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fptk_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    fptk_date_code: Mapped[date | None] = mapped_column(Date, nullable=True)
    position: Mapped[str] = mapped_column(String(255), index=True)
    business_unit: Mapped[str | None] = mapped_column(String(255), nullable=True)
    directorate: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    division: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    level_fptk: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    level_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    request_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category_fptk: Mapped[str | None] = mapped_column(String(120), nullable=True)
    filter_category: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    vacancy: Mapped[int] = mapped_column(Integer, default=1)
    pic_recruiter: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="OP", index=True)
    fptk_availability: Mapped[bool] = mapped_column(Boolean, default=True)
    cancel_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    offering_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    candidate_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estimated_join: Mapped[date | None] = mapped_column(Date, nullable=True)
    laptop_needed: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website_upload_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    manager_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    indirect_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hr_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    employee_status: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bu_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    new_replacement: Mapped[str | None] = mapped_column(String(50), nullable=True)
    detail_category: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sla_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline_sla: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    sla_result: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    applications: Mapped[list["Application"]] = relationship(back_populates="fptk", cascade="all, delete-orphan")

class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    domicile: Mapped[str | None] = mapped_column(String(255), nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(80), nullable=True)
    university_top10: Mapped[str | None] = mapped_column(String(255), nullable=True)
    university_other: Mapped[str | None] = mapped_column(String(255), nullable=True)
    major: Mapped[str | None] = mapped_column(String(255), nullable=True)
    graduation_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    english_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    university_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gpa_tier: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_tenure: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    total_tenure: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fmcg_experience: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_cv_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    applications: Mapped[list["Application"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")

class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("fptk_id", "candidate_id", name="uq_application"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    fptk_id: Mapped[int] = mapped_column(ForeignKey("fptk.id"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidates.id"), index=True)
    recruiter: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE", index=True)
    current_stage: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    fptk: Mapped[FPTK] = relationship(back_populates="applications")
    candidate: Mapped[Candidate] = relationship(back_populates="applications")
    events: Mapped[list["PipelineEvent"]] = relationship(back_populates="application", cascade="all, delete-orphan")

class PipelineEvent(Base):
    __tablename__ = "pipeline_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    stage: Mapped[str] = mapped_column(String(120), index=True)
    result: Mapped[str | None] = mapped_column(String(80), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    score_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    application: Mapped[Application] = relationship(back_populates="events")

class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    fptk_id: Mapped[int | None] = mapped_column(ForeignKey("fptk.id"), nullable=True, index=True)
    evidence_date: Mapped[date] = mapped_column(Date, index=True)
    evidence_type: Mapped[str] = mapped_column(String(120), default="Sourcing")
    file_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    external_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    total_cv: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class TransferHistory(Base):
    __tablename__ = "transfer_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    transfer_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    fptk_id: Mapped[int] = mapped_column(ForeignKey("fptk.id"), index=True)
    transfer_from: Mapped[str] = mapped_column(String(120))
    transfer_to: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="TRANSFERRED")
    transferred_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transferred_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Blacklist(Base):
    __tablename__ = "blacklist"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_name: Mapped[str] = mapped_column(String(255), index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PositionMaster(Base):
    __tablename__ = "position_master"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    position: Mapped[str] = mapped_column(String(255), index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    business_unit: Mapped[str | None] = mapped_column(String(255), nullable=True)
    division: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manager_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    indirect_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    directorate: Mapped[str | None] = mapped_column(String(255), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)

class MappingUser(Base):
    __tablename__ = "mapping_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    position: Mapped[str] = mapped_column(String(255), index=True)
    manager_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    indirect_user: Mapped[str | None] = mapped_column(String(255), nullable=True)
    directorate: Mapped[str | None] = mapped_column(String(255), nullable=True)

class SchemaConfig(Base):
    __tablename__ = "schema_config"
    id: Mapped[int] = mapped_column(primary_key=True)
    database_name: Mapped[str] = mapped_column(String(80), index=True)
    field_id: Mapped[str] = mapped_column(String(120), index=True)
    header_name: Mapped[str] = mapped_column(String(255))
    position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    data_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    show_in_form: Mapped[bool] = mapped_column(Boolean, default=True)
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    read_only: Mapped[bool] = mapped_column(Boolean, default=False)
    searchable: Mapped[bool] = mapped_column(Boolean, default=False)
    control_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dropdown_values: Mapped[str | None] = mapped_column(Text, nullable=True)
    rule: Mapped[str | None] = mapped_column(Text, nullable=True)
    aliases: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_field: Mapped[bool] = mapped_column(Boolean, default=False)
    custom_field: Mapped[bool] = mapped_column(Boolean, default=False)
    canonical_header: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

class ImportRun(Base):
    __tablename__ = "import_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_file: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(80))
    inserted: Mapped[int] = mapped_column(Integer, default=0)
    updated: Mapped[int] = mapped_column(Integer, default=0)
    skipped: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class UploadBatch(Base):
    """One uploaded workbook and its validation/compile result."""
    __tablename__ = "upload_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    owner_email: Mapped[str] = mapped_column(String(255), index=True)
    owner_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_file: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(50), default="RECRUITER")
    file_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="UPLOADED", index=True)
    fptk_rows: Mapped[int] = mapped_column(Integer, default=0)
    sourcing_rows: Mapped[int] = mapped_column(Integer, default=0)
    blacklist_rows: Mapped[int] = mapped_column(Integer, default=0)
    validation_issue_count: Mapped[int] = mapped_column(Integer, default=0)
    validation_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    compile_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    compiled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SourceOwnership(Base):
    """Ownership is based on the uploader/source file, not PIC Recruiter."""
    __tablename__ = "source_ownership"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", name="uq_source_ownership_entity"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(80), index=True)
    entity_id: Mapped[int] = mapped_column(Integer, index=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    owner_email: Mapped[str] = mapped_column(String(255), index=True)
    owner_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_sheet: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_batch_id: Mapped[int | None] = mapped_column(ForeignKey("upload_batches.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SourcingSourceMeta(Base):
    """Source metadata for DB Sourcing records, including mandatory Sourcing Date."""
    __tablename__ = "sourcing_source_meta"
    __table_args__ = (UniqueConstraint("application_id", name="uq_sourcing_meta_application"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), index=True)
    sourcing_date: Mapped[date] = mapped_column(Date, index=True)
    source_identity_key: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    owner_email: Mapped[str] = mapped_column(String(255), index=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CompiledBlacklist(Base):
    """Blacklist from recruiter files. Key is Owner + source No, not No globally."""
    __tablename__ = "compiled_blacklist"
    __table_args__ = (UniqueConstraint("owner_user_id", "source_no", name="uq_blacklist_owner_no"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    owner_email: Mapped[str] = mapped_column(String(255), index=True)
    source_no: Mapped[str] = mapped_column(String(80), index=True)
    last_update: Mapped[date | None] = mapped_column(Date, nullable=True)
    business_unit: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    candidate_name: Mapped[str] = mapped_column(String(255), index=True)
    category: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    pic_recruiter: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UnlinkedSourcing(Base):
    """DB Sourcing row whose Kode Unik has no matching FPTK yet.

    The row is intentionally kept outside Application/Pipeline until a valid parent
    FPTK exists. Therefore it does not contribute to Funneling/Progress.
    """
    __tablename__ = "unlinked_sourcing"
    __table_args__ = (UniqueConstraint("owner_user_id", "source_identity_key", name="uq_unlinked_sourcing_owner_identity"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    kode_unik: Mapped[str] = mapped_column(String(120), index=True)
    candidate_name: Mapped[str] = mapped_column(String(255), index=True)
    sourcing_date: Mapped[date] = mapped_column(Date, index=True)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    recruiter: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    source_identity_key: Mapped[str] = mapped_column(String(500), index=True)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    owner_email: Mapped[str] = mapped_column(String(255), index=True)
    owner_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_row: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_batch_id: Mapped[int | None] = mapped_column(ForeignKey("upload_batches.id"), nullable=True, index=True)
    reason: Mapped[str] = mapped_column(String(120), default="FPTK_NOT_FOUND", index=True)
    status: Mapped[str] = mapped_column(String(30), default="UNLINKED", index=True)
    raw_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_fptk_id: Mapped[int | None] = mapped_column(ForeignKey("fptk.id"), nullable=True, index=True)
    resolved_application_id: Mapped[int | None] = mapped_column(ForeignKey("applications.id"), nullable=True, index=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UploadCycle(Base):
    """Admin-controlled upload period. Exactly one cycle should be active."""
    __tablename__ = "upload_cycles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UploadCycleMember(Base):
    """Per-user completion state inside an upload cycle."""
    __tablename__ = "upload_cycle_members"
    __table_args__ = (UniqueConstraint("cycle_id", "user_id", name="uq_upload_cycle_member"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("upload_cycles.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    username: Mapped[str] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(30), default="NOT_STARTED", index=True)
    successful_file_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_file_count: Mapped[int] = mapped_column(Integer, default=0)
    last_upload_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UploadBatchCycle(Base):
    """Links upload history to the active cycle without altering legacy UploadBatch schema."""
    __tablename__ = "upload_batch_cycles"
    __table_args__ = (UniqueConstraint("upload_batch_id", name="uq_upload_batch_cycle_batch"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    upload_batch_id: Mapped[int] = mapped_column(ForeignKey("upload_batches.id"), index=True)
    cycle_id: Mapped[int] = mapped_column(ForeignKey("upload_cycles.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
