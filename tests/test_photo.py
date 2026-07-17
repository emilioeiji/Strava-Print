from pathlib import Path

from PIL import Image

from strava_print.domain.models import PhotoSettings
from strava_print.layouts.photo import prepare_photo


def test_photo_cover_crop_preserves_target_ratio(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    Image.new("RGB", (400, 100), "red").save(source)
    assert prepare_photo(str(source), (100, 200), PhotoSettings()).size == (100, 200)
