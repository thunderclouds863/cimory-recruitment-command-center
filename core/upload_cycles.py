from __future__ import annotations
from datetime import datetime
from sqlalchemy import select

from .db import session_scope
from .models import User, UploadCycle, UploadCycleMember, UploadBatchCycle

STATUS_LABELS = {
    "NOT_STARTED": "Belum Mulai",
    "UPLOADING": "Sedang Upload",
    "DONE": "Done",
}


def _non_admin_users(s):
    return s.scalars(
        select(User).where(User.active == True, User.role != "admin").order_by(User.id)
    ).all()


def _ensure_members_in_session(s, cycle: UploadCycle):
    existing = {
        row.user_id
        for row in s.scalars(select(UploadCycleMember).where(UploadCycleMember.cycle_id == cycle.id)).all()
    }
    for u in _non_admin_users(s):
        if u.id not in existing:
            s.add(
                UploadCycleMember(
                    cycle_id=cycle.id,
                    user_id=u.id,
                    username=u.display_name,
                    status="NOT_STARTED",
                )
            )


def ensure_active_cycle(created_by: str = "system") -> int:
    with session_scope() as s:
        cycle = s.scalar(select(UploadCycle).where(UploadCycle.active == True).order_by(UploadCycle.id.desc()))
        if cycle is None:
            cycle = UploadCycle(
                name="Current Upload Cycle",
                active=True,
                created_by=created_by,
                opened_at=datetime.utcnow(),
            )
            s.add(cycle)
            s.flush()
        _ensure_members_in_session(s, cycle)
        return cycle.id


def get_active_cycle():
    ensure_active_cycle()
    with session_scope() as s:
        c = s.scalar(select(UploadCycle).where(UploadCycle.active == True).order_by(UploadCycle.id.desc()))
        if not c:
            return None
        return {
            "id": c.id,
            "name": c.name,
            "opened_at": c.opened_at,
            "created_by": c.created_by,
        }


def create_cycle(name: str, created_by: str) -> int:
    name = (name or "").strip() or "New Upload Cycle"
    with session_scope() as s:
        now = datetime.utcnow()
        for old in s.scalars(select(UploadCycle).where(UploadCycle.active == True)).all():
            old.active = False
            old.closed_at = now
        cycle = UploadCycle(name=name, active=True, created_by=created_by, opened_at=now)
        s.add(cycle)
        s.flush()
        _ensure_members_in_session(s, cycle)
        return cycle.id


def get_member_state(user_id: int):
    cycle_id = ensure_active_cycle()
    with session_scope() as s:
        row = s.scalar(
            select(UploadCycleMember).where(
                UploadCycleMember.cycle_id == cycle_id,
                UploadCycleMember.user_id == user_id,
            )
        )
        if row is None:
            cycle = s.get(UploadCycle, cycle_id)
            _ensure_members_in_session(s, cycle)
            s.flush()
            row = s.scalar(
                select(UploadCycleMember).where(
                    UploadCycleMember.cycle_id == cycle_id,
                    UploadCycleMember.user_id == user_id,
                )
            )
        return {
            "cycle_id": cycle_id,
            "status": row.status,
            "status_label": STATUS_LABELS.get(row.status, row.status),
            "successful_file_count": row.successful_file_count,
            "failed_file_count": row.failed_file_count,
            "last_upload_at": row.last_upload_at,
            "done_at": row.done_at,
        }


def register_upload_result(user_id: int, batch_id: int, success: bool):
    cycle_id = ensure_active_cycle()
    with session_scope() as s:
        row = s.scalar(
            select(UploadCycleMember).where(
                UploadCycleMember.cycle_id == cycle_id,
                UploadCycleMember.user_id == user_id,
            )
        )
        if row is None:
            cycle = s.get(UploadCycle, cycle_id)
            _ensure_members_in_session(s, cycle)
            s.flush()
            row = s.scalar(
                select(UploadCycleMember).where(
                    UploadCycleMember.cycle_id == cycle_id,
                    UploadCycleMember.user_id == user_id,
                )
            )
        now = datetime.utcnow()
        row.last_upload_at = now
        if success:
            row.successful_file_count += 1
            row.status = "UPLOADING"
            row.done_at = None
        else:
            row.failed_file_count += 1
        existing = s.scalar(select(UploadBatchCycle).where(UploadBatchCycle.upload_batch_id == batch_id))
        if existing is None:
            s.add(UploadBatchCycle(upload_batch_id=batch_id, cycle_id=cycle_id, user_id=user_id))


def mark_done(user_id: int):
    cycle_id = ensure_active_cycle()
    with session_scope() as s:
        row = s.scalar(
            select(UploadCycleMember).where(
                UploadCycleMember.cycle_id == cycle_id,
                UploadCycleMember.user_id == user_id,
            )
        )
        if row is None or row.successful_file_count <= 0:
            raise ValueError("Minimal satu file harus berhasil di-compile sebelum klik Done Uploading.")
        row.status = "DONE"
        row.done_at = datetime.utcnow()
        return row.successful_file_count


def reopen_member(member_id: int):
    with session_scope() as s:
        row = s.get(UploadCycleMember, member_id)
        if not row:
            return False
        row.status = "UPLOADING" if row.successful_file_count > 0 else "NOT_STARTED"
        row.done_at = None
        return True


def cycle_monitor_rows(cycle_id: int | None = None):
    if cycle_id is None:
        cycle_id = ensure_active_cycle()
    with session_scope() as s:
        members = s.scalars(
            select(UploadCycleMember).where(UploadCycleMember.cycle_id == cycle_id).order_by(UploadCycleMember.id)
        ).all()
        return [
            {
                "member_id": m.id,
                "Username": m.username,
                "Status": STATUS_LABELS.get(m.status, m.status),
                "Successful Files": m.successful_file_count,
                "Failed Attempts": m.failed_file_count,
                "Last Upload": m.last_upload_at,
                "Done At": m.done_at,
            }
            for m in members
        ]


def cycle_summary(cycle_id: int | None = None):
    rows = cycle_monitor_rows(cycle_id)
    return {
        "total": len(rows),
        "not_started": sum(1 for r in rows if r["Status"] == "Belum Mulai"),
        "uploading": sum(1 for r in rows if r["Status"] == "Sedang Upload"),
        "done": sum(1 for r in rows if r["Status"] == "Done"),
    }


def list_cycles():
    with session_scope() as s:
        rows = s.scalars(select(UploadCycle).order_by(UploadCycle.id.desc())).all()
        return [
            {
                "id": x.id,
                "name": x.name,
                "active": x.active,
                "opened_at": x.opened_at,
                "closed_at": x.closed_at,
                "created_by": x.created_by,
            }
            for x in rows
        ]
