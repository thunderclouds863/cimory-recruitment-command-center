from __future__ import annotations
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL
from .models import Base

url = DATABASE_URL
# Most hosted PostgreSQL providers give postgresql://... URLs. Force psycopg v3,
# which is included in requirements.txt.
if url.startswith("postgresql://"):
    url = "postgresql+psycopg://" + url[len("postgresql://"):]
elif url.startswith("postgres://"):
    url = "postgresql+psycopg://" + url[len("postgres://"):]

_connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
engine = create_engine(url, future=True, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
