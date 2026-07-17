"""DEM-backed, circular terrain meshes for printable route maps."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
import trimesh
from rasterio.enums import Resampling
from rasterio.warp import transform
from rasterio.windows import from_bounds

from strava_print.domain.models import Activity


class DEMError(ValueError):
    """Raised when a DEM cannot supply terrain for the activity."""


@dataclass(frozen=True)
class TerrainData:
    mesh: trimesh.Trimesh
    grid: np.ndarray
    base_thickness_mm: float
    height_mm: float


def _fill_nodata(values: np.ndarray, nodata: float | None) -> np.ndarray:
    result = np.asarray(values, dtype=float)
    invalid = ~np.isfinite(result)
    if nodata is not None:
        invalid |= np.isclose(result, nodata)
    if invalid.all():
        raise DEMError("O recorte do DEM não contém elevações válidas para esta rota.")
    result[invalid] = float(np.median(result[~invalid]))
    return result


def read_activity_dem(path: str | Path, activity: Activity, resolution: int) -> np.ndarray:
    """Read a square DEM crop around the GPX, reprojecting its coordinates if needed."""
    if resolution < 24:
        raise DEMError("A resolução de terreno precisa ser de pelo menos 24.")
    source = Path(path)
    if not source.exists():
        raise DEMError(f"Arquivo DEM não encontrado: {source}")
    with rasterio.open(source) as dataset:
        if dataset.crs is None:
            raise DEMError("O DEM precisa ter um CRS geográfico definido.")
        longitudes = [point.longitude for point in activity.points]
        latitudes = [point.latitude for point in activity.points]
        xs, ys = transform("EPSG:4326", dataset.crs, longitudes, latitudes)
        span = max(max(xs) - min(xs), max(ys) - min(ys))
        if span <= 0:
            span = max(abs(dataset.res[0]), abs(dataset.res[1])) * 16
        pad = span * 0.15
        left, right = min(xs) - pad, max(xs) + pad
        bottom, top = min(ys) - pad, max(ys) + pad
        center_x, center_y = (left + right) / 2, (bottom + top) / 2
        side = max(right - left, top - bottom)
        window = from_bounds(
            center_x - side / 2,
            center_y - side / 2,
            center_x + side / 2,
            center_y + side / 2,
            transform=dataset.transform,
        )
        data = dataset.read(
            1,
            window=window,
            out_shape=(resolution, resolution),
            boundless=True,
            fill_value=dataset.nodata,
            resampling=Resampling.bilinear,
        )
        return _fill_nodata(data, dataset.nodata)


def _sample_grid(grid: np.ndarray, positions: np.ndarray, diameter_mm: float) -> np.ndarray:
    height, width = grid.shape
    x = np.clip(positions[:, 0] / diameter_mm * (width - 1), 0, width - 1)
    y = np.clip((1 - positions[:, 1] / diameter_mm) * (height - 1), 0, height - 1)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, width - 1), np.minimum(y0 + 1, height - 1)
    tx, ty = x - x0, y - y0
    return (
        grid[y0, x0] * (1 - tx) * (1 - ty)
        + grid[y0, x1] * tx * (1 - ty)
        + grid[y1, x0] * (1 - tx) * ty
        + grid[y1, x1] * tx * ty
    )


def terrain_mesh(
    grid: np.ndarray, diameter_mm: float, base_thickness_mm: float, height_mm: float
) -> TerrainData:
    """Build a watertight radial mesh whose top surface samples the DEM."""
    rings = max(20, min(72, grid.shape[0] // 2))
    slices = max(48, min(144, grid.shape[1]))
    angles = np.linspace(0, 2 * np.pi, slices, endpoint=False)
    top_xy = [[diameter_mm / 2, diameter_mm / 2]]
    for ring in range(1, rings + 1):
        radius = diameter_mm / 2 * ring / rings
        top_xy.extend(
            [
                [diameter_mm / 2 + radius * np.cos(angle), diameter_mm / 2 + radius * np.sin(angle)]
                for angle in angles
            ]
        )
    xy = np.asarray(top_xy)
    sampled = _sample_grid(grid, xy, diameter_mm)
    relief = sampled - sampled.min()
    scale = height_mm / relief.max() if relief.max() > 1e-9 else 0.0
    top = np.column_stack((xy, base_thickness_mm + relief * scale))
    bottom = np.column_stack((xy, np.zeros(len(xy))))
    vertices = np.vstack((top, bottom))
    faces: list[list[int]] = []
    for slice_index in range(slices):
        next_slice = (slice_index + 1) % slices
        faces.append([0, 1 + slice_index, 1 + next_slice])
    for ring in range(1, rings):
        inner = 1 + (ring - 1) * slices
        outer = 1 + ring * slices
        for slice_index in range(slices):
            next_slice = (slice_index + 1) % slices
            faces.extend(
                [
                    [inner + slice_index, outer + slice_index, inner + next_slice],
                    [inner + next_slice, outer + slice_index, outer + next_slice],
                ]
            )
    offset = len(top)
    faces.extend([[offset + face[2], offset + face[1], offset + face[0]] for face in faces.copy()])
    boundary = 1 + (rings - 1) * slices
    for slice_index in range(slices):
        next_slice = (slice_index + 1) % slices
        faces.extend(
            [
                [boundary + slice_index, offset + boundary + slice_index, boundary + next_slice],
                [
                    boundary + next_slice,
                    offset + boundary + slice_index,
                    offset + boundary + next_slice,
                ],
            ]
        )
    mesh = trimesh.Trimesh(vertices=vertices, faces=np.asarray(faces), process=True)
    return TerrainData(mesh, grid, base_thickness_mm, height_mm)


def route_surface_heights(
    terrain: TerrainData, route: np.ndarray, diameter_mm: float
) -> np.ndarray:
    sampled = _sample_grid(terrain.grid, route, diameter_mm)
    relief = sampled - terrain.grid.min()
    source_span = terrain.grid.max() - terrain.grid.min()
    scale = terrain.height_mm / source_span if source_span > 1e-9 else 0.0
    return terrain.base_thickness_mm + relief * scale
