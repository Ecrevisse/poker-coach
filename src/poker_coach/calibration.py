"""ROI calibration: window-relative coordinates that scale with window size.

JSON schema:
{
  "reference_size": {"w": 1280, "h": 720},
  "hero_cards": [{"x": ..., "y": ..., "w": ..., "h": ...}, ...],
  "board": [...],
  "pot": {...},
  "hero_stack": {...},
  "to_call": {...} | null,
  "villains": [{"seat": 1, "stack": {...}, "position": "BTN"}, ...]
}

ROI x/y are pixel offsets *inside* the PokerTH window, measured at the
reference size. At runtime they scale linearly with current window dims.
w/h stay fixed: card sprites and digit fonts do not resize with the window.
"""

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

    def scale_position(self, sx: float, sy: float) -> ROI:
        """Scale x,y by window ratios; keep w,h fixed."""
        return ROI(x=int(self.x * sx), y=int(self.y * sy), w=self.w, h=self.h)

    def translate(self, dx: int, dy: int) -> ROI:
        return ROI(x=self.x + dx, y=self.y + dy, w=self.w, h=self.h)


@dataclass(frozen=True)
class WindowSize:
    w: int
    h: int


@dataclass
class Calibration:
    reference_size: WindowSize
    hero_cards: list[ROI]
    board: list[ROI]
    pot: ROI
    hero_stack: ROI
    to_call: ROI | None
    villains: list[dict[str, Any]]
    raw: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> Calibration:
        data = json.loads(Path(path).read_text())
        ref = data.get("reference_size") or {"w": 1920, "h": 1080}
        return cls(
            reference_size=WindowSize(w=ref["w"], h=ref["h"]),
            hero_cards=[ROI.from_dict(r) for r in data["hero_cards"]],
            board=[ROI.from_dict(r) for r in data["board"]],
            pot=ROI.from_dict(data["pot"]),
            hero_stack=ROI.from_dict(data["hero_stack"]),
            to_call=ROI.from_dict(data["to_call"]) if data.get("to_call") else None,
            villains=data.get("villains", []),
            raw=data,
        )

    def resolved(self, current_w: int, current_h: int, win_x: int = 0, win_y: int = 0) -> Calibration:
        """Return a new Calibration with ROIs scaled to current window + translated to absolute monitor coords."""
        sx = current_w / self.reference_size.w
        sy = current_h / self.reference_size.h

        def adj(r: ROI) -> ROI:
            return r.scale_position(sx, sy).translate(win_x, win_y)

        villains_resolved: list[dict[str, Any]] = []
        for v in self.villains:
            v2 = dict(v)
            v2["stack"] = {
                "x": int(v["stack"]["x"] * sx) + win_x,
                "y": int(v["stack"]["y"] * sy) + win_y,
                "w": v["stack"]["w"],
                "h": v["stack"]["h"],
            }
            villains_resolved.append(v2)

        return Calibration(
            reference_size=self.reference_size,
            hero_cards=[adj(r) for r in self.hero_cards],
            board=[adj(r) for r in self.board],
            pot=adj(self.pot),
            hero_stack=adj(self.hero_stack),
            to_call=adj(self.to_call) if self.to_call else None,
            villains=villains_resolved,
            raw=self.raw,
        )
