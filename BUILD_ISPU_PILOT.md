# BUILD INSTRUCTIONS: ISPU Pilot (Dashboard Kualitas Udara Berbasis Peta)

Dokumen ini adalah instruksi lengkap untuk agent. Baca seluruhnya sebelum menulis kode. Kerjakan sesuai urutan di bagian "Urutan Pengerjaan" dan berhenti untuk konfirmasi di titik yang ditandai **[STOP]**.

## 1. Tujuan

Bangun web mini (pilot project) yang:

1. Mengambil konsentrasi polutan per jam dari Open-Meteo Air Quality API untuk beberapa titik koordinat.
2. Menghitung nilai ISPU (Indeks Standar Pencemar Udara, Permen LHK No. P.14/MENLHK/SETJEN/KUM.1/7/2020) dari konsentrasi tersebut.
3. Menyimpan hasilnya ke database.
4. Menyediakan REST API.
5. Menampilkan hasilnya pada peta dengan marker berwarna sesuai kategori ISPU.

Ini proyek belajar untuk mahasiswa yang sedang kerja praktik. **Kode harus mudah dibaca dan diberi komentar singkat berbahasa Indonesia pada logika inti**, bukan kode yang sok canggih.

## 2. Stack (jangan diganti tanpa konfirmasi)

- Python 3.11+
- FastAPI + Uvicorn
- SQLAlchemy 2.x, database default **SQLite** (file `ispu.db`), dibuat agar mudah pindah ke PostgreSQL lewat satu variabel `DATABASE_URL`
- `httpx` untuk memanggil Open-Meteo
- `pytest` untuk pengujian
- Frontend: satu file `static/index.html`, JavaScript biasa, **Leaflet** (via CDN). Tanpa React, tanpa build step.

Jangan menambah library di luar daftar ini kecuali benar-benar perlu, dan sebutkan alasannya.

## 3. Struktur Folder

```
ispu-pilot/
├── app/
│   ├── __init__.py
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
├── README.md
└── .gitignore
```

## 4. Spesifikasi `app/ispu.py` (bagian paling penting)

### 4.1 Tabel breakpoint (sebagai DATA, bukan if-else)

Satuan konsentrasi: µg/m³. Setiap parameter punya daftar titik `(ISPU, konsentrasi)` berurutan naik.

| ISPU | PM10 | PM2.5 | SO2 | CO | O3 | NO2 | HC |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 50 | 50 | 15.5 | 52 | 4000 | 120 | 80 | 45 |
| 100 | 150 | 55.4 | 180 | 8000 | 235 | 200 | 100 |
| 200 | 350 | 150.4 | 400 | 15000 | 400 | 1130 | 215 |
| 300 | 420 | 250.4 | 800 | 30000 | 800 | 2260 | 432 |
| 500 | 500 | 500 | 1200 | 45000 | 1000 | 3000 | 648 |

**PERHATIAN:** Baris ISPU 0 sampai 300 sudah diverifikasi pemilik proyek dari laporan pembelajarannya. **Baris ISPU 500 belum diverifikasi** terhadap teks Permen. Tulis di kode sebagai konstanta terpisah dengan komentar `# TODO VERIFIKASI: cek ke Permen LHK P.14/2020 sebelum dipakai`, dan tampilkan peringatan itu di README.

HC **tidak tersedia** di Open-Meteo. Tetap simpan di tabel breakpoint untuk kelengkapan, tetapi tidak dihitung pada pilot.

### 4.2 Rumus

Interpolasi linear di dalam rentang yang memuat konsentrasi:

```
I = ((Ia - Ib) / (Xa - Xb)) * (Xx - Xb) + Ib
```

- `Ia`, `Ib` = ISPU batas atas dan bawah
- `Xa`, `Xb` = konsentrasi batas atas dan bawah
- `Xx` = konsentrasi hasil pengukuran (sudah dirata-ratakan, lihat 4.4)

Aturan implementasi:

- Cari rentang `(Xb, Xa)` yang memuat `Xx` dari tabel breakpoint parameter tersebut.
- Jika `Xx` tepat di batas, pakai rentang bawah supaya hasilnya konsisten (misalnya PM10 = 150 harus menghasilkan ISPU 100).
- Jika `Xx` melebihi batas teratas (baris 500), kembalikan 500 dan tandai `capped=True`.
- Jika `Xx` negatif atau `None`, kembalikan `None` (jangan menebak).
- Bulatkan hasil akhir ke bilangan bulat terdekat hanya pada tahap presentasi. Simpan nilai float di perhitungan.

### 4.3 Kategori

| Kategori | Rentang ISPU |
| --- | --- |
| Baik | 0 – 50 |
| Sedang | 51 – 100 |
| Tidak Sehat | 101 – 200 |
| Sangat Tidak Sehat | 201 – 300 |
| Berbahaya | ≥ 301 |

Warna marker di peta (sesuai status warna ISPU): Baik = hijau, Sedang = biru, Tidak Sehat = kuning, Sangat Tidak Sehat = merah, Berbahaya = hitam.

### 4.4 Rata-rata bergerak per parameter

Open-Meteo memberi nilai per jam, sedangkan ISPU memakai rata-rata dengan periode berbeda per parameter. Buat konstanta di `config.py`:

```python
# TODO VERIFIKASI: periode rata-rata di bawah adalah DEFAULT SEMENTARA.
# Cek periode pasti tiap parameter di Permen LHK P.14/2020 sebelum dipakai.
AVERAGING_HOURS = {
    "pm10": 24,
    "pm25": 24,
    "so2": 24,
    "co": 8,
    "o3": 8,
    "no2": 24,
}
```

Aturan:

- Untuk setiap jam target, hitung rata-rata dari N jam terakhir (termasuk jam target) sesuai konstanta di atas.
- **Aturan validitas 75%:** jika data valid dalam jendela kurang dari 75% dari N jam, hasil rata-rata = `None`, dan ISPU parameter itu = `None`.
- Nilai `None` dari API dianggap tidak valid.

### 4.5 Nilai ISPU lokasi

- Hitung ISPU tiap parameter (PM10, PM2.5, SO2, CO, O3, NO2).
- **ISPU lokasi = nilai maksimum** di antara parameter yang valid.
- Parameter penghasil nilai maksimum disimpan sebagai `critical_parameter`.
- Jika semua parameter `None`, ISPU lokasi = `None` dan kategori = "Tidak ada data".

### 4.6 Fungsi publik yang harus ada

```python
def hitung_ispu_parameter(parameter: str, konsentrasi: float | None) -> float | None: ...
def tentukan_kategori(ispu: float | None) -> str: ...
def hitung_ispu_lokasi(rata_rata: dict[str, float | None]) -> dict: ...
# hitung_ispu_lokasi mengembalikan:
# {"ispu": float|None, "critical_parameter": str|None,
#  "category": str, "per_parameter": {param: ispu}}
```

## 5. Pengujian `tests/test_ispu.py`

Wajib lulus sebelum lanjut ke integrasi API:

1. PM2.5 = 40 → ISPU ≈ 80,7 (toleransi 0,1), kategori Sedang. Perhitungan manual: `(100-50)/(55.4-15.5) * (40-15.5) + 50`.
2. PM10 = 200 → ISPU tepat 125, kategori Tidak Sehat. Perhitungan manual: `(200-100)/(350-150) * (200-150) + 100 = 125`.
3. Batas: PM10 = 0 → 0; PM10 = 50 → 50; PM10 = 150 → 100; PM10 = 350 → 200.
4. Di atas batas teratas → 500 dan `capped=True`.
5. Input `None` dan nilai negatif → `None`.
6. Kategori: 50 → Baik, 51 → Sedang, 100 → Sedang, 101 → Tidak Sehat, 200 → Tidak Sehat, 201 → Sangat Tidak Sehat, 300 → Sangat Tidak Sehat, 301 → Berbahaya.
7. `hitung_ispu_lokasi`: ambil maksimum dan `critical_parameter` benar (contoh: PM10=200 dan PM2.5=40 → ISPU 125, critical = pm10).
8. Rata-rata bergerak: jendela dengan data valid kurang dari 75% menghasilkan `None`.

**[STOP]** Setelah `ispu.py` dan semua tes lulus, tampilkan ringkasan hasil `pytest -v` dan tunggu konfirmasi sebelum lanjut.

## 6. Sumber Data: Open-Meteo

- Endpoint: `https://air-quality-api.open-meteo.com/v1/air-quality`
- Parameter: `latitude`, `longitude`, `hourly=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone`, `past_days=2`, `forecast_days=1`, `timezone=Asia/Jakarta`
- Tanpa API key.
- Data adalah **hasil model (CAMS), bukan pengukuran sensor stasiun**. Tampilkan catatan ini di footer `index.html` dan di README.
- Mapping nama: `pm2_5`→`pm25`, `carbon_monoxide`→`co`, `nitrogen_dioxide`→`no2`, `sulphur_dioxide`→`so2`, `ozone`→`o3`.
- Tangani error jaringan dan timeout (timeout 15 detik). Jika satu lokasi gagal, lanjutkan lokasi lain dan catat log.

## 7. Database

```
Location:     id (PK), name, lat, lon
Measurement:  id (PK), location_id (FK), timestamp,
              pm10, pm25, so2, co, o3, no2,          # konsentrasi mentah per jam
              ispu_value, critical_parameter, category
```

- Konsentrasi mentah dan hasil ISPU disimpan di baris yang sama, supaya bisa dihitung ulang bila rumus berubah.
- Unique constraint pada `(location_id, timestamp)`. Fetch ulang harus **update**, bukan menggandakan baris.
- Seed lokasi saat startup jika tabel `Location` kosong (lihat bagian 8).

## 8. Lokasi Seed (`config.py`)

Koordinat di bawah adalah perkiraan pusat kota, cukup untuk pilot.

| Nama | Lat | Lon |
| --- | --- | --- |
| Palembang | -2.9761 | 104.7754 |
| Prabumulih | -3.4333 | 104.2333 |
| Lubuklinggau | -3.2967 | 102.8617 |
| Baturaja | -4.1275 | 104.1667 |
| Jakarta (pembanding) | -6.2088 | 106.8456 |
| Bogor (pembanding) | -6.5971 | 106.8060 |

Fokus utama adalah Sumatera Selatan. Jakarta dan Bogor dipakai sebagai pembanding terhadap udara.jakarta.go.id.

## 9. REST API (`routes.py`)

| Method | Path | Fungsi |
| --- | --- | --- |
| GET | `/api/locations` | Daftar lokasi |
| GET | `/api/ispu/latest` | **GeoJSON FeatureCollection**: satu Feature (Point) per lokasi, `properties` berisi nama, ispu (dibulatkan), kategori, critical_parameter, timestamp, dan ISPU per parameter |
| GET | `/api/ispu/{location_id}/history?hours=48` | Riwayat ISPU per jam |
| POST | `/api/refresh` | Memicu fetch Open-Meteo untuk semua lokasi, hitung, simpan |
| GET | `/api/health` | `{"status": "ok"}` |

Catatan GeoJSON: urutan koordinat adalah `[lon, lat]`.

## 10. Frontend `static/index.html`

- Peta Leaflet (tile OpenStreetMap), pusat awal Sumatera Selatan, zoom 7.
- Muat `/api/ispu/latest`, gambar `circleMarker` berwarna sesuai kategori (bagian 4.3).
- Popup: nama lokasi, ISPU, kategori, parameter kritis, waktu data.
- Legenda warna kategori di sudut peta.
- Tombol "Refresh data" yang memanggil `POST /api/refresh` lalu memuat ulang marker.
- Footer: "Sumber data: Open-Meteo (model CAMS), bukan sensor stasiun. Parameter HC tidak tersedia."
- Lokasi dengan ISPU `None` ditampilkan abu-abu dengan label "Tidak ada data".

## 11. Urutan Pengerjaan

1. Buat struktur folder, `requirements.txt`, `.gitignore`, dan virtual environment.
2. Tulis `app/ispu.py` dan `tests/test_ispu.py`. Jalankan `pytest`. **[STOP]**
3. Tulis `db.py`, `models.py`, `config.py`.
4. Tulis `data_source.py`. Uji manual satu lokasi dan cetak 5 baris pertama hasil parse.
5. Tulis `service.py` (fetch → rata-rata bergerak → ISPU → simpan). Uji manual untuk Palembang.
6. Tulis `routes.py` dan `main.py`. Jalankan `uvicorn app.main:app --reload` dan uji tiap endpoint dengan `curl`.
7. Tulis `static/index.html`.
8. Tulis `README.md`: cara install, cara jalan, daftar endpoint, dan **daftar hal yang belum diverifikasi** (baris ISPU 500 dan periode rata-rata).

## 12. Aturan Umum untuk Agent

- Jangan membuat file di luar struktur yang disebut kecuali diminta.
- Jangan mengarang nilai breakpoint atau periode rata-rata. Nilai yang ditandai TODO VERIFIKASI harus tetap bertanda TODO di kode.
- Jangan menghapus tes agar build lulus. Jika tes gagal, perbaiki kodenya dan jelaskan penyebabnya.
- Setelah tiap langkah di bagian 11, ringkas apa yang dikerjakan dalam beberapa kalimat.
- Jika ada keputusan desain yang tidak tercakup di dokumen ini, tanyakan sebelum memutuskan.
