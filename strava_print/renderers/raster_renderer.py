"""High-resolution printable raster renderer."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from strava_print.domain.models import Activity, Project
from strava_print.gpx.geometry import fit_route_to_circle, normalized_route
from strava_print.layouts.photo import prepare_photo
from strava_print.layouts.presentation import metric_values
from strava_print.layouts.templates import Template
from strava_print.layouts.themes import THEMES

PX_PER_MM_300 = 300 / 25.4


def font(size_mm: float, dpi: int = 300, condensed: bool = False) -> ImageFont.ImageFont:
    candidates = (
        ("C:/Windows/Fonts/bahnschrift.ttf", "DejaVuSansCondensed.ttf", "DejaVuSans.ttf")
        if condensed
        else ("DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf")
    )
    for path in candidates:
        try:
            return ImageFont.truetype(path, max(10, round(size_mm * dpi / 25.4)))
        except OSError:
            continue
    return ImageFont.load_default()


def route_coordinates(
    activity: Activity, project: Project, map_box: dict[str, float], scale: float
) -> list[tuple[int, int]]:
    route = normalized_route(
        activity.points,
        map_box["width"],
        map_box["height"],
        4,
        float(project.route_2d.get("rotation", 0)),
    )
    if map_box.get("shape") == "circle":
        route = fit_route_to_circle(route, min(map_box["width"], map_box["height"]))
    return [
        (
            round((map_box["x"] + x) * scale),
            round((map_box["y"] + map_box["height"] - y) * scale),
        )
        for x, y in route
    ]


def render_image(
    activity: Activity, project: Project, template: Template, dpi: int = 300
) -> Image.Image:
    scale = dpi / 25.4
    colors = {**THEMES["Gallery Edition"], **project.theme}
    image = Image.new(
        "RGB",
        (round(template.width_mm * scale), round(template.height_mm * scale)),
        colors["background"],
    )
    draw = ImageDraw.Draw(image)
    elements = template.elements

    def box(item: dict[str, float]) -> tuple[int, int, int, int]:
        return (
            round(item["x"] * scale),
            round(item["y"] * scale),
            round((item["x"] + item["width"]) * scale),
            round((item["y"] + item["height"]) * scale),
        )

    if elements.get("photo") and project.photo.path:
        photo = elements["photo"]
        target = (round(photo["width"] * scale), round(photo["height"] * scale))
        prepared = prepare_photo(project.photo.path, target, project.photo)
        image.paste(prepared, (round(photo["x"] * scale), round(photo["y"] * scale)))
        draw = ImageDraw.Draw(image)

    map_box = elements["map"]
    coordinates = route_coordinates(activity, project, map_box, scale)
    if map_box.get("shape") == "circle":
        draw.ellipse(
            box(map_box),
            fill=colors["map_fill"],
            outline=colors["guide"],
            width=max(1, round(0.35 * scale)),
        )
    else:
        draw.rectangle(box(map_box), outline=colors["guide"], width=max(1, round(0.35 * scale)))
    draw.line(
        coordinates,
        fill=colors["accent"],
        width=max(2, round(1.15 * scale)),
        joint="curve",
    )
    marker_radius = max(4, round(1.5 * scale))
    for point, fill in (
        (coordinates[0], colors["background"]),
        (coordinates[-1], colors["accent"]),
    ):
        draw.ellipse(
            (
                point[0] - marker_radius,
                point[1] - marker_radius,
                point[0] + marker_radius,
                point[1] + marker_radius,
            ),
            fill=fill,
            outline=colors["accent"],
            width=max(2, round(0.45 * scale)),
        )

    eyebrow = elements.get("eyebrow")
    if eyebrow:
        draw.text(
            (eyebrow["x"] * scale, eyebrow["y"] * scale),
            f"{project.activity_type.upper()} / PERSONAL TERRAIN EDITION",
            font=font(eyebrow["size"], dpi, condensed=True),
            fill=colors["accent"],
            anchor="ms",
        )
    title = elements["title"]
    draw.text(
        (title["x"] * scale, title["y"] * scale),
        (project.title or "Untitled activity").upper(),
        font=font(title["size"], dpi, condensed=True),
        fill=colors["ink"],
        anchor="ms" if title.get("align") == "center" else "ls",
    )
    meta = elements["meta"]
    meta_text = " / ".join(
        value.upper() for value in (project.date, project.location, project.country) if value
    )
    draw.text(
        (meta["x"] * scale, meta["y"] * scale),
        meta_text,
        font=font(meta["size"], dpi, condensed=True),
        fill=colors["muted"],
        anchor="ms" if meta.get("align") == "center" else "ls",
    )
    if caption := elements.get("map_caption"):
        draw.text(
            (caption["x"] * scale, caption["y"] * scale),
            "CUSTOM GPX / 130 MM / TERRAIN READY",
            font=font(caption["size"], dpi, condensed=True),
            fill=colors["muted"],
            anchor="ms",
        )

    metric_box = elements["metrics"]
    metrics = metric_values(activity, project)
    top_rule = (metric_box["y"] - 18) * scale
    draw.line(
        (15 * scale, top_rule, 195 * scale, top_rule),
        fill=colors["ink"],
        width=max(2, round(0.35 * scale)),
    )
    for index, (value, label) in enumerate(metrics):
        left = metric_box["x"] + index * metric_box["width"] / len(metrics)
        right = metric_box["x"] + (index + 1) * metric_box["width"] / len(metrics)
        if index:
            draw.line(
                (
                    left * scale,
                    (metric_box["y"] - 10) * scale,
                    left * scale,
                    (metric_box["y"] + 10) * scale,
                ),
                fill=colors["guide"],
                width=max(1, round(0.25 * scale)),
            )
        center = (left + right) / 2 * scale
        draw.text(
            (center, metric_box["y"] * scale),
            value,
            font=font(8.0, dpi, condensed=True),
            fill=colors["ink"],
            anchor="ms",
        )
        draw.text(
            (center, (metric_box["y"] + 7) * scale),
            label,
            font=font(3.0, dpi, condensed=True),
            fill=colors["muted"],
            anchor="ms",
        )
    draw.line(
        (15 * scale, 272 * scale, 195 * scale, 272 * scale),
        fill=colors["ink"],
        width=max(1, round(0.25 * scale)),
    )
    footer = elements["footer"]
    draw.text(
        (footer["x"] * scale, footer["y"] * scale),
        project.description.upper() if project.description else "GPX TERRAIN / COLLECTOR EDITION",
        font=font(footer["size"], dpi, condensed=True),
        fill=colors["muted"],
        anchor="ls",
    )
    draw.text(
        (195 * scale, footer["y"] * scale),
        "MADE FROM YOUR RIDE",
        font=font(3.1, dpi, condensed=True),
        fill=colors["accent"],
        anchor="rs",
    )
    return image


def save_raster(path: str | Path, activity: Activity, project: Project, template: Template) -> Path:
    output = Path(path)
    image = render_image(activity, project, template)
    image.save(output, dpi=(300, 300), quality=95)
    return output
