"""Bridge persisted Django projects to the existing render and 3D engine."""

from __future__ import annotations

import shutil
import zipfile
from dataclasses import asdict
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.text import slugify

from strava_print.domain.models import Model3DSettings, PhotoSettings, Project
from strava_print.export.package import export_all
from strava_print.gpx.parser import parse_gpx
from strava_print.layouts.templates import load_template
from strava_print.layouts.themes import MATERIALS, ROUTE_COLORS, THEMES
from strava_print.renderers.preview_renderer import render_mounted_preview
from studio.models import ExportArtifact, PrintProject


def parse_activity(project: PrintProject):
    return parse_gpx(project.gpx_file.path)


def update_activity_metadata(project: PrintProject) -> None:
    activity = parse_activity(project)
    project.metrics_data = asdict(activity.metrics)
    if project.name == "Nova atividade":
        project.name = Path(project.gpx_file.name).stem.replace("_", " ")
    if project.title == "Morning Ride" and project.name:
        project.title = project.name
    project.status = PrintProject.Status.READY
    project.error_message = ""
    project.save(update_fields=["metrics_data", "name", "title", "status", "error_message", "updated_at"])


def build_domain_project(project: PrintProject) -> Project:
    theme_name = project.theme_name if project.theme_name in THEMES else "Gallery Edition"
    material_name = project.theme_settings.get("material_name", next(iter(MATERIALS)))
    route_color_name = project.theme_settings.get("route_color_name", next(iter(ROUTE_COLORS)))
    theme = {
        **THEMES[theme_name],
        "material": MATERIALS.get(material_name, next(iter(MATERIALS.values()))),
        "accent": ROUTE_COLORS.get(route_color_name, next(iter(ROUTE_COLORS.values()))),
    }
    photo_data = {**project.photo_settings}
    photo_data["path"] = project.photo_file.path if project.photo_file else None
    model_data = {
        "mode": "terrain" if project.dem_file else "flat_map",
        **project.model3d_settings,
    }
    model_data["dem_path"] = project.dem_file.path if project.dem_file else None
    return Project(
        source_gpx=project.source_filename,
        template=project.template_name,
        title=project.title,
        subtitle=project.subtitle,
        date=project.date,
        location=project.location,
        country=project.country,
        description=project.description,
        activity_type=project.activity_type,
        units=project.units,
        metrics=project.visible_metrics,
        theme=theme,
        photo=PhotoSettings(**photo_data),
        route_2d=project.route_settings,
        model_3d=Model3DSettings(**model_data),
    )


def generate_preview(project: PrintProject) -> str:
    activity = parse_activity(project)
    domain_project = build_domain_project(project)
    template = load_template(domain_project.template)
    image = render_mounted_preview(activity, domain_project, template, dpi=120)
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=90, optimize=True)
    if project.preview_file:
        project.preview_file.delete(save=False)
    project.preview_file.save("mounted-preview.jpg", ContentFile(buffer.getvalue()), save=False)
    project.metrics_data = asdict(activity.metrics)
    project.status = PrintProject.Status.READY
    project.error_message = ""
    project.save()
    return project.preview_file.url


@transaction.atomic
def generate_exports(project: PrintProject) -> list[ExportArtifact]:
    activity = parse_activity(project)
    domain_project = build_domain_project(project)
    export_dir = Path(settings.MEDIA_ROOT) / "projects" / str(project.id) / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    stem = slugify(project.name) or "activity"
    files = export_all(activity, domain_project, export_dir, stem)

    package_path = export_dir / f"{stem}_complete.zip"
    with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files.values():
            archive.write(path, path.name)
    files["package"] = package_path

    artifacts = []
    for kind, path in files.items():
        relative = path.relative_to(settings.MEDIA_ROOT).as_posix()
        artifact, _ = ExportArtifact.objects.update_or_create(
            project=project,
            kind=kind,
            defaults={"file": relative, "size_bytes": path.stat().st_size},
        )
        artifacts.append(artifact)
    project.status = PrintProject.Status.COMPLETE
    project.error_message = ""
    project.save(update_fields=["status", "error_message", "updated_at"])
    return artifacts


def delete_project_files(project: PrintProject) -> None:
    directory = Path(settings.MEDIA_ROOT) / "projects" / str(project.id)
    if directory.exists():
        shutil.rmtree(directory)


def metric_cards(project: PrintProject) -> list[dict[str, str]]:
    values = project.metrics_data
    distance_m = float(values.get("distance_m") or 0)
    moving_s = values.get("moving_time_s") or values.get("duration_s")
    gain = values.get("elevation_gain_m")
    speed = values.get("average_speed_mps")

    def duration(value: float | None) -> str:
        if value is None:
            return "—"
        total = int(value)
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"

    return [
        {"label": "Distância", "value": f"{distance_m / 1000:.2f}", "unit": "km"},
        {"label": "Tempo", "value": duration(moving_s), "unit": "h:min:s"},
        {"label": "Elevação", "value": f"{float(gain or 0):.0f}", "unit": "m"},
        {"label": "Média", "value": f"{float(speed or 0) * 3.6:.1f}", "unit": "km/h"},
    ]
