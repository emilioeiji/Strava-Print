"""ReportLab PDF renderer with physical page dimensions expressed in mm."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas

from strava_print.domain.models import Activity, Project
from strava_print.gpx.geometry import normalized_route
from strava_print.layouts.templates import Template
from strava_print.layouts.themes import THEMES


def save_pdf(
    path: str | Path,
    activity: Activity,
    project: Project,
    template: Template,
    calibration_page: bool = False,
) -> Path:
    output = Path(path)
    canvas = Canvas(str(output), pagesize=(template.width_mm * mm, template.height_mm * mm))
    colors = {**THEMES["Minimal Light"], **project.theme}
    e = template.elements
    canvas.setFillColor(colors["background"])
    canvas.rect(0, 0, template.width_mm * mm, template.height_mm * mm, fill=1, stroke=0)

    def y(value: float) -> float:
        return (template.height_mm - value) * mm

    if e.get("photo") and project.photo.path:
        photo = e["photo"]
        canvas.drawImage(
            ImageReader(project.photo.path),
            photo["x"] * mm,
            y(photo["y"] + photo["height"]),
            photo["width"] * mm,
            photo["height"] * mm,
            preserveAspectRatio=True,
            anchor="c",
            mask="auto",
        )
    canvas.setFillColor(colors["ink"])
    canvas.setFont("Helvetica-Bold", e["title"]["size"])
    canvas.drawString(
        e["title"]["x"] * mm, y(e["title"]["y"]), project.title or "Untitled activity"
    )
    canvas.setFillColor(colors["muted"])
    canvas.setFont("Helvetica", e["meta"]["size"])
    canvas.drawString(
        e["meta"]["x"] * mm,
        y(e["meta"]["y"]),
        " · ".join(v for v in [project.date, project.location, project.country] if v),
    )
    m = e["map"]
    canvas.setStrokeColor(colors["guide"])
    canvas.rect(m["x"] * mm, y(m["y"] + m["height"]), m["width"] * mm, m["height"] * mm, fill=0)
    points = normalized_route(
        activity.points, m["width"], m["height"], 4, float(project.route_2d.get("rotation", 0))
    )
    route = canvas.beginPath()
    route.moveTo((m["x"] + points[0, 0]) * mm, y(m["y"] + m["height"] - points[0, 1]))
    for x, yy in points[1:]:
        route.lineTo((m["x"] + x) * mm, y(m["y"] + m["height"] - yy))
    canvas.setStrokeColor(colors["accent"])
    canvas.setLineWidth(0.7 * mm)
    canvas.drawPath(route)
    canvas.setFont("Helvetica", e["footer"]["size"])
    canvas.setFillColor(colors["muted"])
    canvas.drawString(
        e["footer"]["x"] * mm,
        y(e["footer"]["y"]),
        project.description or "GPX PRINT · LOCAL EDITION",
    )
    canvas.showPage()
    if calibration_page:
        canvas.setFont("Helvetica", 12)
        canvas.drawString(
            20 * mm, (template.height_mm - 20) * mm, "Calibration: print at actual size / 100%"
        )
        canvas.rect(20 * mm, (template.height_mm - 80) * mm, 50 * mm, 50 * mm)
        canvas.line(
            20 * mm, (template.height_mm - 100) * mm, 120 * mm, (template.height_mm - 100) * mm
        )
        canvas.circle(70 * mm, (template.height_mm - 160) * mm, 50 * mm, fill=0)
        canvas.showPage()
    canvas.save()
    return output
