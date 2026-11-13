"""
Entrypoint aplikasi FastAPI.

Jalankan dengan:
    uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import Base, SessionLocal, engine
from app.models import Location, Measurement  # noqa: F401 - pastikan model terdaftar
from app.routes import router
from app.service import seed_lokasi


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Saat startup: buat tabel bila belum ada, lalu seed lokasi jika kosong.
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed_lokasi(db)
    finally:
        db.close()
    yield


app = FastAPI(title="ISPU Pilot", version="0.1.0", lifespan=lifespan)

# Daftarkan semua endpoint API.
app.include_router(router)

# Sajikan frontend statis (peta Leaflet) di "/".
app.mount("/", StaticFiles(directory="static", html=True), name="static")
