"""
Endpoint REST API.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import config
from app.db import get_db
from app.ispu import (
    PARAMETER_DIHITUNG,
    hitung_ispu_parameter,
    rata_rata_bergerak,
)
from app.models import Location, Measurement
from app.service import refresh_semua_lokasi

router = APIRouter()


@router.get("/api/health")
def health():
    """Cek cepat bahwa aplikasi hidup."""
    return {"status": "ok"}


@router.get("/api/locations")
def daftar_lokasi(db: Session = Depends(get_db)):
    """Daftar semua lokasi pemantauan."""
    lokasi = db.query(Location).order_by(Location.id).all()
    return [
        {"id": loc.id, "name": loc.name, "province": loc.province, "lat": loc.lat, "lon": loc.lon}
        for loc in lokasi
    ]


def _ispu_per_parameter_dari_db(db: Session, location_id: int, terakhir: Measurement) -> dict:
    """
    Hitung ISPU per parameter untuk jam terbaru, memakai jendela rata-rata
    bergerak yang direkonstruksi dari baris mentah yang tersimpan di DB.
    """
    hasil: dict[str, float | None] = {}
    for param in PARAMETER_DIHITUNG:
        n = config.AVERAGING_HOURS[param]
        mulai = terakhir.timestamp - timedelta(hours=n - 1)
        rows = (
            db.query(Measurement)
            .filter(
                Measurement.location_id == location_id,
                Measurement.timestamp >= mulai,
                Measurement.timestamp <= terakhir.timestamp,
            )
            .order_by(Measurement.timestamp)
            .all()
        )
        if len(rows) < n:
            hasil[param] = None
            continue
        rata = rata_rata_bergerak([getattr(r, param) for r in rows])
        hasil[param] = hitung_ispu_parameter(param, rata)
    return hasil


@router.get("/api/ispu/latest")
def ispu_terbaru(db: Session = Depends(get_db)):
    """
    GeoJSON FeatureCollection: satu Feature (Point) per lokasi.
    Catatan GeoJSON: urutan koordinat adalah [lon, lat].
    """
    features = []
    for loc in db.query(Location).order_by(Location.id).all():
        terakhir = (
            db.query(Measurement)
            .filter(Measurement.location_id == loc.id)
            .order_by(Measurement.timestamp.desc())
            .first()
        )
        if terakhir is None:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [loc.lon, loc.lat]},
                    "properties": {
                        "id": loc.id,
                        "name": loc.name,
                        "province": loc.province,
                        "ispu": None,
                        "category": "Tidak ada data",
                        "critical_parameter": None,
                        "timestamp": None,
                        "per_parameter": {},
                    },
                }
            )
            continue

        per_parameter = _ispu_per_parameter_dari_db(db, loc.id, terakhir)
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [loc.lon, loc.lat]},
                "properties": {
                    "id": loc.id,
                    "name": loc.name,
                    "province": loc.province,
                    "ispu": None if terakhir.ispu_value is None else round(terakhir.ispu_value),
                    "category": terakhir.category,
                    "critical_parameter": terakhir.critical_parameter,
                    "timestamp": terakhir.timestamp.isoformat(),
                    "per_parameter": {
                        p: (None if v is None else round(v))
                        for p, v in per_parameter.items()
                    },
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}


@router.get("/api/summary")
def ringkasan(db: Session = Depends(get_db)):
    """
    Ringkasan dashboard: 5 kota terburuk, sebaran kategori,
    jumlah kota tidak sehat ke atas, dan rata-rata PM2.5 terakhir.
    """
    lokasi_list = db.query(Location).all()

    terakhir_per_lokasi: dict[int, Measurement] = {}
    for loc in lokasi_list:
        m = (
            db.query(Measurement)
            .filter(Measurement.location_id == loc.id)
            .order_by(Measurement.timestamp.desc())
            .first()
        )
        if m is not None:
            terakhir_per_lokasi[loc.id] = m

    jumlah_per_kategori: dict[str, int] = {
        "Baik": 0, "Sedang": 0, "Tidak Sehat": 0,
        "Sangat Tidak Sehat": 0, "Berbahaya": 0, "Tidak ada data": 0,
    }
    for m in terakhir_per_lokasi.values():
        if m.category in jumlah_per_kategori:
            jumlah_per_kategori[m.category] += 1

    terburuk = sorted(
        terakhir_per_lokasi.items(),
        key=lambda item: item[1].ispu_value if item[1].ispu_value is not None else -1,
        reverse=True,
    )[:5]
    daftar_terburuk = []
    for loc_id, m in terburuk:
        loc = next(l for l in lokasi_list if l.id == loc_id)
        daftar_terburuk.append({
            "id": loc.id,
            "name": loc.name,
            "province": loc.province,
            "ispu": None if m.ispu_value is None else round(m.ispu_value),
            "category": m.category,
            "critical_parameter": m.critical_parameter,
        })

    # Rata-rata PM2.5 terakhir antar lokasi yang punya data.
    pm25_values = [m.pm25 for m in terakhir_per_lokasi.values() if m.pm25 is not None]
    rata_pm25 = round(sum(pm25_values) / len(pm25_values), 1) if pm25_values else None

    return {
        "total_lokasi": len(lokasi_list),
        "lokasi_berdata": len(terakhir_per_lokasi),
        "jumlah_per_kategori": jumlah_per_kategori,
        "tidak_sehat_ke_atas": sum(
            jumlah_per_kategori[k] for k in ("Tidak Sehat", "Sangat Tidak Sehat", "Berbahaya")
        ),
        "rata_pm25_terakhir": rata_pm25,
        "terburuk": daftar_terburuk,
    }


@router.get("/api/ispu/{location_id}/history")
def riwayat_ispu(
    location_id: int,
    hours: int = Query(default=48, ge=1, le=240),
    db: Session = Depends(get_db),
):
    """Riwayat ISPU per jam untuk satu lokasi (default 48 jam terakhir)."""
    lokasi = db.query(Location).filter(Location.id == location_id).first()
    if lokasi is None:
        raise HTTPException(status_code=404, detail="Lokasi tidak ditemukan")

    rows = (
        db.query(Measurement)
        .filter(Measurement.location_id == location_id)
        .order_by(Measurement.timestamp.desc())
        .limit(hours)
        .all()
    )
    rows.reverse()  # urut waktu naik supaya gampang digambar grafik

    # "now" = jam sekarang menurut zona Asia/Jakarta, tanpa info tz
    # (konsisten dengan timestamp yang disimpan). Frontend memakainya
    # untuk memisahkan data lampiran (garis penuh) dan prediksi (garis putus).
    sekarang = datetime.now(ZoneInfo("Asia/Jakarta")).replace(tzinfo=None).isoformat()

    return {
        "location_id": location_id,
        "name": lokasi.name,
        "now": sekarang,
        "data": [
            {
                "timestamp": m.timestamp.isoformat(),
                "ispu": None if m.ispu_value is None else round(m.ispu_value),
                "category": m.category,
            }
            for m in rows
        ],
    }


@router.post("/api/refresh")
def refresh(db: Session = Depends(get_db)):
    """Memicu fetch Open-Meteo untuk semua lokasi, hitung, simpan."""
    log = refresh_semua_lokasi(db)
    return {"status": "selesai", "log": log}
