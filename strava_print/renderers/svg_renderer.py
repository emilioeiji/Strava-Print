"""Editable SVG poster renderer using millimetres as its coordinate system."""

from __future__ import annotations

from base64 import b64encode
from html import escape
from pathlib import Path

from strava_print.domain.models import Activity, Project
from strava_print.domain.units import distance, duration, elevation, pace, speed
from strava_print.gpx.geometry import normalized_route
from strava_print.layouts.templates import Template
from strava_print.layouts.themes import THEMES


def _metric_values(activity: Activity, project: Project) -> list[tuple[str, str]]:
    m, units = activity.metrics, project.units
    values: dict[str, tuple[str, str]] = {}
    d, du = distance(m.distance_m, units)
    values["distance"] = (f"{d:.2f}", du)
    values["moving_time"] = (duration(m.moving_time_s or m.duration_s), "MOVING TIME")
    if m.elevation_gain_m is not None:
        e, eu = elevation(m.elevation_gain_m, units)
        values["elevation_gain"] = (f"{e:.0f}", eu + " GAIN")
    if m.average_speed_mps is not None:
        s, su = speed(m.average_speed_mps, units)
        values["average_speed"] = (f"{s:.1f}", su + " AVG")
    if m.max_speed_mps is not None:
        s, su = speed(m.max_speed_mps, units)
        values["max_speed"] = (f"{s:.1f}", su + " MAX")
    p, pu = pace(m.average_pace_s_per_km, units)
    values["average_pace"] = (p, pu)
    if m.altitude_max_m is not None:
        a, au = elevation(m.altitude_max_m, units)
        values["altitude_max"] = (f"{a:.0f}", au + " MAX")
    return [values[key] for key in project.metrics if key in values][:5]


def render_svg(
    activity: Activity, project: Project, template: Template, guide: str = "outline"
) -> str:
    colors = {**THEMES["Minimal Light"], **project.theme}
    e, map_box = template.elements, template.elements["map"]
    route = normalized_route(
        activity.points,
        map_box["width"],
        map_box["height"],
        4,
        float(project.route_2d.get("rotation", 0)),
    )
    points = " ".join(
        f"{map_box['x'] + x:.3f},{map_box['y'] + map_box['height'] - y:.3f}" for x, y in route
    )
    title = escape(project.title or "Untitled activity")
    meta = escape(
        " · ".join(value for value in [project.date, project.location, project.country] if value)
    )
    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{template.width_mm}mm" height="{template.height_mm}mm" viewBox="0 0 {template.width_mm} {template.height_mm}">',
        f'<rect width="100%" height="100%" fill="{colors["background"]}"/>',
        "<style>text{font-family:DejaVu Sans,Arial,sans-serif} .title{font-weight:700;letter-spacing:0} .label{font-size:5px;fill:#777}</style>",
    ]
    if e.get("photo") and project.photo.path:
        photo = e["photo"]
        photo_data = b64encode(Path(project.photo.path).read_bytes()).decode("ascii")
        chunks.append(
            f'<image href="data:image/jpeg;base64,{photo_data}" x="{photo["x"]}" y="{photo["y"]}" width="{photo["width"]}" height="{photo["height"]}" preserveAspectRatio="xMidYMid slice"/>'
        )
    chunks += [
        f'<text class="title" x="{e["title"]["x"]}" y="{e["title"]["y"]}" font-size="{e["title"]["size"]}" fill="{colors["ink"]}">{title}</text>',
        f'<text x="{e["meta"]["x"]}" y="{e["meta"]["y"]}" font-size="{e["meta"]["size"]}" fill="{colors["muted"]}">{meta}</text>',
    ]
    if guide != "invisible":
        dash = ' stroke-dasharray="2 2"' if guide == "dashed" else ""
        chunks.append(
            f'<rect x="{map_box["x"]}" y="{map_box["y"]}" width="{map_box["width"]}" height="{map_box["height"]}" fill="none" stroke="{colors["guide"]}" stroke-width="0.35"{dash}/>'
        )
    chunks.append(
        f'<polyline points="{points}" fill="none" stroke="{colors["accent"]}" stroke-width="0.7" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    metrics = _metric_values(activity, project)
    metric_box = e["metrics"]
    for index, (value, label) in enumerate(metrics):
        x = metric_box["x"] + index * metric_box["width"] / max(len(metrics), 1)
        chunks.append(
            f'<text x="{x}" y="{metric_box["y"]}" font-size="10" fill="{colors["ink"]}">{escape(value)}</text><text class="label" x="{x}" y="{metric_box["y"] + 7}">{escape(label)}</text>'
        )
    footer = escape(project.description or "GPX PRINT · LOCAL EDITION")
    chunks.append(
        f'<text x="{e["footer"]["x"]}" y="{e["footer"]["y"]}" font-size="{e["footer"]["size"]}" fill="{colors["muted"]}">{footer}</text></svg>'
    )
    return "".join(chunks)


def save_svg(path: str | Path, *args: object) -> Path:
    output = Path(path)
    output.write_text(render_svg(*args), encoding="utf-8")
    return output
