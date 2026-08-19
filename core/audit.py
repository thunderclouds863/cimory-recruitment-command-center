from .db import session_scope
from .models import AuditLog

def write_audit(user_email, action, entity_type=None, entity_id=None, detail=None):
    with session_scope() as s:
        s.add(AuditLog(user_email=user_email, action=action, entity_type=entity_type, entity_id=str(entity_id) if entity_id is not None else None, detail=detail))
