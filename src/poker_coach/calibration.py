"""Load ROI (region-of-interest) calibration JSON for a given resolution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ROI:
    x: int
    y: int
    w: int
    h: int

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> ROI:
        return cls(x=d["x"], y=d["y"], w=d["w"], h=d["h"])


@dataclass
class Calibration:
    hero_cards: list[ROI]
    board: list[ROI]
    pot: ROI
    hero_stack: ROI
    to_call: ROI | None
    villains: list[dict[str, Any]]  # {"seat": int, "stack": ROI dict, "position": str, ...}
    raw: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> Calibration:
        data = json.loads(Path(path).read_text())
        return cls(
            hero_cards=[ROI.from_dict(r) for r in data["hero_cards"]],
            board=[ROI.from_dict(r) for r in data["board"]],
            pot=ROI.from_dict(data["pot"]),
            hero_stack=ROI.from_dict(data["hero_stack"]),
            to_call=ROI.from_dict(data["to_call"]) if data.get("to_call") else None,
            villains=data.get("villains", []),
            raw=data,
        )
