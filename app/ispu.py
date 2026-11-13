"""
Modul inti perhitungan ISPU (Indeks Standar Pencemar Udara)
berdasarkan Permen LHK No. P.14/MENLHK/SETJEN/KUM.1/7/2020.

Semua konsentrasi dalam satuan µg/m³.
"""

# ---------------------------------------------------------------------------
# Tabel breakpoint (DATA, bukan if-else)
# Format tiap parameter: daftar tuple (ISPU, konsentrasi) berurutan naik.
#
# PERHATIAN: baris ISPU 0 sampai 300 sudah diverifikasi pemilik proyek.
# Baris ISPU 500 ditambahkan terpisah di bawah karena BELUM diverifikasi.
# ---------------------------------------------------------------------------
BREAKPOINTS_TERIFIKASI: dict[str, list[tuple[float, float]]] = {
    "pm10": [(0, 0), (50, 50), (100, 150), (200, 350), (300, 420)],
    "pm25": [(0, 0), (50, 15.5), (100, 55.4), (200, 150.4), (300, 250.4)],
    "so2":  [(0, 0), (50, 52), (100, 180), (200, 400), (300, 800)],
    "co":   [(0, 0), (50, 4000), (100, 8000), (200, 15000), (300, 30000)],
    "o3":   [(0, 0), (50, 120), (100, 235), (200, 400), (300, 800)],
    "no2":  [(0, 0), (50, 80), (100, 200), (200, 1130), (300, 2260)],
    # HC tidak tersedia di Open-Meteo, disimpan hanya untuk kelengkapan.
    "hc":   [(0, 0), (50, 45), (100, 100), (200, 215), (300, 432)],
}

# TODO VERIFIKASI: cek ke Permen LHK P.14/2020 sebelum dipakai.
# Baris ISPU 500 ini BELUM diverifikasi terhadap teks Permen.
ROW_500: dict[str, tuple[float, float]] = {
    "pm10": (500, 500),
    "pm25": (500, 500),
    "so2":  (500, 1200),
    "co":   (500, 45000),
    "o3":   (500, 1000),
    "no2":  (500, 3000),
    "hc":   (500, 648),
}

# Gabungkan baris 500 ke tabel utama saat modul dimuat.
for _param, _titik in ROW_500.items():
    BREAKPOINTS_TERIFIKASI[_param].append(_titik)

# Nama parameter yang dihitung pada pilot (HC tidak tersedia di Open-Meteo).
PARAMETER_DIHITUNG = ["pm10", "pm25", "so2", "co", "o3", "no2"]


def _interpolasi_ispu(konsentrasi: float | None, breakpoint: list[tuple[float, float]]) -> tuple[float | None, bool]:
    """
    Hitung ISPU satu parameter dari konsentrasi (µg/m³).

    Rumus interpolasi linear:
        I = ((Ia - Ib) / (Xa - Xb)) * (Xx - Xb) + Ib

    Mengembalikan tuple (ispu, capped):
    - ispu: nilai ISPU (float) atau None bila tidak bisa dihitung.
    - capped: True bila konsentrasi melebihi batas teratas (ISPU ditetapkan 500).
    """
    # Aturan: input None atau negatif -> None (jangan menebak).
    if konsentrasi is None or konsentrasi < 0:
        return None, False

    # Cek dulu apakah konsentrasi tepat sama dengan salah satu titik breakpoint.
    # Cek dari baris terbawah agar "tepat di batas" memakai rentang bawah
    # (mis. PM10 = 150 -> ISPU 100, bukan nilai rentang atas).
    for ispu, x in breakpoint:
        if konsentrasi == x:
            return float(ispu), False

    # Cari rentang (Xb, Xa) yang memuat konsentrasi.
    for (ib, xb), (ia, xa) in zip(breakpoint, breakpoint[1:]):
        if xb < konsentrasi <= xa:
            hasil = ((ia - ib) / (xa - xb)) * (konsentrasi - xb) + ib
            return float(hasil), False

    # Melebihi batas teratas -> ISPU ditetapkan 500 dan ditandai capped.
    return 500.0, True


def hitung_ispu_parameter_dengan_flag(parameter: str, konsentrasi: float | None) -> tuple[float | None, bool]:
    """Versi hitung_ispu_parameter yang juga mengembalikan flag `capped`."""
    breakpoint = BREAKPOINTS_TERIFIKASI.get(parameter)
    if breakpoint is None:
        raise ValueError(f"Parameter tidak dikenal: {parameter}")
    return _interpolasi_ispu(konsentrasi, breakpoint)


def hitung_ispu_parameter(parameter: str, konsentrasi: float | None) -> float | None:
    """Hitung ISPU satu parameter. None bila konsentrasi None/negatif."""
    ispu, _capped = hitung_ispu_parameter_dengan_flag(parameter, konsentrasi)
    return ispu


def tentukan_kategori(ispu: float | None) -> str:
    """Terjemahkan nilai ISPU ke kategori sesuai Permen LHK P.14/2020."""
    if ispu is None:
        return "Tidak ada data"
    if ispu <= 50:
        return "Baik"
    if ispu <= 100:
        return "Sedang"
    if ispu <= 200:
        return "Tidak Sehat"
    if ispu <= 300:
        return "Sangat Tidak Sehat"
    return "Berbahaya"


def rata_rata_bergerak(nilai: list[float | None]) -> float | None:
    """
    Rata-rata dari satu jendela N jam (jendela SUDAH termasuk jam target).

    Aturan validitas 75%: jika jumlah data valid (bukan None) dalam jendela
    kurang dari 75% dari N jam, hasil = None.
    """
    n = len(nilai)
    if n == 0:
        return None
    valid = [v for v in nilai if v is not None and v >= 0]
    # Aturan 75%: valid harus minimal 75% dari N.
    if len(valid) < 0.75 * n:
        return None
    return sum(valid) / len(valid)


def hitung_ispu_lokasi(rata_rata: dict[str, float | None]) -> dict:
    """
    Hitung ISPU satu lokasi dari dict rata-rata konsentrasi per parameter.

    ISPU lokasi = nilai MAKSIMUM di antara parameter yang valid.
    Mengembalikan:
    {
      "ispu": float | None,
      "critical_parameter": str | None,
      "category": str,
      "per_parameter": {param: ispu},
    }
    """
    per_parameter: dict[str, float | None] = {}
    ispu_maks: float | None = None
    critical: str | None = None

    for param in PARAMETER_DIHITUNG:
        ispu = hitung_ispu_parameter(param, rata_rata.get(param))
        per_parameter[param] = ispu
        # Parameter diiterasi sesuai urutan daftar, jadi saat seri
        # parameter pertama yang menang jadi critical_parameter.
        if ispu is not None and (ispu_maks is None or ispu > ispu_maks):
            ispu_maks = ispu
            critical = param

    return {
        "ispu": ispu_maks,
        "critical_parameter": critical,
        "category": tentukan_kategori(ispu_maks),
        "per_parameter": per_parameter,
    }
