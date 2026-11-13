"""
Setup database: engine, session, dan Base.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import DATABASE_URL

# check_same_thread=False dibutuhkan khusus untuk SQLite agar bisa dipakai
# dari thread uvicorn yang berbeda. Aman karena SQLite satu file lokal.
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Kelas dasar semua model ORM."""


def get_db():
    """Dependency FastAPI: buka sesi DB per request, tutup di akhir."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
