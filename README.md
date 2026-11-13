# ISPU Pilot — Dashboard Kualitas Udara Berbasis Peta

Pilot project Kerja Praktik: mengambil konsentrasi polutan per jam dari
**Open-Meteo Air Quality API**, menghitung **ISPU** (Permen LHK No.
P.14/MENLHK/SETJEN/KUM.1/7/2020), menyimpannya ke database, menyediakan REST
API, dan menampilkan hasilnya di peta Leaflet dengan marker berwarna sesuai
kategori ISPU.

> **Catatan sumber data:** data dari Open-Meteo adalah **hasil model (CAMS),
> bukan pengukuran sensor stasiun**. Parameter **HC tidak tersedia** di
> Open-Meteo sehingga tidak dihitung pada pilot ini.

## Cara Install

```bash
# 1. Buat virtual environment
python -m venv .venv

# 2. Aktifkan (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# 3. Pasang dependensi
pip install -r requirements.txt
```

## Cara Jalankan

```bash
uvicorn app.main:app --reload
```

Buka `http://127.0.0.1:8000/` di browser untuk melihat peta.
Lokasi seed otomatis diisi saat aplikasi pertama kali dijalankan.

Untuk mengisi data pertama kali, klik tombol **"Refresh data"** di peta,
atau panggil endpoint `POST /api/refresh`.

## Daftar Endpoint

| Method | Path | Fungsi |
| --- | --- | --- |
| GET | `/api/locations` | Daftar lokasi (nama, provinsi, koordinat) |
| GET | `/api/ispu/latest` | GeoJSON FeatureCollection: ISPU terbaru tiap lokasi |
| GET | `/api/ispu/{location_id}/history?hours=48` | Riwayat ISPU per jam + `now` (waktu WIB saat ini) |
| GET | `/api/summary` | 5 kota terburuk, sebaran kategori, rata-rata PM2.5 |
| POST | `/api/refresh` | Fetch Open-Meteo untuk semua lokasi (batch), hitung, simpan |
| GET | `/api/health` | Cek status aplikasi |

## Cakupan Lokasi

55 titik: **Sumatera Selatan** (asal proyek), **DKI Jakarta** (pembanding),
**Jawa Barat** (22 kota/kabupaten), dan **Jawa Timur** (28 kota/kabupaten).
Setiap lokasi punya kolom `province` sehingga dashboard bisa difilter per provinsi.

## Dashboard (TellHaze)

Halaman utama (`/`) menampilkan:

- **Kota terburuk hari ini** — 5 peringkat ISPU tertinggi, klik untuk detail.
- **Sebaran kategori** — satu bar proporsi + jumlah per kategori ISPU.
- **Peta Leaflet** — marker angka ISPU berwarna sesuai kategori, filter provinsi, legenda.
- **Panel detail kota** — angka ISPU besar, saran kesehatan, grafik 24 jam riwayat
  (garis penuh) + 24 jam perkiraan model (garis putus-putus), dan ISPU per polutan.
- **Tabel peringkat seluruh kota** — klik baris untuk membuka detail di peta.

## Struktur Proyek

```
ispu-pilot/
├── app/
│   ├── main.py            # FastAPI app, mount static, daftar router
│   ├── config.py          # DATABASE_URL, daftar lokasi, konstanta
│   ├── db.py              # engine, session, Base
│   ├── models.py          # tabel Location, Measurement
│   ├── data_source.py     # fetch dan parse Open-Meteo
│   ├── ispu.py            # breakpoint + fungsi hitung ISPU (inti proyek)
│   ├── service.py         # alur: fetch -> rata-rata -> ISPU -> simpan
│   └── routes.py          # endpoint API
├── static/
│   └── index.html         # peta Leaflet
├── tests/
│   └── test_ispu.py
├── requirements.txt
└── README.md
```

## Pengujian

```bash
pytest -v
```

## ⚠️ Daftar yang BELUM Diverifikasi

Bagian-bagian berikut masih perlu dicek ke teks **Permen LHK
P.14/MENLHK/SETJEN/KUM.1/7/2020** sebelum dipakai serius:

1. **Baris ISPU 500 pada tabel breakpoint** — baris ISPU 0 sampai 300 sudah
   diverifikasi pemilik proyek dari laporan pembelajarannya, tetapi baris 500
   belum. Di kode ditandai dengan komentar `# TODO VERIFIKASI` di `app/ispu.py`
   (konstanta `ROW_500`).
2. **Periode rata-rata bergerak per parameter** — nilai di `AVERAGING_HOURS`
   (`app/config.py`: PM10/PM2.5/SO2/NO2 = 24 jam, CO/O3 = 8 jam) adalah
   **default sementara**, belum dicek ke Permen.
