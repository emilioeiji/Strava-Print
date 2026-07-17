"""Conversions and display formatting for metric and imperial units."""

from __future__ import annotations

from strava_print.domain.models import UnitSystem

MILES_PER_METER = 0.000621371
FEET_PER_METER = 3.28084


def distance(value_m: float, units: UnitSystem) -> tuple[float, str]:
    return (value_m * MILES_PER_METER, "mi") if units == "imperial" else (value_m / 1000, "km")


def elevation(value_m: float, units: UnitSystem) -> tuple[float, str]:
    return (value_m * FEET_PER_METER, "ft") if units == "imperial" else (value_m, "m")


def speed(value_mps: float, units: UnitSystem) -> tuple[float, str]:
    return (value_mps * 2.236936, "mph") if units == "imperial" else (value_mps * 3.6, "km/h")


def duration(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    minutes, _ = divmod(round(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:d}:{minutes:02d}" if hours else f"{minutes:d} min"


def pace(seconds_per_km: float | None, units: UnitSystem) -> tuple[str, str]:
    if seconds_per_km is None:
        return "-", "min/km" if units == "metric" else "min/mi"
    value = seconds_per_km * 1.609344 if units == "imperial" else seconds_per_km
    minutes, seconds = divmod(round(value), 60)
    return f"{minutes}:{seconds:02d}", "min/mi" if units == "imperial" else "min/km"
