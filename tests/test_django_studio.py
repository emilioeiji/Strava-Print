import json
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from studio.models import ExportArtifact, PrintProject


def _gpx_upload() -> SimpleUploadedFile:
    content = Path("tests/fixtures/sample.gpx").read_bytes()
    return SimpleUploadedFile("sample.gpx", content, content_type="application/gpx+xml")


def _editor_data(project: PrintProject) -> dict[str, object]:
    return {
        "name": project.name,
        "title": project.title,
        "subtitle": "Collector Series",
        "date": "2026-07-18",
        "location": "Izumo, Shimane",
        "country": "Japan",
        "description": "Morning roads",
        "template_name": "classic_portrait",
        "theme_name": "Gallery Edition",
        "activity_type": "cycling",
        "units": "metric",
        "visible_metrics": ["distance", "moving_time", "elevation_gain", "average_speed"],
        "material": "Burnished Bronze",
        "route_color": "Signal Orange",
        "route_rotation": 0,
        "model_mode": "flat_map",
        "width_mm": 130,
        "base_thickness_mm": 1.6,
        "route_width_mm": 1.8,
        "route_height_mm": 1.2,
        "terrain_height_mm": 8,
        "terrain_route_style": "inlay",
        "inlay_clearance_mm": 0.15,
        "photo_x": 50,
        "photo_y": 50,
        "photo_zoom": 1,
        "photo_rotation": 0,
        "photo_brightness": 1,
        "photo_contrast": 1,
        "photo_overlay": "none",
    }


@pytest.mark.django_db
def test_create_project_generates_metrics_and_preview(client: Client, settings, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = tmp_path

    response = client.post(
        reverse("studio:create"),
        {"name": "Sample Ride", "gpx_file": _gpx_upload()},
    )

    project = PrintProject.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("studio:editor", args=[project.id])
    assert project.metrics_data["distance_m"] > 0
    assert project.preview_file
    assert Path(project.preview_file.path).exists()


@pytest.mark.django_db
def test_project_is_private_to_its_session(client: Client, settings, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = tmp_path
    client.post(reverse("studio:create"), {"name": "Private", "gpx_file": _gpx_upload()})
    project = PrintProject.objects.get()

    other_client = Client()
    response = other_client.get(reverse("studio:editor", args=[project.id]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_editor_preview_and_complete_export(client: Client, settings, tmp_path: Path) -> None:
    settings.MEDIA_ROOT = tmp_path
    client.post(reverse("studio:create"), {"name": "Production", "gpx_file": _gpx_upload()})
    project = PrintProject.objects.get()
    data = _editor_data(project)

    editor_response = client.get(reverse("studio:editor", args=[project.id]))
    preview_response = client.post(reverse("studio:preview", args=[project.id]), data)
    export_response = client.post(reverse("studio:export", args=[project.id]), data)

    assert editor_response.status_code == 200
    assert preview_response.status_code == 200
    assert preview_response.json()["metrics"][0]["label"] == "Distância"
    assert export_response.status_code == 200
    assert ExportArtifact.objects.filter(project=project, kind="package").exists()
    project.refresh_from_db()
    assert project.status == PrintProject.Status.COMPLETE
    package = ExportArtifact.objects.get(project=project, kind="package")
    assert Path(package.file.path).stat().st_size > 100
    project_json = ExportArtifact.objects.get(project=project, kind="project")
    saved_project = json.loads(Path(project_json.file.path).read_text(encoding="utf-8"))
    assert str(settings.MEDIA_ROOT) not in json.dumps(saved_project)

    download = client.get(reverse("studio:download", args=[project.id, package.id]))
    assert download.status_code == 200
    assert download["Content-Disposition"].startswith("attachment;")
