"""Export separate and combined STL assets with shared physical dimensions."""

from __future__ import annotations

from pathlib import Path

import trimesh

from strava_print.domain.models import Activity, Model3DSettings
from strava_print.gpx.geometry import fit_route_to_circle, normalized_route
from strava_print.model3d.base_mesh import round_base
from strava_print.model3d.route_mesh import route_tube


def export_stls(
    activity: Activity, settings: Model3DSettings, output_dir: str | Path, stem: str
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    route = normalized_route(activity.points, settings.width_mm, settings.width_mm, 0)
    route = fit_route_to_circle(route, settings.width_mm, settings.margin_mm)
    route_mesh = route_tube(
        route, settings.route_width_mm, settings.base_thickness_mm + settings.route_height_mm / 2
    )
    base = round_base(settings.width_mm, settings.base_thickness_mm)
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
