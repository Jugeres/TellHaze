"""
Mengambil dan mem-parsing data dari Open-Meteo Air Quality API.

Data yang diberikan adalah hasil model (CAMS), bukan pengukuran sensor stasiun.
Open-Meteo mendukung banyak lokasi dalam SATU panggilan lewat daftar
latitude/longitude yang dipisah koma — dipakai agar refresh banyak kota tetap cepat.
"""

from datetime import datetime

import httpx

from app import config


def _parse_respon(data: dict) -> list[dict]:
    """Ubah satu objek respons Open-Meteo menjadi daftar record per jam."""
    hourly = data.get("hourly", {})
    waktu = hourly.get("time", [])

    records = []
    for i, waktu_str in enumerate(waktu):
        record: dict = {"timestamp": datetime.fromisoformat(waktu_str)}
        for nama_api, nama_internal in config.OPEN_METEO_MAPPING.items():
            nilai = hourly.get(nama_api, [None] * len(waktu))[i]
            record[nama_internal] = nilai
        records.append(record)
    return records


def fetch_multi(daftar_koordinat: list[tuple[float, float]]) -> dict[tuple[float, float], list[dict]]:
    """
    Fetch data kualitas udara per jam untuk BANYAK titik koordinat.
    Koordinat dikirim dalam chunk kecil; setiap chunk = satu panggilan HTTP.

    Mengembalikan dict: (lat, lon) -> daftar record
        {"timestamp": datetime, "pm10": float|None, "pm25": ..., dst}
    """
    hasil: dict[tuple[float, float], list[dict]] = {}
    chunk_size = config.CHUNK_LOKASI

    for mulai in range(0, len(daftar_koordinat), chunk_size):
        chunk = daftar_koordinat[mulai : mulai + chunk_size]
        params = {
            "latitude": ",".join(f"{lat}" for lat, _lon in chunk),
            "longitude": ",".join(f"{lon}" for _lat, lon in chunk),
            "hourly": config.OPEN_METEO_HOURLY,
            "past_days": config.PAST_DAYS,
            "forecast_days": config.FORECAST_DAYS,
            "timezone": config.TIMEZONE,
        }

        # Error jaringan/timeout dibiarkan naik ke pemanggil supaya
        # service bisa mencatat log dan lanjut ke chunk berikutnya.
        response = httpx.get(config.OPEN_METEO_URL, params=params, timeout=config.TIMEOUT_DETIK)
        response.raise_for_status()
        body = response.json()

        # Respons satu lokasi berbentuk dict; banyak lokasi berbentuk list.
        respon_chunk = body if isinstance(body, list) else [body]

        # Urutan respons mengikuti urutan koordinat yang dikirim.
        for (lat, lon), data in zip(chunk, respon_chunk):
            hasil[(lat, lon)] = _parse_respon(data)

    return hasil


if __name__ == "__main__":
    # Uji manual: dua lokasi (Palembang & Surabaya), cetak 5 baris pertama
    # hasil parse untuk masing-masing.
    data = fetch_multi([(-2.9761, 104.7754), (-7.2575, 112.7521)])
    for koordinat, records in data.items():
        print(f"\nLokasi {koordinat} — total baris: {len(records)}")
        for baris in records[:5]:
            print(baris)
