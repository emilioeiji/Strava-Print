"""Defensive GPX ingestion with understandable validation errors."""

from __future__ import annotations

from pathlib import Path

import gpxpy

from strava_print.domain.models import Activity, TrackPoint
from strava_print.gpx.metrics import calculate_metrics


class GPXError(ValueError):
    """Raised when no usable activity data can be read."""


def parse_gpx(path: str | Path) -> Activity:
    source = Path(path)
    if not source.exists():
        raise GPXError(f"Arquivo GPX não encontrado: {source}")
    try:
        document = gpxpy.parse(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, gpxpy.gpx.GPXXMLSyntaxException) as error:
        raise GPXError(f"Não foi possível ler o GPX: {error}") from error
    points: list[TrackPoint] = []
    for track in document.tracks:
        for segment in track.segments:
            for point in segment.points:
                if -90 <= point.latitude <= 90 and -180 <= point.longitude <= 180:
                    points.append(
                        TrackPoint(point.latitude, point.longitude, point.elevation, point.time)
                    )
    if len(points) < 2:
        raise GPXError("O GPX precisa conter pelo menos dois pontos válidos de rota.")
    lats, lons = [p.latitude for p in points], [p.longitude for p in points]
    return Activity(
        points,
        calculate_metrics(points),
        points[0],
        points[-1],
        (min(lats), min(lons), max(lats), max(lons)),
        (sum(lats) / len(lats), sum(lons) / len(lons)),
        source.name,
    )
