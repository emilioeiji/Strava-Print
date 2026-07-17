"""Support-free route inserts and matching grooves for terrain models."""

from __future__ import annotations

import numpy as np
import trimesh
from shapely.geometry import LineString, Polygon

from strava_print.model3d.terrain import TerrainData, terrain_mesh


def _footprint(route: np.ndarray, width_mm: float) -> Polygon:
    if width_mm <= 0:
        raise ValueError("A largura do encaixe precisa ser positiva.")
    line = LineString(route).simplify(0.08, preserve_topology=False)
    footprint = line.buffer(width_mm / 2, quad_segs=4, cap_style="round", join_style="round")
    if footprint.is_empty or not isinstance(footprint, Polygon):
        raise ValueError("Nao foi possivel criar uma area continua para a rota.")
    return footprint


def _prism(route: np.ndarray, width_mm: float, floor_mm: float, top_mm: float) -> trimesh.Trimesh:
    prism = trimesh.creation.extrude_polygon(
        _footprint(route, width_mm), height=top_mm - floor_mm, engine="earcut"
    )
    prism.apply_translation((0, 0, floor_mm))
    return prism


def terrain_route_inlay(
    terrain: TerrainData,
    route: np.ndarray,
    diameter_mm: float,
    route_width_mm: float,
    route_height_mm: float,
    clearance_mm: float,
    floor_mm: float,
) -> tuple[trimesh.Trimesh, trimesh.Trimesh, trimesh.Trimesh]:
    """Return the grooved base, assembled insert, and flat-bed printable insert."""
    if not 0 < floor_mm < terrain.base_thickness_mm:
        raise ValueError("O piso do encaixe deve ficar entre 0 e a espessura da base.")
    if not 0 <= clearance_mm <= 0.5:
        raise ValueError("A folga do encaixe deve ficar entre 0 e 0,5 mm por lado.")

    top_mm = terrain.base_thickness_mm + terrain.height_mm + route_height_mm + 1.0
    insert_prism = _prism(route, route_width_mm, floor_mm, top_mm)
    cutter = _prism(route, route_width_mm + clearance_mm * 2, floor_mm, top_mm)
    raised_surface = terrain_mesh(
        terrain.grid,
        diameter_mm,
        terrain.base_thickness_mm + route_height_mm,
        terrain.height_mm,
    ).mesh

    grooved_base = trimesh.boolean.difference([terrain.mesh, cutter], engine="manifold")
    assembled_insert = trimesh.boolean.intersection(
        [insert_prism, raised_surface], engine="manifold"
    )
    if grooved_base is None or assembled_insert is None or assembled_insert.is_empty:
        raise ValueError("Nao foi possivel gerar o encaixe da rota neste relevo.")

    printable_insert = assembled_insert.copy()
    printable_insert.apply_translation((0, 0, -floor_mm))
    return grooved_base, assembled_insert, printable_insert
