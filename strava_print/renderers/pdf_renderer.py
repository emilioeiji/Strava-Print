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
from strava_print.renderers.svg_renderer import _metric_values


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
    elements = template.elements
    canvas.setFillColor(colors["background"])
    canvas.rect(0, 0, template.width_mm * mm, template.height_mm * mm, fill=1, stroke=0)

    def y(value: float) -> float:
        return (template.height_mm - value) * mm

    if elements.get("photo") and project.photo.path:
        photo = elements["photo"]
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
    title = elements["title"]
    canvas.setFillColor(colors["ink"])
    canvas.setFont("Helvetica-Bold", title["size"])
    text = project.title or "Untitled activity"
    if title.get("align") == "center":
        canvas.drawCentredString(title["x"] * mm, y(title["y"]), text)
    else:
        canvas.drawString(title["x"] * mm, y(title["y"]), text)
    meta_element = elements["meta"]
    meta = " / ".join(value for value in [project.date, project.location, project.country] if value)
    canvas.setFillColor(colors["muted"])
    canvas.setFont("Helvetica", meta_element["size"])
    if meta_element.get("align") == "center":
        canvas.drawCentredString(meta_element["x"] * mm, y(meta_element["y"]), meta)
    else:
        canvas.drawString(meta_element["x"] * mm, y(meta_element["y"]), meta)
    map_box = elements["map"]
    canvas.setStrokeColor(colors["guide"])
    if map_box.get("shape") == "circle":
        canvas.circle(
            (map_box["x"] + map_box["width"] / 2) * mm,
            y(map_box["y"] + map_box["height"] / 2),
            min(map_box["width"], map_box["height"]) / 2 * mm,
            fill=0,
        )
    else:
        canvas.rect(
            map_box["x"] * mm,
            y(map_box["y"] + map_box["height"]),
            map_box["width"] * mm,
            map_box["height"] * mm,
            fill=0,
        )
    points = normalized_route(
        activity.points,
        map_box["width"],
        map_box["height"],
        4,
        float(project.route_2d.get("rotation", 0)),
    )
    route = canvas.beginPath()
    route.moveTo(
        (map_box["x"] + points[0, 0]) * mm, y(map_box["y"] + map_box["height"] - points[0, 1])
    )
    for x, route_y in points[1:]:
        route.lineTo((map_box["x"] + x) * mm, y(map_box["y"] + map_box["height"] - route_y))
    canvas.setStrokeColor(colors["accent"])
    canvas.setLineWidth(1.25 * mm)
    canvas.drawPath(route)
    metric_box = elements["metrics"]
    metrics = _metric_values(activity, project)
    for index, (value, label) in enumerate(metrics):
        left = metric_box["x"] + index * metric_box["width"] / len(metrics)
        right = metric_box["x"] + (index + 1) * metric_box["width"] / len(metrics)
        if index:
            canvas.setStrokeColor(colors["guide"])
            canvas.setLineWidth(0.25 * mm)
            canvas.line(left * mm, y(metric_box["y"] - 12), left * mm, y(metric_box["y"] + 10))
        center = (left + right) / 2
        canvas.setFillColor(colors["ink"])
        canvas.setFont("Helvetica", 8.5)
        canvas.drawCentredString(center * mm, y(metric_box["y"]), value)
        canvas.setFillColor(colors["muted"])
        canvas.setFont("Helvetica", 4)
        canvas.drawCentredString(center * mm, y(metric_box["y"] + 7), label)
    canvas.setStrokeColor(colors["guide"])
    canvas.line(15 * mm, y(272), 195 * mm, y(272))
    footer = elements["footer"]
    canvas.setFillColor(colors["muted"])
    canvas.setFont("Helvetica", footer["size"])
    canvas.drawString(
        footer["x"] * mm, y(footer["y"]), project.description or "GPX PRINT / LOCAL EDITION"
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
