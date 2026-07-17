"""Non-destructive photo cover crop and adjustments."""

from __future__ import annotations

from PIL import Image, ImageEnhance, ImageOps

from strava_print.domain.models import PhotoSettings


def prepare_photo(path: str, target_px: tuple[int, int], settings: PhotoSettings) -> Image.Image:
    image = Image.open(path).convert("RGB")
    if settings.rotation:
        image = image.rotate(settings.rotation, expand=True, resample=Image.Resampling.BICUBIC)
    if settings.grayscale:
        image = ImageOps.grayscale(image).convert("RGB")
    image = ImageEnhance.Brightness(image).enhance(settings.brightness)
    image = ImageEnhance.Contrast(image).enhance(settings.contrast)
    target_w, target_h = target_px
    scale = max(target_w / image.width, target_h / image.height) * settings.zoom
    image = image.resize(
        (max(1, round(image.width * scale)), max(1, round(image.height * scale))),
        Image.Resampling.LANCZOS,
    )
    x = max(0, min(image.width - target_w, round((image.width - target_w) * settings.x / 100)))
    y = max(0, min(image.height - target_h, round((image.height - target_h) * settings.y / 100)))
    return image.crop((x, y, x + target_w, y + target_h))
