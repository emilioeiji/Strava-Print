"""Basic FDM mesh validation messages."""

from __future__ import annotations

import trimesh


def validate_mesh(mesh: trimesh.Trimesh, min_feature_mm: float = 0.4) -> list[str]:
    warnings: list[str] = []
    if mesh.is_empty:
        warnings.append("Malha vazia.")
    if not mesh.is_watertight:
        warnings.append("Malha não é estanque (watertight).")
    if min(mesh.extents) < min_feature_mm:
        warnings.append("Há uma dimensão menor que o limite FDM configurado.")
    return warnings
