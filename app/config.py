"""
Konfigurasi global aplikasi: database, daftar lokasi seed, dan konstanta ISPU.
"""

# URL database. Default SQLite (file ispu.db). Untuk pindah ke PostgreSQL,
# cukup ganti variabel ini, misal:
#   postgresql://user:password@host:5432/ispu
DATABASE_URL = "sqlite:///./ispu.db"

# ---------------------------------------------------------------------------
# TODO VERIFIKASI: periode rata-rata di bawah adalah DEFAULT SEMENTARA.
# Cek periode pasti tiap parameter di Permen LHK P.14/2020 sebelum dipakai.
# ---------------------------------------------------------------------------
AVERAGING_HOURS = {
    "pm10": 24,
    "pm25": 24,
    "so2": 24,
    "co": 8,
    "o3": 8,
    "no2": 24,
}

# Lokasi seed (nama, provinsi, lat, lon). Koordinat adalah perkiraan pusat
# kota/kabupaten, cukup untuk pilot.
# Asal proyek: Sumatera Selatan + DKI Jakarta (pembanding).
# Perluasan dashboard: Jawa Barat dan Jawa Timur.
LOCATIONS_SEED = [
    # --- Sumatera Selatan ---
    ("Palembang", "Sumatera Selatan", -2.9761, 104.7754),
    ("Prabumulih", "Sumatera Selatan", -3.4333, 104.2333),
    ("Lubuklinggau", "Sumatera Selatan", -3.2967, 102.8617),
    ("Baturaja (OKU)", "Sumatera Selatan", -4.1275, 104.1667),
    # --- DKI Jakarta (pembanding) ---
    ("Jakarta", "DKI Jakarta", -6.2088, 106.8456),
    # --- Jawa Barat ---
    ("Kota Bandung", "Jawa Barat", -6.9175, 107.6191),
    ("Kota Cimahi", "Jawa Barat", -6.8722, 107.5403),
    ("Kota Bekasi", "Jawa Barat", -6.2383, 106.9756),
    ("Cikarang (Kab. Bekasi)", "Jawa Barat", -6.3049, 107.1500),
    ("Kota Bogor", "Jawa Barat", -6.5950, 106.8166),
    ("Cibinong (Kab. Bogor)", "Jawa Barat", -6.4817, 106.8533),
    ("Kota Depok", "Jawa Barat", -6.4000, 106.8186),
    ("Kota Sukabumi", "Jawa Barat", -6.9281, 106.9300),
    ("Kota Cirebon", "Jawa Barat", -6.7320, 108.5523),
    ("Kota Tasikmalaya", "Jawa Barat", -7.3274, 108.2207),
    ("Kota Banjar", "Jawa Barat", -7.3706, 108.5342),
    ("Garut", "Jawa Barat", -7.0386, 107.9166),
    ("Karawang", "Jawa Barat", -6.3221, 107.3053),
    ("Purwakarta", "Jawa Barat", -6.5569, 107.4433),
    ("Subang", "Jawa Barat", -6.5700, 107.7600),
    ("Sumedang", "Jawa Barat", -6.8447, 107.9264),
    ("Indramayu", "Jawa Barat", -6.3276, 108.3200),
    ("Majalengka", "Jawa Barat", -6.7914, 108.1900),
    ("Kuningan", "Jawa Barat", -6.9758, 108.4831),
    ("Ciamis", "Jawa Barat", -7.2767, 108.3536),
    ("Cianjur", "Jawa Barat", -6.8169, 107.1422),
    ("Pangandaran", "Jawa Barat", -7.6167, 108.5000),
    # --- Jawa Timur ---
    ("Kota Surabaya", "Jawa Timur", -7.2575, 112.7521),
    ("Kota Malang", "Jawa Timur", -7.9666, 112.6326),
    ("Kota Batu", "Jawa Timur", -7.8667, 112.4167),
    ("Kota Kediri", "Jawa Timur", -7.8482, 112.4429),
    ("Kota Madiun", "Jawa Timur", -7.6298, 111.5241),
    ("Kota Mojokerto", "Jawa Timur", -7.4664, 112.4338),
    ("Kota Pasuruan", "Jawa Timur", -7.6453, 112.9075),
    ("Kota Probolinggo", "Jawa Timur", -7.7545, 113.2131),
    ("Sidoarjo", "Jawa Timur", -7.4478, 112.7183),
    ("Gresik", "Jawa Timur", -7.1539, 112.6550),
    ("Jember", "Jawa Timur", -8.1728, 113.6995),
    ("Banyuwangi", "Jawa Timur", -8.2192, 114.3669),
    ("Kab. Blitar", "Jawa Timur", -8.1006, 112.1681),
    ("Ponorogo", "Jawa Timur", -7.8981, 111.4669),
    ("Ngawi", "Jawa Timur", -7.4056, 111.4464),
    ("Bojonegoro", "Jawa Timur", -7.2386, 111.6764),
    ("Tuban", "Jawa Timur", -6.8976, 111.9056),
    ("Lamongan", "Jawa Timur", -7.1097, 112.4167),
    ("Jombang", "Jawa Timur", -7.5464, 112.2331),
    ("Nganjuk", "Jawa Timur", -7.6031, 111.9036),
    ("Situbondo", "Jawa Timur", -7.7069, 114.0108),
    ("Bondowoso", "Jawa Timur", -7.9136, 113.8236),
    ("Lumajang", "Jawa Timur", -8.1356, 113.2231),
    ("Pacitan", "Jawa Timur", -7.7864, 111.0858),
    ("Bangkalan", "Jawa Timur", -7.0333, 112.7500),
    ("Pamekasan", "Jawa Timur", -7.1597, 113.4789),
    ("Sampang", "Jawa Timur", -6.8683, 113.2319),
    ("Sumenep", "Jawa Timur", -6.9667, 113.9333),
]

# Parameter Open-Meteo Air Quality yang diminta (nama asli API).
# Catatan: HC tidak tersedia di Open-Meteo, jadi tidak diminta.
OPEN_METEO_HOURLY = "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone"

# Endpoint Open-Meteo Air Quality (tanpa API key).
OPEN_METEO_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"

# Pengaturan fetch.
PAST_DAYS = 2          # ambil data 2 hari ke belakang untuk rata-rata bergerak
FORECAST_DAYS = 1
TIMEZONE = "Asia/Jakarta"
TIMEOUT_DETIK = 30     # timeout panggilan API

# Banyak lokasi per satu panggilan Open-Meteo (API mendukung multi-lokasi
# lewat latitude/longitude dipisah koma). Chunking menjaga respons tetap ringan.
CHUNK_LOKASI = 25

# Mapping nama variabel Open-Meteo -> nama internal kita.
OPEN_METEO_MAPPING = {
    "pm10": "pm10",
    "pm2_5": "pm25",
    "carbon_monoxide": "co",
    "nitrogen_dioxide": "no2",
    "sulphur_dioxide": "so2",
    "ozone": "o3",
}
