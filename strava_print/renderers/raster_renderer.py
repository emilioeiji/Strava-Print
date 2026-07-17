"""Pillow renderer for high-resolution printable PNG and JPG files."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from strava_print.domain.models import Activity, Project
from strava_print.gpx.geometry import normalized_route
from strava_print.layouts.photo import prepare_photo
from strava_print.layouts.templates import Template
from strava_print.layouts.themes import THEMES

PX_PER_MM_300 = 300 / 25.4


def _font(size_mm: float) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", max(10, round(size_mm * PX_PER_MM_300)))
    except OSError:
        return ImageFont.load_default()


def render_image(
    activity: Activity, project: Project, template: Template, dpi: int = 300
) -> Image.Image:
    scale = dpi / 25.4
    colors = {**THEMES["Minimal Light"], **project.theme}
    image = Image.new(
        "RGB",
        (round(template.width_mm * scale), round(template.height_mm * scale)),
        colors["background"],
    )
    draw = ImageDraw.Draw(image)
    e = template.elements

    def box(item: dict[str, float]) -> tuple[int, int, int, int]:
        return tuple(round(item[key] * scale) for key in ("x", "y", "width", "height"))

    if e.get("photo") and project.photo.path:
        photo = e["photo"]
        target = (round(photo["width"] * scale), round(photo["height"] * scale))
        prepared = prepare_photo(project.photo.path, target, project.photo)
        image.paste(prepared, (round(photo["x"] * scale), round(photo["y"] * scale)))
    map_box = e["map"]
    route = normalized_route(
        activity.points,
        map_box["width"],
        map_box["height"],
        4,
        float(project.route_2d.get("rotation", 0)),
    )
    coordinates = [
        (round((map_box["x"] + x) * scale), round((map_box["y"] + map_box["height"] - y) * scale))
        for x, y in route
    ]
    draw.rectangle(box(map_box), outline=colors["guide"], width=max(1, round(0.35 * scale)))
    draw.line(coordinates, fill=colors["accent"], width=max(2, round(0.7 * scale)), joint="curve")
    draw.text(
        (e["title"]["x"] * scale, e["title"]["y"] * scale),
        project.title or "Untitled activity",
        font=_font(e["title"]["size"]),
        fill=colors["ink"],
        anchor="ls",
    )
    meta = " · ".join(value for value in [project.date, project.location, project.country] if value)
    draw.text(
        (e["meta"]["x"] * scale, e["meta"]["y"] * scale),
        meta,
        font=_font(e["meta"]["size"]),
        fill=colors["muted"],
        anchor="ls",
    )
    return image


def save_raster(path: str | Path, activity: Activity, project: Project, template: Template) -> Path:
    output = Path(path)
    image = render_image(activity, project, template)
    image.save(output, dpi=(300, 300), quality=95)
    return output
