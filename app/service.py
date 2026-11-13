"""
Alur utama: fetch Open-Meteo -> rata-rata bergerak -> ISPU -> simpan ke DB.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app import config
from app.data_source import fetch_multi
from app.ispu import PARAMETER_DIHITUNG, hitung_ispu_lokasi, rata_rata_bergerak
from app.models import Location, Measurement


def seed_lokasi(db: Session) -> None:
    """Isi tabel Location dari LOCATIONS_SEED jika tabel masih kosong."""
    if db.query(Location).count() > 0:
        return
    for nama, provinsi, lat, lon in config.LOCATIONS_SEED:
        db.add(Location(name=nama, province=provinsi, lat=lat, lon=lon))
    db.commit()


def _proses_record_lokasi(db: Session, location: Location, records: list[dict]) -> str:
    """
    Simpan/update satu lokasi dari data record hasil fetch:
    konsentrasi mentah per jam -> rata-rata bergerak -> ISPU -> simpan.

    Mengembalikan ringkasan singkat untuk log.
    """
    # Ambil semua baris lama lokasi ini sebagai dict timestamp -> baris,
    # supaya fetch ulang UPDATE baris lama, bukan menggandakan.
    existing = {
        m.timestamp: m
        for m in db.query(Measurement).filter(Measurement.location_id == location.id).all()
    }

    jumlah_baru = 0
    jumlah_update = 0

    for i, record in enumerate(records):
        timestamp: datetime = record["timestamp"]

        # Simpan/update konsentrasi mentah (konsentrasi di jam itu sendiri).
        baris = existing.get(timestamp)
        if baris is None:
            baris = Measurement(location_id=location.id, timestamp=timestamp)
            db.add(baris)
            jumlah_baru += 1
        else:
            jumlah_update += 1
        for param in PARAMETER_DIHITUNG:
            setattr(baris, param, record.get(param))

        # Rata-rata bergerak per parameter: N jam terakhir TERMASUK jam ini.
        rata_rata: dict[str, float | None] = {}
        for param in PARAMETER_DIHITUNG:
            n = config.AVERAGING_HOURS[param]
            jendela = records[i - n + 1 : i + 1]  # jam target + N-1 jam sebelumnya
            if len(jendela) < n:
                # Jendela belum penuh (awal deret data) -> tidak valid.
                rata_rata[param] = None
                continue
            nilai = [j.get(param) for j in jendela]
            rata_rata[param] = rata_rata_bergerak(nilai)

        # ISPU lokasi = maksimum antar parameter yang valid.
        hasil = hitung_ispu_lokasi(rata_rata)
        baris.ispu_value = hasil["ispu"]
        baris.critical_parameter = hasil["critical_parameter"]
        baris.category = hasil["category"]

    db.commit()
    return f"{location.name}: {jumlah_baru} baris baru, {jumlah_update} di-update"


def refresh_semua_lokasi(db: Session) -> list[str]:
    """
    Fetch SEMUA lokasi sekaligus (batch, beberapa panggilan HTTP saja),
    lalu hitung dan simpan per lokasi. Jika satu lokasi gagal dihitung
    atau fetch gagal, catat log dan lanjutkan ke bagian lain.
    """
    lokasi_list = db.query(Location).all()

    log: list[str] = []
    try:
        # Satu fetch batch untuk semua lokasi (chunk otomatis di data_source).
        data = fetch_multi([(loc.lat, loc.lon) for loc in lokasi_list])
    except Exception as e:  # noqa: BLE001 - fetch gagal total, laporkan saja
        return [f"FETCH GAGAL TOTAL - {type(e).__name__}: {e}"]

    for loc in lokasi_list:
        records = data.get((loc.lat, loc.lon))
        if not records:
            log.append(f"{loc.name}: GAGAL - tidak ada data untuk koordinat ini")
            continue
        try:
            log.append(_proses_record_lokasi(db, loc, records))
        except Exception as e:  # noqa: BLE001 - satu lokasi gagal tidak boleh menghentikan lainnya
            log.append(f"{loc.name}: GAGAL - {type(e).__name__}: {e}")
    return log


if __name__ == "__main__":
    # Uji manual: seed lokasi + proses Palembang saja.
    from app.data_source import fetch_multi
    from app.db import SessionLocal

    db = SessionLocal()
    seed_lokasi(db)
    palembang = db.query(Location).filter(Location.name == "Palembang").first()
    records = fetch_multi([(palembang.lat, palembang.lon)])[(palembang.lat, palembang.lon)]
    print(_proses_record_lokasi(db, palembang, records))

    # Tampilkan 5 baris terakhir hasil perhitungan.
    contoh = (
        db.query(Measurement)
        .filter(Measurement.location_id == palembang.id)
        .order_by(Measurement.timestamp.desc())
        .limit(5)
        .all()
    )
    for m in contoh:
        print(
            m.timestamp,
            f"ISPU={None if m.ispu_value is None else round(m.ispu_value, 1)}",
            m.category,
            f"kritis={m.critical_parameter}",
        )
    db.close()
