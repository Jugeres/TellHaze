"""
Pengujian modul inti ISPU (app/ispu.py).
Semua kasus diambil dari dokumen BUILD_ISPU_PILOT.md bagian 5.
"""

import pytest

from app.ispu import (
    hitung_ispu_lokasi,
    hitung_ispu_parameter,
    hitung_ispu_parameter_dengan_flag,
    rata_rata_bergerak,
    tentukan_kategori,
)


# --- 1. PM2.5 = 40 -> ISPU ~ 80,7 (toleransi 0,1), kategori Sedang ----------
def test_pm25_40_ispu_807():
    # Manual: (100-50)/(55.4-15.5) * (40-15.5) + 50
    ispu = hitung_ispu_parameter("pm25", 40)
    assert ispu == pytest.approx(80.7, abs=0.1)
    assert tentukan_kategori(ispu) == "Sedang"


# --- 2. PM10 = 200 -> ISPU tepat 125, kategori Tidak Sehat ------------------
def test_pm10_200_ispu_125():
    # Manual: (200-100)/(350-150) * (200-150) + 100 = 125
    ispu = hitung_ispu_parameter("pm10", 200)
    assert ispu == pytest.approx(125.0)
    assert tentukan_kategori(ispu) == "Tidak Sehat"


# --- 3. Batas-batas breakpoint ---------------------------------------------
@pytest.mark.parametrize(
    "konsentrasi, diharapkan",
    [(0, 0.0), (50, 50.0), (150, 100.0), (350, 200.0)],
)
def test_batas_pm10(konsentrasi, diharapkan):
    assert hitung_ispu_parameter("pm10", konsentrasi) == pytest.approx(diharapkan)


# --- 4. Di atas batas teratas -> 500 dan capped=True ------------------------
def test_di_atas_batas_teratas():
    ispu, capped = hitung_ispu_parameter_dengan_flag("pm10", 600)
    assert ispu == 500.0
    assert capped is True


# --- 5. Input None dan nilai negatif -> None --------------------------------
@pytest.mark.parametrize("nilai", [None, -1.0, -100])
def test_input_none_dan_negatif(nilai):
    assert hitung_ispu_parameter("pm10", nilai) is None


# --- 6. Kategori sesuai rentang ISPU -----------------------------------------
@pytest.mark.parametrize(
    "ispu, kategori",
    [
        (50, "Baik"),
        (51, "Sedang"),
        (100, "Sedang"),
        (101, "Tidak Sehat"),
        (200, "Tidak Sehat"),
        (201, "Sangat Tidak Sehat"),
        (300, "Sangat Tidak Sehat"),
        (301, "Berbahaya"),
    ],
)
def test_kategori(ispu, kategori):
    assert tentukan_kategori(float(ispu)) == kategori


def test_kategori_none():
    assert tentukan_kategori(None) == "Tidak ada data"


# --- 7. ISPU lokasi = maksimum antar parameter ------------------------------
def test_hitung_ispu_lokasi_maksimum():
    hasil = hitung_ispu_lokasi({"pm10": 200.0, "pm25": 40.0})
    assert hasil["ispu"] == pytest.approx(125.0)
    assert hasil["critical_parameter"] == "pm10"
    assert hasil["category"] == "Tidak Sehat"
    # PM2.5 ikut dihitung tapi bukan yang tertinggi.
    assert hasil["per_parameter"]["pm25"] == pytest.approx(80.7, abs=0.1)


def test_hitung_ispu_lokasi_semua_none():
    hasil = hitung_ispu_lokasi({"pm10": None, "pm25": None})
    assert hasil["ispu"] is None
    assert hasil["critical_parameter"] is None
    assert hasil["category"] == "Tidak ada data"


# --- 8. Rata-rata bergerak dengan aturan validitas 75% ----------------------
def test_rata_rata_bergerak_validitas_75_persen():
    # Jendela 8 jam, hanya 5 jam valid (62.5% < 75%) -> None.
    jendela = [10.0, 20.0, None, 30.0, None, None, 40.0, 50.0]
    assert rata_rata_bergerak(jendela) is None


def test_rata_rata_bergerak_cukup_valid():
    # Jendela 8 jam, 6 jam valid (tepat 75%) -> hitung rata-rata.
    jendela = [10.0, 20.0, None, 30.0, None, 40.0, 50.0, 60.0]
    # Rata-rata dari 10+20+30+40+50+60 = 210/6 = 35
    assert rata_rata_bergerak(jendela) == pytest.approx(35.0)


def test_rata_rata_bergerak_jendela_kosong():
    assert rata_rata_bergerak([]) is None
