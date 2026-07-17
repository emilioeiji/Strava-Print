"""Typed domain objects shared by parsing, rendering and export."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Literal

ActivityType = Literal["cycling", "running", "walking", "hiking", "generic"]
UnitSystem = Literal["metric", "imperial"]


@dataclass(frozen=True)
class TrackPoint:
    latitude: float
    longitude: float
    elevation_m: float | None = None
    time: datetime | None = None


@dataclass
class ActivityMetrics:
    distance_m: float = 0.0
    duration_s: float | None = None
    moving_time_s: float | None = None
    elevation_gain_m: float | None = None
    elevation_loss_m: float | None = None
    altitude_min_m: float | None = None
    altitude_max_m: float | None = None
    average_speed_mps: float | None = None
    max_speed_mps: float | None = None
    average_pace_s_per_km: float | None = None


@dataclass
class Activity:
    points: list[TrackPoint]
    metrics: ActivityMetrics
    start: TrackPoint | None = None
    end: TrackPoint | None = None
    bounds: tuple[float, float, float, float] | None = None
    center: tuple[float, float] | None = None
    source_name: str = ""


@dataclass
class PhotoSettings:
    path: str | None = None
    x: float = 50.0
    y: float = 50.0
    zoom: float = 1.0
    rotation: float = 0.0
    brightness: float = 1.0
    contrast: float = 1.0
    grayscale: bool = False
    overlay: Literal["none", "dark", "light"] = "none"
    rounded: bool = False


@dataclass
class Model3DSettings:
    width_mm: float = 130.0
    base_thickness_mm: float = 1.6
    route_height_mm: float = 1.2
    route_width_mm: float = 1.8
    margin_mm: float = 4.0
    mode: Literal["route_only", "flat_map", "terrain"] = "flat_map"
    dem_path: str | None = None
    terrain_height_mm: float = 8.0
    terrain_resolution: int = 96
    pins: bool = False


@dataclass
class Project:
    schema_version: int = 1
    source_gpx: str = ""
    template: str = "classic_portrait"
    paper: str = "A4"
    orientation: Literal["portrait", "landscape"] = "portrait"
    title: str = "Morning Ride"
    subtitle: str = ""
    date: str = ""
    location: str = ""
    country: str = ""
    description: str = ""
    activity_type: ActivityType = "cycling"
    units: UnitSystem = "metric"
    metrics: list[str] = field(
        default_factory=lambda: ["distance", "moving_time", "elevation_gain", "average_speed"]
    )
    theme: dict[str, Any] = field(default_factory=dict)
    photo: PhotoSettings = field(default_factory=PhotoSettings)
    route_2d: dict[str, Any] = field(default_factory=dict)
    model_3d: Model3DSettings = field(default_factory=Model3DSettings)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
