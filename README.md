# TellHaze 🌫️

Dashboard pemantau kualitas udara (ISPU) interaktif berbasis web untuk 55 kota di Indonesia (Sumsel, Jakarta, Jabar, dan Jatim).

Dibuat sebagai pilot. Data polutan diambil secara berkala dari Open-Meteo Air Quality API, dihitung menjadi nilai ISPU standar KLHK, lalu divisualisasikan dalam peta interaktif.

---

### ✨ Fitur Utama
- **Peta Interaktif (Leaflet):** Marker kota dengan warna sesuai kategori ISPU (Baik sampai Berbahaya), filter per provinsi.
- **Detail & Riwayat:** Grafik tren 24 jam ke belakang + 24 jam perkiraan model (Chart.js), saran kesehatan, dan rincian parameter kritis (PM2.5, PM10, CO, SO2, NO2, O3).
- **Tema Gelap & Terang:** Dilengkapi toggle Dark Ember & Light Mode (tile peta ikut menyesuaikan).
- **Auto-Refresh & CSV:** Jadwal refresh otomatis (1/5/15 menit) serta fitur ekspor dan impor lokasi via CSV.

---

### 🚀 Cara Menjalankan

1. **Clone & Setup Environment**
   ```bash
   git clone https://github.com/Jugeres/TellHaze.git
   cd TellHaze
   python -m venv .venv
   .\.venv\Scripts\activate   # Linux/Mac: source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Jalankan Server**
   ```bash
   uvicorn app.main:app --port 8000
   ```

3. Buka browser di `http://127.0.0.1:8000/`.  
   *(Dokumentasi API interaktif otomatis tersedia di `http://127.0.0.1:8000/docs`)*

---

### 🛠️ Tech Stack
- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, SQLite
- **Frontend:** Vanilla JS, Leaflet.js, Chart.js (tanpa build tool / single static file)
- **Data Source:** Open-Meteo Air Quality API (CAMS atmospheric model)
- **Testing:** Pytest (24 unit tests untuk formula ISPU)

---

### 📝 Catatan Tambahan
- Data polutan saat ini ditarik dari hasil model Open-Meteo (bukan stasiun sensor fisik langsung di lapangan).
- Parameter HC (hidrokarbon) belum dihitung karena ketiadaan data dari Open-Meteo.
- Dua angka masih perlu dicek ke teks asli Permen LHK P.14/2020 sebelum dipakai serius: baris ISPU 500 (`app/ispu.py`) dan periode rata-rata bergerak (`app/config.py`). Keduanya ditandai `# TODO VERIFIKASI` di kode.
