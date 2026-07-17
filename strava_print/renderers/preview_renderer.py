"""Mounted preview that communicates material, relief and physical depth."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from strava_print.domain.models import Activity, Project
from strava_print.layouts.templates import Template
from strava_print.layouts.themes import THEMES
from strava_print.model3d.terrain import DEMError, read_activity_dem
from strava_print.renderers.raster_renderer import render_image, route_coordinates


def _procedural_relief(size: int = 192) -> np.ndarray:
    axis = np.linspace(-3.2, 3.2, size)
    x, y = np.meshgrid(axis, axis)
    return (
        np.sin(x * 1.7 + np.cos(y * 0.8))
        + np.cos(y * 2.1 - x * 0.35) * 0.7
        + np.sin((x + y) * 3.2) * 0.18
    )


def _material_texture(activity: Activity, project: Project, size: tuple[int, int]) -> Image.Image:
    colors = {**THEMES["Gallery Edition"], **project.theme}
    if project.model_3d.dem_path:
        try:
            grid = read_activity_dem(project.model_3d.dem_path, activity, 192)
            source = grid
        except DEMError:
            source = _procedural_relief()
    else:
        source = _procedural_relief()
    gradient_y, gradient_x = np.gradient(source)
    shade = 0.68 - gradient_x * 0.16 + gradient_y * 0.22
    shade -= shade.min()
    peak = shade.max()
    if peak > 0:
        shade /= peak
    grayscale = Image.fromarray(np.uint8(shade * 255))
    material = colors.get("material", "#72503d")
    texture = ImageOps.colorize(grayscale, black="#292624", white=material)
    return texture.resize(size, Image.Resampling.LANCZOS)


def render_mounted_preview(
    activity: Activity, project: Project, template: Template, dpi: int = 150
) -> Image.Image:
    """Render a presentation preview; print exports remain dimensionally clean."""
    image = render_image(activity, project, template, dpi=dpi).convert("RGBA")
    scale = dpi / 25.4
    map_box = template.elements["map"]
    bounds = tuple(round(map_box[key] * scale) for key in ("x", "y", "width", "height"))
    left, top, width, height = bounds
    ellipse = (left, top, left + width, top + height)
    shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    offset = round(2.2 * scale)
    shadow_draw.ellipse(
        (ellipse[0] + offset, ellipse[1] + offset, ellipse[2] + offset, ellipse[3] + offset),
        fill=(18, 20, 20, 115),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(round(2.8 * scale)))
    image = Image.alpha_composite(image, shadow)
    texture = _material_texture(activity, project, (width, height)).convert("RGBA")
    mask = Image.new("L", (width, height), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, width - 1, height - 1), fill=255)
    image.paste(texture, (left, top), mask)
    draw = ImageDraw.Draw(image)
    draw.ellipse(ellipse, outline=(255, 255, 255, 75), width=max(2, round(0.45 * scale)))
    coordinates = route_coordinates(activity, project, map_box, scale)
    route_shadow = [(x + round(0.65 * scale), y + round(0.8 * scale)) for x, y in coordinates]
    draw.line(
        route_shadow,
        fill=(24, 20, 18, 185),
        width=max(4, round(2.6 * scale)),
        joint="curve",
    )
    draw.line(
        coordinates,
        fill="#ff5a2f",
        width=max(3, round(1.75 * scale)),
        joint="curve",
    )
    draw.line(
        coordinates,
        fill="#ff8a62",
        width=max(1, round(0.38 * scale)),
        joint="curve",
    )
    return image.convert("RGB")
