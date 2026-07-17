"""Load and validate JSON templates stored outside the Python package."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_DIR = ROOT / "templates"


@dataclass(frozen=True)
class Template:
    name: str
    width_mm: float
    height_mm: float
    elements: dict[str, Any]


def load_template(name: str) -> Template:
    path = TEMPLATE_DIR / f"{name}.json"
    if not path.exists():
        raise ValueError(f"Template não encontrado: {name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not {"name", "page", "elements"} <= data.keys():
        raise ValueError(f"Template inválido: {path.name}")
    page = data["page"]
    return Template(
        data["name"], float(page["width_mm"]), float(page["height_mm"]), data["elements"]
    )


def available_templates() -> list[str]:
    return sorted(path.stem for path in TEMPLATE_DIR.glob("*.json"))
