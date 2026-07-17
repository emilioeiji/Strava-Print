"""Simple printable flat-map base."""

from __future__ import annotations

import trimesh


def flat_base(width_mm: float, height_mm: float, thickness_mm: float) -> trimesh.Trimesh:
    return trimesh.creation.box(
        extents=(width_mm, height_mm, thickness_mm),
        transform=trimesh.transformations.translation_matrix(
            (width_mm / 2, height_mm / 2, thickness_mm / 2)
        ),
    )


def round_base(diameter_mm: float, thickness_mm: float) -> trimesh.Trimesh:
    """Create a circular Flat Map base aligned to positive X/Y route coordinates."""
    mesh = trimesh.creation.cylinder(radius=diameter_mm / 2, height=thickness_mm, sections=96)
    mesh.apply_translation((diameter_mm / 2, diameter_mm / 2, thickness_mm / 2))
    return mesh
