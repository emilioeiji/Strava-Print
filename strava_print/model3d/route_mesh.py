"""Generate a continuous, printable tube mesh for a normalized route."""

from __future__ import annotations

import numpy as np
import trimesh


def route_tube(
    points: np.ndarray, width_mm: float, z_mm: float | np.ndarray, sides: int = 8
) -> trimesh.Trimesh:
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("Os pontos da rota devem ter o formato (N, 2).")

    z_input = np.asarray(z_mm, dtype=float)
    if z_input.ndim > 1 or (z_input.ndim == 1 and len(z_input) != len(points)):
        raise ValueError("As alturas da rota devem ser um valor unico ou uma altura por ponto.")

    keep = np.r_[True, np.linalg.norm(np.diff(points, axis=0), axis=1) > 1e-6]
    points = points[keep]
    if len(points) < 2:
        raise ValueError("Rota sem pontos suficientes para STL.")
    z_values = np.full(len(points), float(z_input)) if z_input.ndim == 0 else z_input[keep]
    radius = width_mm / 2
    vertices: list[list[float]] = []
    for i, point in enumerate(points):
        direction = points[min(i + 1, len(points) - 1)] - points[max(0, i - 1)]
        length = np.linalg.norm(direction) or 1
        normal = np.array([-direction[1], direction[0]]) / length
        for side in range(sides):
            angle = 2 * np.pi * side / sides
            offset = normal * (np.cos(angle) * radius)
            vertices.append(
                [point[0] + offset[0], point[1] + offset[1], z_values[i] + np.sin(angle) * radius]
            )
    faces: list[list[int]] = []
    for i in range(len(points) - 1):
        for side in range(sides):
            a, b = i * sides + side, i * sides + (side + 1) % sides
            c, d = (i + 1) * sides + side, (i + 1) * sides + (side + 1) % sides
            faces.extend([[a, c, b], [b, c, d]])
    start_center = len(vertices)
    vertices.append([points[0, 0], points[0, 1], z_values[0]])
    for side in range(sides):
        faces.append([start_center, (side + 1) % sides, side])
    last = (len(points) - 1) * sides
    end_center = len(vertices)
    vertices.append([points[-1, 0], points[-1, 1], z_values[-1]])
    for side in range(sides):
        faces.append([end_center, last + side, last + (side + 1) % sides])
    return trimesh.Trimesh(vertices=np.asarray(vertices), faces=np.asarray(faces), process=True)
