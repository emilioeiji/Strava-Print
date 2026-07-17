from strava_print.domain.models import TrackPoint
from strava_print.domain.units import distance, elevation, speed
from strava_print.gpx.metrics import calculate_metrics


def test_distance_and_units() -> None:
    metrics = calculate_metrics([TrackPoint(0, 0), TrackPoint(0, 0.01)])
    assert 1000 < metrics.distance_m < 1200
    assert distance(1000, "imperial")[1] == "mi"
    assert elevation(100, "imperial")[1] == "ft"
    assert speed(10, "metric")[0] == 36
