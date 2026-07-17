from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from strava_print.domain.models import Project
from strava_print.export.package import export_all
from strava_print.gpx.parser import parse_gpx


def test_export_dimensions_and_mesh(tmp_path: Path) -> None:
    activity = parse_gpx("tests/fixtures/sample.gpx")
    files = export_all(activity, Project(title="Test"), tmp_path, "test")
    assert Image.open(files["png"]).size == (2480, 3508)
    page = PdfReader(str(files["pdf"])).pages[0]
    assert abs(float(page.mediabox.width) / 72 * 25.4 - 210) < 0.1
    assert "<svg" in files["svg"].read_text(encoding="utf-8")
    assert files["combined"].stat().st_size > 100
