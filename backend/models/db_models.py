"""
db_models.py
------------
SQLAlchemy ORM models representing the database schema.

Flight: one row per flight (metadata)
TrajectoryPoint: one row per ADS-B position report, linked to a Flight
"""

from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Flight(Base):
    """
    Represents a single aircraft flight.
    icao24: ICAO 24-bit aircraft address (unique hardware ID).
    callsign: flight number/identifier (can change mid-flight).
    """
    __tablename__ = "flights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    icao24: Mapped[str] = mapped_column(String(10), index=True)
    callsign: Mapped[str] = mapped_column(String(20), nullable=True)
    origin_country: Mapped[str] = mapped_column(String(50), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    point_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # One-to-many: one flight has many trajectory points
    points: Mapped[list["TrajectoryPoint"]] = relationship(
        "TrajectoryPoint", back_populates="flight", cascade="all, delete-orphan"
    )


class TrajectoryPoint(Base):
    """
    A single ADS-B position report belonging to a flight.
    Stores both raw values and a flag for whether this point was 'gapped'
    (masked for evaluation, simulating an ADS-C coverage gap).
    """
    __tablename__ = "trajectory_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flight_id: Mapped[int] = mapped_column(ForeignKey("flights.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    altitude: Mapped[float] = mapped_column(Float, nullable=True)   # meters
    velocity: Mapped[float] = mapped_column(Float, nullable=True)   # m/s
    heading: Mapped[float] = mapped_column(Float, nullable=True)    # degrees
    vertical_rate: Mapped[float] = mapped_column(Float, nullable=True)  # m/s
    is_gapped: Mapped[bool] = mapped_column(Boolean, default=False)  # masked for eval

    flight: Mapped["Flight"] = relationship("Flight", back_populates="points")