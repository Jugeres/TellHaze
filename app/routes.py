"""
Endpoint REST API.
"""

import csv
import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app import config
from app.data_source import fetch_multi
from app.db import get_db
from app.ispu import (
    PARAMETER_DIHITUNG,
    hitung_ispu_parameter,
    rata_rata_bergerak,
)
from app.models import Location, Measurement
from app.service import _proses_record_lokasi, refresh_semua_lokasi

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


@router.get("/api/export/csv")
def ekspor_csv(db: Session = Depends(get_db)):
    """
    Unduh status terbaru seluruh kota sebagai CSV (bisa dibuka di Excel).
    Kolom konsentrasi diambil dari baris jam terakhir tiap lokasi.
    """
    # BOM UTF-8 agar karakter µ dan kategori terbaca benar oleh Excel.
    BOM = "\ufeff"
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "peringkat", "kota", "provinsi", "lat", "lon",
        "ispu", "kategori", "parameter_kritis", "waktu_data",
        "pm25_ugm3", "pm10_ugm3", "co_ugm3", "no2_ugm3", "so2_ugm3", "o3_ugm3",
    ])

    lokasi_list = db.query(Location).all()
    baris_data = []
    for loc in lokasi_list:
        terakhir = (
            db.query(Measurement)
            .filter(Measurement.location_id == loc.id)
            .order_by(Measurement.timestamp.desc())
            .first()
        )
        baris_data.append((loc, terakhir))

    # Urutkan dari ISPU tertinggi; lokasi tanpa data taruh paling bawah.
    baris_data.sort(
        key=lambda x: x[1].ispu_value if x[1] is not None and x[1].ispu_value is not None else -1,
        reverse=True,
    )

    for peringkat, (loc, m) in enumerate(baris_data, start=1):
        if m is None:
            writer.writerow([peringkat, loc.name, loc.province, loc.lat, loc.lon,
                             "", "Tidak ada data", "", "", "", "", "", "", "", ""])
            continue
        writer.writerow([
            peringkat, loc.name, loc.province, loc.lat, loc.lon,
            None if m.ispu_value is None else round(m.ispu_value),
            m.category, m.critical_parameter or "", m.timestamp.isoformat(),
            _fmt(m.pm25), _fmt(m.pm10), _fmt(m.co), _fmt(m.no2), _fmt(m.so2), _fmt(m.o3),
        ])

    return Response(
        content=(BOM + buffer.getvalue()).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="tellhaze_ispu.csv"'},
    )


def _fmt(nilai: float | None) -> str:
    """Format angka konsentrasi untuk CSV: None jadi string kosong."""
    return "" if nilai is None else f"{nilai:g}"


@router.post("/api/locations/import")
async def impor_lokasi_csv(request: Request, db: Session = Depends(get_db)):
    """
    Impor daftar lokasi dari teks CSV (body request, bukan multipart).

    Format minimal tiap baris: name,province,lat,lon
    Lokasi baru langsung di-fetch datanya dari Open-Meteo.
    """
    teks = (await request.body()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(teks))

    ditambah: list[Location] = []
    dilewati: list[str] = []
    tidak_valid: list[str] = []

    for i, row in enumerate(reader, start=2):  # baris 1 adalah header
        # Toleran terhadap spasi/beda kapital di nama kolom.
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        nama = row.get("name", "")
        provinsi = row.get("province") or "Lainnya"
        try:
            lat, lon = float(row.get("lat", "")), float(row.get("lon", ""))
        except ValueError:
            tidak_valid.append(f"baris {i}: lat/lon bukan angka")
            continue
        if not nama:
            tidak_valid.append(f"baris {i}: kolom name kosong")
            continue
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            tidak_valid.append(f"baris {i}: koordinat di luar rentang")
            continue
        if db.query(Location).filter(Location.name == nama).first() is not None:
            dilewati.append(f"{nama} (sudah ada)")
            continue
        ditambah.append(Location(name=nama, province=provinsi, lat=lat, lon=lon))

    for loc in ditambah:
        db.add(loc)
    db.commit()

    # Fetch data untuk lokasi yang baru saja ditambahkan.
    log_fetch: list[str] = []
    if ditambah:
        try:
            data = fetch_multi([(l.lat, l.lon) for l in ditambah])
            for loc in ditambah:
                records = data.get((loc.lat, loc.lon))
                if records:
                    log_fetch.append(_proses_record_lokasi(db, loc, records))
                else:
                    log_fetch.append(f"{loc.name}: GAGAL - tidak ada data Open-Meteo")
        except Exception as e:  # noqa: BLE001
            log_fetch.append(f"FETCH GAGAL - {type(e).__name__}: {e}")

    return {
        "added": len(ditambah),
        "skipped": dilewati,
        "invalid": tidak_valid,
        "fetch_log": log_fetch,
    }
