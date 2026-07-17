"""Editable SVG poster renderer using millimetres as coordinates."""

from __future__ import annotations

from base64 import b64encode
from html import escape
from pathlib import Path

from strava_print.domain.models import Activity, Project
from strava_print.gpx.geometry import fit_route_to_circle, normalized_route
from strava_print.layouts.presentation import metric_values
from strava_print.layouts.templates import Template
from strava_print.layouts.themes import THEMES


def render_svg(
    activity: Activity, project: Project, template: Template, guide: str = "outline"
) -> str:
    colors = {**THEMES["Gallery Edition"], **project.theme}
    elements = template.elements
    map_box = elements["map"]
    route = normalized_route(
        activity.points,
        map_box["width"],
        map_box["height"],
        4,
        float(project.route_2d.get("rotation", 0)),
    )
    if map_box.get("shape") == "circle":
        route = fit_route_to_circle(route, min(map_box["width"], map_box["height"]))
    route_points = " ".join(
        f"{map_box['x'] + x:.3f},{map_box['y'] + map_box['height'] - y:.3f}" for x, y in route
    )
    chunks = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{template.width_mm}mm" height="{template.height_mm}mm" viewBox="0 0 {template.width_mm} {template.height_mm}">',
        f'<rect width="100%" height="100%" fill="{colors["background"]}"/>',
        "<style>text{font-family:'DejaVu Sans Condensed','Arial Narrow',sans-serif}.title{font-weight:700;letter-spacing:1.8px}.label{font-size:3px;letter-spacing:.3px}</style>",
    ]
    if elements.get("photo") and project.photo.path:
        photo = elements["photo"]
        photo_data = b64encode(Path(project.photo.path).read_bytes()).decode("ascii")
        chunks.append(
            f'<image href="data:image/jpeg;base64,{photo_data}" x="{photo["x"]}" y="{photo["y"]}" width="{photo["width"]}" height="{photo["height"]}" preserveAspectRatio="xMidYMid slice"/>'
        )
    if eyebrow := elements.get("eyebrow"):
        chunks.append(
            f'<text x="{eyebrow["x"]}" y="{eyebrow["y"]}" text-anchor="middle" font-size="{eyebrow["size"]}" letter-spacing=".7" fill="{colors["accent"]}">{escape(project.activity_type.upper())} / PERSONAL TERRAIN EDITION</text>'
        )
    title = elements["title"]
    chunks.append(
        f'<text class="title" x="{title["x"]}" y="{title["y"]}" text-anchor="middle" font-size="{title["size"]}" fill="{colors["ink"]}">{escape((project.title or "Untitled activity").upper())}</text>'
    )
    meta = elements["meta"]
    meta_text = " / ".join(
        value.upper() for value in (project.date, project.location, project.country) if value
    )
    chunks.append(
        f'<text x="{meta["x"]}" y="{meta["y"]}" text-anchor="middle" font-size="{meta["size"]}" letter-spacing=".35" fill="{colors["muted"]}">{escape(meta_text)}</text>'
    )
    is_circle = map_box.get("shape") == "circle"
    center_x = map_box["x"] + map_box["width"] / 2
    center_y = map_box["y"] + map_box["height"] / 2
    radius = min(map_box["width"], map_box["height"]) / 2
    if guide != "invisible":
        dash = ' stroke-dasharray="2 2"' if guide == "dashed" else ""
        if is_circle:
            chunks.append(
                f'<circle cx="{center_x}" cy="{center_y}" r="{radius}" fill="{colors["map_fill"]}" stroke="{colors["guide"]}" stroke-width="0.35"{dash}/>'
            )
        else:
            chunks.append(
                f'<rect x="{map_box["x"]}" y="{map_box["y"]}" width="{map_box["width"]}" height="{map_box["height"]}" fill="none" stroke="{colors["guide"]}" stroke-width="0.35"{dash}/>'
            )
    chunks.append(
        f'<polyline points="{route_points}" fill="none" stroke="{colors["accent"]}" stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round"/>'
    )
    start = (map_box["x"] + route[0, 0], map_box["y"] + map_box["height"] - route[0, 1])
    end = (map_box["x"] + route[-1, 0], map_box["y"] + map_box["height"] - route[-1, 1])
    chunks.extend(
        [
            f'<circle cx="{start[0]}" cy="{start[1]}" r="1.5" fill="{colors["background"]}" stroke="{colors["accent"]}" stroke-width="0.45"/>',
            f'<circle cx="{end[0]}" cy="{end[1]}" r="1.5" fill="{colors["accent"]}" stroke="{colors["background"]}" stroke-width="0.45"/>',
        ]
    )
    if caption := elements.get("map_caption"):
        chunks.append(
            f'<text x="{caption["x"]}" y="{caption["y"]}" text-anchor="middle" font-size="{caption["size"]}" letter-spacing=".45" fill="{colors["muted"]}">CUSTOM GPX / 130 MM / TERRAIN READY</text>'
        )
    metric_box = elements["metrics"]
    metrics = metric_values(activity, project)
    chunks.append(
        f'<line x1="15" y1="{metric_box["y"] - 18}" x2="195" y2="{metric_box["y"] - 18}" stroke="{colors["ink"]}" stroke-width="0.35"/>'
    )
    for index, (value, label) in enumerate(metrics):
        left = metric_box["x"] + index * metric_box["width"] / len(metrics)
        right = metric_box["x"] + (index + 1) * metric_box["width"] / len(metrics)
        center = (left + right) / 2
        if index:
            chunks.append(
                f'<line x1="{left}" y1="{metric_box["y"] - 10}" x2="{left}" y2="{metric_box["y"] + 10}" stroke="{colors["guide"]}" stroke-width="0.25"/>'
            )
        chunks.append(
            f'<text x="{center}" y="{metric_box["y"]}" text-anchor="middle" font-size="8" fill="{colors["ink"]}">{escape(value)}</text><text class="label" x="{center}" y="{metric_box["y"] + 7}" text-anchor="middle" fill="{colors["muted"]}">{escape(label)}</text>'
        )
    footer = elements["footer"]
    footer_text = escape(
        project.description.upper() if project.description else "GPX TERRAIN / COLLECTOR EDITION"
    )
    chunks.extend(
        [
            f'<line x1="15" y1="272" x2="195" y2="272" stroke="{colors["ink"]}" stroke-width="0.25"/>',
            f'<text x="{footer["x"]}" y="{footer["y"]}" font-size="{footer["size"]}" fill="{colors["muted"]}">{footer_text}</text>',
            f'<text x="195" y="{footer["y"]}" text-anchor="end" font-size="3.1" letter-spacing=".4" fill="{colors["accent"]}">MADE FROM YOUR RIDE</text>',
            "</svg>",
        ]
    )
    return "".join(chunks)


def save_svg(path: str | Path, activity: Activity, project: Project, template: Template) -> Path:
    output = Path(path)
    output.write_text(render_svg(activity, project, template), encoding="utf-8")
    return output
