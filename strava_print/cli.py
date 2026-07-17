"""Command line entry point for non-interactive export."""

from __future__ import annotations

import argparse
from pathlib import Path

from strava_print.domain.models import Project
from strava_print.export.package import export_all
from strava_print.gpx.parser import parse_gpx
from strava_print.layouts.templates import available_templates


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate GPX poster and STL files.")
    parser.add_argument("--gpx", required=True)
    parser.add_argument("--template", default="classic_portrait", choices=available_templates())
    parser.add_argument("--title", default="")
    parser.add_argument("--location", default="")
    parser.add_argument("--country", default="")
    parser.add_argument("--photo")
    parser.add_argument("--dem", help="GeoTIFF DEM usado pelo modo terrain")
    parser.add_argument("--terrain-height", type=float, default=8.0)
    parser.add_argument("--terrain-resolution", type=int, default=96)
    parser.add_argument("--units", choices=["metric", "imperial"], default="metric")
    parser.add_argument("--output", required=True)
    parser.add_argument("--stem", default="activity")
    args = parser.parse_args()
    activity = parse_gpx(args.gpx)
    project = Project(
        source_gpx=str(args.gpx),
        template=args.template,
        title=args.title or Path(args.gpx).stem,
        location=args.location,
        country=args.country,
        units=args.units,
    )
    if args.photo:
        project.photo.path = args.photo
    if args.dem:
        project.model_3d.mode = "terrain"
        project.model_3d.dem_path = args.dem
        project.model_3d.terrain_height_mm = args.terrain_height
        project.model_3d.terrain_resolution = args.terrain_resolution
    files = export_all(activity, project, args.output, args.stem)
    print("Arquivos exportados:")
    for key, value in files.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
