"""Projection and normalization of routes for visual and 3D output."""

from __future__ import annotations

from math import cos, radians, sin

import numpy as np

from strava_print.domain.models import TrackPoint


def normalized_route(
    points: list[TrackPoint],
    width: float,
    height: float,
    margin: float = 0.0,
    rotation: float = 0.0,
) -> np.ndarray:
    if len(points) < 2:
        raise ValueError("A rota precisa ter ao menos dois pontos.")
    lat0 = sum(point.latitude for point in points) / len(points)
    raw = np.array(
        [
            [
                (point.longitude - points[0].longitude) * cos(radians(lat0)),
                point.latitude - points[0].latitude,
            ]
            for point in points
        ],
        dtype=float,
    )
    raw -= raw.mean(axis=0)
    if rotation:
        angle = radians(rotation)
        raw = raw @ np.array([[cos(angle), -sin(angle)], [sin(angle), cos(angle)]])
    span = np.ptp(raw, axis=0)
    usable_w, usable_h = max(width - margin * 2, 1), max(height - margin * 2, 1)
    scale = min(usable_w / max(span[0], 1e-12), usable_h / max(span[1], 1e-12))
    return raw * scale + np.array([width / 2, height / 2])
