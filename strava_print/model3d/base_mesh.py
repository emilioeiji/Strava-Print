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
