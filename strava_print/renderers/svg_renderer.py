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
        "<style>text{font-family:DejaVu Sans,Arial,sans-serif} .title{font-weight:700;letter-spacing:1.8px} .label{font-size:4px;letter-spacing:.25px;fill:#777}</style>",
    ]
    if e.get("photo") and project.photo.path:
        photo = e["photo"]
        photo_data = b64encode(Path(project.photo.path).read_bytes()).decode("ascii")
        chunks.append(
            f'<image href="data:image/jpeg;base64,{photo_data}" x="{photo["x"]}" y="{photo["y"]}" width="{photo["width"]}" height="{photo["height"]}" preserveAspectRatio="xMidYMid slice"/>'
        )
    chunks += [
        f'<text class="title" x="{e["title"]["x"]}" y="{e["title"]["y"]}" font-size="{e["title"]["size"]}" fill="{colors["ink"]}" text-anchor="{e["title"].get("align", "start")}">{title}</text>',
        f'<text x="{e["meta"]["x"]}" y="{e["meta"]["y"]}" font-size="{e["meta"]["size"]}" fill="{colors["muted"]}" text-anchor="{e["meta"].get("align", "start")}">{meta}</text>',
    ]
    is_circle = map_box.get("shape") == "circle"
    center_x = map_box["x"] + map_box["width"] / 2
    center_y = map_box["y"] + map_box["height"] / 2
    radius = min(map_box["width"], map_box["height"]) / 2
    if is_circle:
        chunks.append(
            f'<defs><clipPath id="route-area"><circle cx="{center_x}" cy="{center_y}" r="{radius}"/></clipPath></defs>'
        )
    if guide != "invisible":
        dash = ' stroke-dasharray="2 2"' if guide == "dashed" else ""
        if is_circle:
            chunks.append(
                f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="none" stroke="{colors["guide"]}" stroke-width="0.35"{dash}/>'
            )
        else:
            chunks.append(
                f'<rect x="{map_box["x"]}" y="{map_box["y"]}" width="{map_box["width"]}" height="{map_box["height"]}" fill="none" stroke="{colors["guide"]}" stroke-width="0.35"{dash}/>'
            )
    clip = ' clip-path="url(#route-area)"' if is_circle else ""
    chunks.append(
        f'<polyline points="{points}" fill="none" stroke="{colors["accent"]}" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round"{clip}/>'
    )
    start_x, start_y = map_box["x"] + route[0, 0], map_box["y"] + map_box["height"] - route[0, 1]
    end_x, end_y = map_box["x"] + route[-1, 0], map_box["y"] + map_box["height"] - route[-1, 1]
    chunks += [
        f'<circle cx="{start_x}" cy="{start_y}" r="2.2" fill="#ffffff" stroke="{colors["accent"]}" stroke-width="0.8"/>',
        f'<circle cx="{end_x}" cy="{end_y}" r="2.2" fill="{colors["accent"]}" stroke="#ffffff" stroke-width="0.8"/>',
    ]
    metrics = _metric_values(activity, project)
    metric_box = e["metrics"]
    for index, (value, label) in enumerate(metrics):
        x = metric_box["x"] + index * metric_box["width"] / max(len(metrics), 1)
        if index:
            chunks.append(
                f'<line x1="{x}" y1="{metric_box["y"] - 12}" x2="{x}" y2="{metric_box["y"] + 10}" stroke="{colors["guide"]}" stroke-width="0.25"/>'
            )
        chunks.append(
            f'<text x="{x + metric_box["width"] / max(len(metrics), 1) / 2}" y="{metric_box["y"]}" text-anchor="middle" font-size="9" fill="{colors["ink"]}">{escape(value)}</text><text class="label" text-anchor="middle" x="{x + metric_box["width"] / max(len(metrics), 1) / 2}" y="{metric_box["y"] + 7}">{escape(label)}</text>'
        )
    footer = escape(project.description or "GPX PRINT · LOCAL EDITION")
    chunks.append(
        f'<line x1="15" y1="272" x2="195" y2="272" stroke="{colors["guide"]}" stroke-width="0.35"/>'
    )
    chunks.append(
        f'<text x="{e["footer"]["x"]}" y="{e["footer"]["y"]}" font-size="{e["footer"]["size"]}" fill="{colors["muted"]}">{footer}</text></svg>'
    )
    return "".join(chunks)


def save_svg(path: str | Path, *args: object) -> Path:
    output = Path(path)
    output.write_text(render_svg(*args), encoding="utf-8")
    return output
