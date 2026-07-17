"""Activity metric calculations independent of a particular GPX parser."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from strava_print.domain.models import ActivityMetrics, TrackPoint


def haversine_m(a: TrackPoint, b: TrackPoint) -> float:
    radius = 6_371_000.0
    lat_delta = radians(b.latitude - a.latitude)
    lon_delta = radians(b.longitude - a.longitude)
    lat_a, lat_b = radians(a.latitude), radians(b.latitude)
    h = sin(lat_delta / 2) ** 2 + cos(lat_a) * cos(lat_b) * sin(lon_delta / 2) ** 2
    return 2 * radius * asin(sqrt(h))


def calculate_metrics(points: list[TrackPoint]) -> ActivityMetrics:
    if len(points) < 2:
        return ActivityMetrics()
    distances = [haversine_m(a, b) for a, b in zip(points, points[1:])]
    total = sum(distances)
    timed = [(a, b, d) for a, b, d in zip(points, points[1:], distances) if a.time and b.time]
    duration = (
        (points[-1].time - points[0].time).total_seconds()
        if points[0].time and points[-1].time
        else None
    )
    moving = sum(
        (b.time - a.time).total_seconds()
        for a, b, d in timed
        if 0 < (b.time - a.time).total_seconds() <= 300 and d > 1
    )
    elevations = [p.elevation_m for p in points if p.elevation_m is not None]
    changes = [
        b.elevation_m - a.elevation_m
        for a, b in zip(points, points[1:])
        if a.elevation_m is not None and b.elevation_m is not None
    ]
    gain = sum(change for change in changes if change > 0)
    loss = -sum(change for change in changes if change < 0)
    active_duration = moving or duration
    avg_speed = total / active_duration if active_duration else None
    max_speed = max(
        (
            d / (b.time - a.time).total_seconds()
            for a, b, d in timed
            if (b.time - a.time).total_seconds() > 0
        ),
        default=None,
    )
    return ActivityMetrics(
        total,
        duration,
        moving or None,
        gain if elevations else None,
        loss if elevations else None,
        min(elevations) if elevations else None,
        max(elevations) if elevations else None,
        avg_speed,
        max_speed,
        (active_duration / (total / 1000)) if total and active_duration else None,
    )
