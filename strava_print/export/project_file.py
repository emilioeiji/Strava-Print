"""Portable JSON project storage."""

from __future__ import annotations

import json
from pathlib import Path

from strava_print.domain.models import Model3DSettings, PhotoSettings, Project


def save_project(path: str | Path, project: Project) -> Path:
    target = Path(path)
    data = project.to_dict()
    if data["photo"].get("path"):
        data["photo"]["path"] = Path(data["photo"]["path"]).name
    if data["model_3d"].get("dem_path"):
        data["model_3d"]["dem_path"] = Path(data["model_3d"]["dem_path"]).name
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def load_project(path: str | Path) -> Project:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["photo"] = PhotoSettings(**data.get("photo", {}))
    data["model_3d"] = Model3DSettings(**data.get("model_3d", {}))
    return Project(**data)
