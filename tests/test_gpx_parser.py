from pathlib import Path

from strava_print.gpx.parser import parse_gpx


def test_parse_valid_gpx() -> None:
    activity = parse_gpx(Path("tests/fixtures/sample.gpx"))
    assert len(activity.points) == 4
    assert activity.metrics.distance_m > 100
    assert activity.metrics.elevation_gain_m == 18


def test_gpx_without_optional_data(tmp_path: Path) -> None:
    path = tmp_path / "simple.gpx"
    path.write_text(
        '<?xml version="1.0"?><gpx><trk><trkseg><trkpt lat="1" lon="1"/><trkpt lat="1.01" lon="1.01"/></trkseg></trk></gpx>'
    )
    activity = parse_gpx(path)
    assert activity.metrics.duration_s is None
    assert activity.metrics.altitude_max_m is None
