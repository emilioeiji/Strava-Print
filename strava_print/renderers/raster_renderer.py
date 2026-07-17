"""Pillow renderer for high-resolution printable PNG and JPG files."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

from strava_print.domain.models import Activity, Project
from strava_print.gpx.geometry import fit_route_to_circle, normalized_route
from strava_print.layouts.photo import prepare_photo
from strava_print.layouts.templates import Template
from strava_print.layouts.themes import THEMES
from strava_print.renderers.svg_renderer import _metric_values

PX_PER_MM_300 = 300 / 25.4


def _font(size_mm: float) -> ImageFont.ImageFont:
    for path in ("DejaVuSans.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(path, max(10, round(size_mm * PX_PER_MM_300)))
        except OSError:
            continue
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
    if map_box.get("shape") == "circle":
        route = fit_route_to_circle(route, min(map_box["width"], map_box["height"]))
    coordinates = [
        (round((map_box["x"] + x) * scale), round((map_box["y"] + map_box["height"] - y) * scale))
        for x, y in route
    ]
    if map_box.get("shape") == "circle":
        bounds = box(map_box)
        draw.ellipse(bounds, outline=colors["guide"], width=max(1, round(0.35 * scale)))
        route_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        route_draw = ImageDraw.Draw(route_layer)
        route_draw.line(
            coordinates, fill=colors["accent"], width=max(2, round(1.25 * scale)), joint="curve"
        )
        mask = Image.new("L", image.size, 0)
        ImageDraw.Draw(mask).ellipse(bounds, fill=255)
        route_layer.putalpha(ImageChops.multiply(route_layer.getchannel("A"), mask))
        image = Image.alpha_composite(image.convert("RGBA"), route_layer).convert("RGB")
        draw = ImageDraw.Draw(image)
    else:
        draw.rectangle(box(map_box), outline=colors["guide"], width=max(1, round(0.35 * scale)))
        draw.line(
            coordinates, fill=colors["accent"], width=max(2, round(1.25 * scale)), joint="curve"
        )
    draw.ellipse(
        (
            coordinates[0][0] - 12,
            coordinates[0][1] - 12,
            coordinates[0][0] + 12,
            coordinates[0][1] + 12,
        ),
        outline=colors["accent"],
        width=4,
        fill=colors["background"],
    )
    draw.ellipse(
        (
            coordinates[-1][0] - 12,
            coordinates[-1][1] - 12,
            coordinates[-1][0] + 12,
            coordinates[-1][1] + 12,
        ),
        outline=colors["background"],
        width=4,
        fill=colors["accent"],
    )
    title_anchor = "ms" if e["title"].get("align") == "center" else "ls"
    meta_anchor = "ms" if e["meta"].get("align") == "center" else "ls"
    draw.text(
        (e["title"]["x"] * scale, e["title"]["y"] * scale),
        project.title or "Untitled activity",
        font=_font(e["title"]["size"]),
        fill=colors["ink"],
        anchor=title_anchor,
    )
    meta = " · ".join(value for value in [project.date, project.location, project.country] if value)
    draw.text(
        (e["meta"]["x"] * scale, e["meta"]["y"] * scale),
        meta,
        font=_font(e["meta"]["size"]),
        fill=colors["muted"],
        anchor=meta_anchor,
    )
    metric_box = e["metrics"]
    metrics = _metric_values(activity, project)
    for index, (value, label) in enumerate(metrics):
        x0 = metric_box["x"] + index * metric_box["width"] / len(metrics)
        x1 = metric_box["x"] + (index + 1) * metric_box["width"] / len(metrics)
        if index:
            draw.line(
                (
                    round(x0 * scale),
                    round((metric_box["y"] - 12) * scale),
                    round(x0 * scale),
                    round((metric_box["y"] + 10) * scale),
                ),
                fill=colors["guide"],
                width=2,
            )
        center = round((x0 + x1) / 2 * scale)
        draw.text(
            (center, metric_box["y"] * scale),
            value,
            font=_font(8.5),
            fill=colors["ink"],
            anchor="ms",
        )
        draw.text(
            (center, (metric_box["y"] + 7) * scale),
            label,
            font=_font(3.6),
            fill=colors["muted"],
            anchor="ms",
        )
    draw.line((15 * scale, 272 * scale, 195 * scale, 272 * scale), fill=colors["guide"], width=2)
    return image


def save_raster(path: str | Path, activity: Activity, project: Project, template: Template) -> Path:
    output = Path(path)
    image = render_image(activity, project, template)
    image.save(output, dpi=(300, 300), quality=95)
    return output
