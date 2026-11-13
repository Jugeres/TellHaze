"""
Model tabel database: Location dan Measurement.

Konsentrasi mentah dan hasil ISPU disimpan di baris yang sama,
supaya bisa dihitung ulang bila rumus ISPU berubah.
"""

from datetime import datetime

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Location(Base):
    """Titik lokasi pemantauan (kota)."""

    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    province: Mapped[str] = mapped_column(String(50))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)

    measurements: Mapped[list["Measurement"]] = relationship(back_populates="location")


class Measurement(Base):
    """Satu baris = satu jam satu lokasi: konsentrasi mentah + hasil ISPU."""

    __tablename__ = "measurements"
    __table_args__ = (
        # Fetch ulang harus update baris lama, bukan menggandakan.
        UniqueConstraint("location_id", "timestamp", name="uq_location_timestamp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(ForeignKey("locations.id"))

    timestamp: Mapped[datetime] = mapped_column()

    # Konsentrasi mentah per jam (µg/m³), None bila data tidak tersedia.
    pm10: Mapped[float | None] = mapped_column(Float, nullable=True)
    pm25: Mapped[float | None] = mapped_column(Float, nullable=True)
    so2: Mapped[float | None] = mapped_column(Float, nullable=True)
    co: Mapped[float | None] = mapped_column(Float, nullable=True)
    o3: Mapped[float | None] = mapped_column(Float, nullable=True)
    no2: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Hasil perhitungan ISPU untuk baris (jam) ini.
    ispu_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    critical_parameter: Mapped[str | None] = mapped_column(String(10), nullable=True)
    category: Mapped[str | None] = mapped_column(String(30), nullable=True)

    location: Mapped["Location"] = relationship(back_populates="measurements")
