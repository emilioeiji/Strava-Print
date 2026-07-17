"""Presentation labels shared by print and preview renderers."""

from strava_print.domain.models import Activity, Project
from strava_print.domain.units import distance, duration, elevation, pace, speed


def metric_values(activity: Activity, project: Project) -> list[tuple[str, str]]:
    metrics, units = activity.metrics, project.units
    values: dict[str, tuple[str, str]] = {}
    value, unit = distance(metrics.distance_m, units)
    values["distance"] = (f"{value:.2f}", unit.upper())
    values["moving_time"] = (duration(metrics.moving_time_s or metrics.duration_s), "MOVING TIME")
    if metrics.elevation_gain_m is not None:
        value, unit = elevation(metrics.elevation_gain_m, units)
        values["elevation_gain"] = (f"{value:.0f}", f"{unit.upper()} GAIN")
    if metrics.average_speed_mps is not None:
        value, unit = speed(metrics.average_speed_mps, units)
        values["average_speed"] = (f"{value:.1f}", f"{unit.upper()} AVG")
    if metrics.max_speed_mps is not None:
        value, unit = speed(metrics.max_speed_mps, units)
        values["max_speed"] = (f"{value:.1f}", f"{unit.upper()} MAX")
    value, unit = pace(metrics.average_pace_s_per_km, units)
    values["average_pace"] = (value, unit.upper())
    if metrics.altitude_max_m is not None:
        value, unit = elevation(metrics.altitude_max_m, units)
        values["altitude_max"] = (f"{value:.0f}", f"{unit.upper()} MAX")
    return [values[key] for key in project.metrics if key in values][:5]
