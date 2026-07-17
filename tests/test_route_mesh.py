import numpy as np

from strava_print.model3d.route_mesh import route_tube


def test_route_tube_filters_matching_heights_with_duplicate_points() -> None:
    points = np.asarray([[0, 0], [4, 3], [4, 3], [10, 3]], dtype=float)
    heights = np.asarray([2, 4, 99, 6], dtype=float)

    mesh = route_tube(points, width_mm=1.8, z_mm=heights)

    assert mesh.is_watertight
    assert len(mesh.vertices) > 0
