"""One entry point that emits all deliverable formats."""

from __future__ import annotations

from pathlib import Path

from strava_print.domain.models import Activity, Project
from strava_print.export.project_file import save_project
from strava_print.layouts.templates import load_template
from strava_print.model3d.exporters import export_stls
from strava_print.renderers.pdf_renderer import save_pdf
from strava_print.renderers.raster_renderer import save_raster
from strava_print.renderers.svg_renderer import save_svg


def export_all(
    activity: Activity, project: Project, output_dir: str | Path, stem: str = "activity"
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    template = load_template(project.template)
    files = {
        "svg": save_svg(output / f"{stem}.svg", activity, project, template),
        "pdf": save_pdf(output / f"{stem}.pdf", activity, project, template, calibration_page=True),
        "png": save_raster(output / f"{stem}.png", activity, project, template),
        "jpg": save_raster(output / f"{stem}.jpg", activity, project, template),
        "project": save_project(output / f"{stem}_project.json", project),
    }
    files.update(export_stls(activity, project.model_3d, output, stem))
    return files
