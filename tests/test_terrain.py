from pathlib import Path

import numpy as np
import rasterio
import trimesh
from rasterio.transform import from_bounds

from strava_print.domain.models import Model3DSettings
from strava_print.gpx.parser import parse_gpx
from strava_print.model3d.exporters import export_stls


def _is_single_body(mesh: trimesh.Trimesh) -> bool:
    neighbors: dict[int, set[int]] = {index: set() for index in range(len(mesh.faces))}
    for first, second in mesh.face_adjacency:
        neighbors[int(first)].add(int(second))
        neighbors[int(second)].add(int(first))
    visited = {0}
    pending = [0]
    while pending:
        current = pending.pop()
        unseen = neighbors[current] - visited
        visited.update(unseen)
        pending.extend(unseen)
    return len(visited) == len(mesh.faces)


def test_dem_terrain_generates_watertight_stl(tmp_path: Path) -> None:
    dem_path = tmp_path / "terrain.tif"
    data = np.add.outer(np.arange(64, dtype=np.float32), np.arange(64, dtype=np.float32))
    with rasterio.open(
        dem_path,
        "w",
        driver="GTiff",
        width=64,
        height=64,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_bounds(132.70, 35.30, 132.80, 35.40, 64, 64),
    ) as dataset:
        dataset.write(data, 1)
    settings = Model3DSettings(mode="terrain", dem_path=str(dem_path), terrain_resolution=48)
    files = export_stls(parse_gpx("tests/fixtures/sample.gpx"), settings, tmp_path, "terrain")
    assert files["combined"].stat().st_size > 100
    assert trimesh.load(files["combined"], force="mesh").is_watertight
    base = trimesh.load(files["base"], force="mesh")
    route = trimesh.load(files["route"], force="mesh")
    assert base.is_watertight
    assert route.is_watertight
    assert np.isclose(route.bounds[0, 2], 0, atol=1e-6)
    assert _is_single_body(route)
