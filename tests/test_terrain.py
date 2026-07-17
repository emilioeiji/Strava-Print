from pathlib import Path

import numpy as np
import rasterio
import trimesh
from rasterio.transform import from_bounds

from strava_print.domain.models import Model3DSettings
from strava_print.gpx.parser import parse_gpx
from strava_print.model3d.exporters import export_stls


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
