"""Mounted preview that communicates material, relief and physical depth."""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFilter, ImageOps

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
    texture = ImageOps.colorize(grayscale, black="#292624", white=material).convert("RGBA")
    normalized = (source - source.min()) / max(float(source.max() - source.min()), 1e-9)
    contour_fraction = np.mod(normalized * 11, 1)
    contour_alpha = np.where(contour_fraction < 0.045, 58, 0).astype(np.uint8)
    contours = Image.new("RGBA", grayscale.size, (20, 18, 16, 0))
    contours.putalpha(Image.fromarray(contour_alpha))
    texture = Image.alpha_composite(texture, contours).convert("RGB")
    return texture.resize(size, Image.Resampling.LANCZOS)


def render_mounted_preview(
    activity: Activity, project: Project, template: Template, dpi: int = 150
) -> Image.Image:
    """Render a presentation preview; print exports remain dimensionally clean."""
    colors = {**THEMES["Gallery Edition"], **project.theme}
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
        fill=colors["accent"],
        width=max(3, round(1.75 * scale)),
        joint="curve",
    )
    accent_rgb = ImageColor.getrgb(colors["accent"])
    highlight = tuple(round(channel * 0.65 + 255 * 0.35) for channel in accent_rgb)
    draw.line(
        coordinates,
        fill=highlight,
        width=max(1, round(0.38 * scale)),
        joint="curve",
    )
    return image.convert("RGB")


def render_framed_preview(
    activity: Activity, project: Project, template: Template, width: int = 1280
) -> Image.Image:
    """Place the full mounted poster in a restrained gallery-frame mockup."""
    height = round(width * 0.64)
    wall = Image.new("RGB", (width, height), "#d8d4cc")
    wall_draw = ImageDraw.Draw(wall)
    wall_draw.rectangle((0, round(height * 0.76), width, height), fill="#cbc5ba")
    poster = render_mounted_preview(activity, project, template, dpi=110)
    target_height = round(height * 0.82)
    target_width = round(target_height * template.width_mm / template.height_mm)
    poster = poster.resize((target_width, target_height), Image.Resampling.LANCZOS)
    frame = max(12, round(width * 0.014))
    mat = max(7, round(width * 0.006))
    outer_width = target_width + 2 * (frame + mat)
    outer_height = target_height + 2 * (frame + mat)
    left = (width - outer_width) // 2
    top = (height - outer_height) // 2 - round(height * 0.015)
    shadow = Image.new("RGBA", wall.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rectangle(
        (left + 18, top + 22, left + outer_width + 18, top + outer_height + 22),
        fill=(25, 25, 23, 115),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(12, round(width * 0.018))))
    wall = Image.alpha_composite(wall.convert("RGBA"), shadow).convert("RGB")
    draw = ImageDraw.Draw(wall)
    draw.rectangle((left, top, left + outer_width, top + outer_height), fill="#151718")
    inner = frame
    draw.rectangle(
        (left + inner, top + inner, left + outer_width - inner, top + outer_height - inner),
        fill="#f3f0e9",
    )
    paste_x = left + frame + mat
    paste_y = top + frame + mat
    wall.paste(poster, (paste_x, paste_y))
    draw = ImageDraw.Draw(wall)
    draw.line(
        (left + frame, top + frame, left + outer_width - frame, top + frame),
        fill="#55595a",
        width=2,
    )
    return wall
