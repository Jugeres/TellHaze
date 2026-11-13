# AGENTS.md — Memori Proyek TellHaze (ISPU Pilot)

> Baca file ini di awal setiap sesi sebelum menyentuh kode.
> Dokumen brief asli proyek: `BUILD_ISPU_PILOT.md` (instruksi build pilot dasar).

## 1. Apa proyek ini

Dashboard kualitas udara **TellHaze** untuk Kerja Praktik di Telkomsat.
Mengambil data polutan per jam dari **Open-Meteo Air Quality API (model CAMS)**,
menghitung **ISPU** sesuai **Permen LHK P.14/MENLHK/SETJEN/KUM.1/7/2020**,
menyimpan ke SQLite, menyediakan REST API, dan menampilkan peta + dashboard.

- Referensi UI yang diinginkan pemilik: nusantara360.id/pantau (Smoke Haze Monitor) —
  **terinspirasi, jangan ditiru mentah-mentah**. TellHaze punya identitas visual sendiri:
  latar kabut biru-pucat `#e7edf1`, tinta teal `#123b47`, font Bricolage Grotesque +
  Instrument Sans, angka ISPU raksasa sebagai satu-satunya elemen berani.
- Cakupan lokasi (55 kota): Sumatera Selatan (asal proyek), DKI Jakarta (pembanding),
  Jawa Barat (22), Jawa Timur (28). Tambah kota baru lewat `LOCATIONS_SEED` di `app/config.py`.

## 2. Peta file (siapa mengerjakan apa)

| File | Peran |
| --- | --- |
| `app/ispu.py` | INTI: tabel breakpoint (data, bukan if-else), interpolasi linear, kategori, rata-rata bergerak 75%, `hitung_ispu_lokasi` |
| `app/config.py` | `DATABASE_URL`, `LOCATIONS_SEED`, `AVERAGING_HOURS`, konstanta Open-Meteo |
| `app/data_source.py` | Fetch batch multi-lokasi Open-Meteo (`fetch_multi`, chunk 25 lokasi/request) |
| `app/service.py` | Alur: fetch → rata-rata bergerak → ISPU → upsert DB (update, jangan gandakan) |
| `app/models.py` | `Location` (punya kolom `province`) dan `Measurement` (konsentrasi mentah + ISPU, unique `(location_id, timestamp)`) |
| `app/routes.py` | Endpoint API |
| `app/main.py` | Entrypoint FastAPI, buat tabel + seed lokasi saat startup, mount `static/` |
| `static/index.html` | SELURUH frontend (satu file, vanilla JS + Leaflet + Chart.js via CDN, tanpa build step) |
| `tests/test_ispu.py` | 24 unit test wajib lulus |

## 3. Perintah penting (Windows / PowerShell)

```powershell
# Jangan pakai "&&" di PowerShell — jalankan per perintah atau pakai ";"
.\.venv\Scripts\python.exe -m pytest tests\test_ispu.py -v   # jalankan dari root proyek
.\.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
.\.venv\Scripts\python.exe -m app.service                     # uji manual service
.\.venv\Scripts\python.exe -m app.data_source                 # uji manual fetch
```

- Kode Python dijalankan **sebagai module** (`-m app.xxx`) dari root proyek, bukan path file.
- `tzdata` ada di requirements — **wajib di Windows** untuk `zoneinfo` (Asia/Jakarta).

## 4. Kebiasaan kerja (before / during / after)

### Sebelum mengerjakan
1. Baca AGENTS.md ini + cek `git log --oneline` dan `git status` untuk tahu kondisi terakhir.
2. Jika ada rencana besar, diskusikan dulu; perubahan skema DB diumumkan dulu.
3. Pastikan server jalan bila perlu: cek `http://127.0.0.1:8000/api/health`.

### Saat mengerjakan
1. Komentar kode **berbahasa Indonesia**, sederhana dan mudah dibaca (proyek belajar KP).
2. Jangan menambah library tanpa alasan yang dituliskan di `requirements.txt`.
3. Komentar `# TODO VERIFIKASI` adalah **tanda merah yang tidak boleh dihapus**:
   - baris ISPU 500 di `app/ispu.py` (konstanta `ROW_500`) — belum diverifikasi ke Permen;
   - periode rata-rata `AVERAGING_HOURS` di `app/config.py` — default sementara.
4. Tes wajib lulus (`pytest`) sebelum fitur dianggap selesai; jika gagal, perbaiki kodenya
   atau koreksi tes yang salah datanya — **jelaskan penyebabnya, jangan hapus tes**.
5. Bila mengubah UI, kerjakan iteratif: ubah → reload → screenshot/cek snapshot → perbaiki.

### Setelah mengerjakan
1. Jalankan `pytest` + cek endpoint yang tersentuh (curl) sebelum mengatakan selesai.
2. **Bersihkan artefak sementara**: screenshot PNG di root, folder `.playwright-cli/`.
3. **Commit ke Git** dengan pesan yang jelas (feat/fix/chore + ringkasan) —
   setiap fitur/bugfix selesai langsung di-commit, ini safety net pemilik proyek.
4. Ringkas hasil: apa yang berubah, apa yang dites, apa yang masih perlu dilakukan.

## 5. Catatan teknis yang pernah menjadi jebakan

- Ganti skema DB → **hapus `ispu.db`** lalu restart server + `POST /api/refresh`
  (data bisa diambil ulang dari Open-Meteo, jadi aman).
- Chart.js: canvas HARUS dibungkus `<div class="wadah-grafik">` tinggi tetap,
  jangan paksa width/height canvas dengan `!important` (grafik ter-squash).
- `uvicorn` berjalan di background OpenCode — matikan dulu via port 8000 sebelum
  skema/`routes.py` berubah besar: `Stop-Process -Id (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess`.
- Marker lokasi tanpa data ditampilkan abu-abu kecil, label "Tidak ada data".
- Playwright dijalankan **headed** (`--headed`) supaya pemilik bisa melihat realtime;
  mode default headless tidak menampilkan jendela.
