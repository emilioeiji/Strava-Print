"""Export separate and combined STL assets with shared physical dimensions."""

from __future__ import annotations

from pathlib import Path

import trimesh

from strava_print.domain.models import Activity, Model3DSettings
from strava_print.gpx.geometry import fit_route_to_circle, normalized_route
from strava_print.model3d.base_mesh import round_base
from strava_print.model3d.route_mesh import route_tube
from strava_print.model3d.terrain import read_activity_dem, route_surface_heights, terrain_mesh


def export_stls(
    activity: Activity, settings: Model3DSettings, output_dir: str | Path, stem: str
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    route = normalized_route(activity.points, settings.width_mm, settings.width_mm, 0)
    route = fit_route_to_circle(route, settings.width_mm, settings.margin_mm)
    if settings.mode == "terrain":
        if not settings.dem_path:
            raise ValueError("O modo Terrain requer um GeoTIFF DEM.")
        grid = read_activity_dem(settings.dem_path, activity, settings.terrain_resolution)
        terrain = terrain_mesh(
            grid, settings.width_mm, settings.base_thickness_mm, settings.terrain_height_mm
        )
        base = terrain.mesh
        route_z = (
            route_surface_heights(terrain, route, settings.width_mm) + settings.route_height_mm / 2
        )
    else:
        base = round_base(settings.width_mm, settings.base_thickness_mm)
        route_z = settings.base_thickness_mm + settings.route_height_mm / 2
    route_mesh = route_tube(route, settings.route_width_mm, route_z)
    combined = trimesh.util.concatenate([base, route_mesh])
    files = {
        "base": output / f"{stem}_base.stl",
        "route": output / f"{stem}_route.stl",
        "combined": output / f"{stem}_combined.stl",
    }
    base.export(files["base"])
    route_mesh.export(files["route"])
    combined.export(files["combined"])
    return files
