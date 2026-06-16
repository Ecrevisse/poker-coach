"""ROI calibration with seat-rects + shared layouts.

PokerTH UI: 10 player seats arranged around a centered table. Each seat has
the same fixed-size internal layout — but the table is mirrored: 5 bottom
seats (hero + v0, v1, v7, v8) share `layout_bottom`; 5 top seats (v2..v6)
share `layout_top`.

Calibration stores:
  - reference_size              (window size at calibration time, for context only)
  - layout_bottom, layout_top   (offsets of sub-ROIs inside any seat using that layout)
  - seats[]                     (each: name, layout, rect anchored to window_center)
  - board[5], pot               (anchored to window_center)
  - templates                   (paths to puck + card_back assets)

JSON schema:
{
  "reference_size": {"w": 1090, "h": 962},
  "layout_bottom": {
    "stack":        {"dx": 60, "dy": 110, "w": 84, "h": 12},
    "current_bet":  {"dx": ..., "dy": ..., "w": ..., "h": ...},
    "cards":        [{"dx": ..., "dy": ..., "w": ..., "h": ...}, {...}],
    "action_label": {...},
    "chip_marker":  {...}
  },
  "layout_top": {...same shape...},
  "seats": [
    {"name": "hero", "layout": "bottom",
     "rect": {"anchor": "window_center", "dx": -100, "dy": 600, "w": 200, "h": 130}},
    ...
  ],
  "board": [{"anchor": "window_center", "dx": ..., "dy": ..., "w": ..., "h": ...}, ...],
  "pot":  {"anchor": "window_center", ...},
  "templates": {
    "card_back":   "assets/pokerth/templates/card_back.png",
    "chip_dealer": "assets/pokerth/templates/dealerPuck.png",
    "chip_sb":     "assets/pokerth/templates/smallblindPuck.png",
    "chip_bb":     "assets/pokerth/templates/bigblindPuck.png"
  }
}
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ROI:
    """Resolved ROI in absolute window-relative pixels."""
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class Offset:
    """Sub-ROI offset inside a containing seat_rect."""
    dx: int
    dy: int
    w: int
    h: int

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> Offset:
        return cls(dx=int(d["dx"]), dy=int(d["dy"]), w=int(d["w"]), h=int(d["h"]))

    def resolve(self, parent: ROI) -> ROI:
        return ROI(x=parent.x + self.dx, y=parent.y + self.dy, w=self.w, h=self.h)


@dataclass(frozen=True)
class AnchoredROI:
    """ROI anchored to the window center."""
    dx: int
    dy: int
    w: int
    h: int

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AnchoredROI:
        # Tolerate extra "anchor" key (always "window_center" for now).
        return cls(dx=int(d["dx"]), dy=int(d["dy"]), w=int(d["w"]), h=int(d["h"]))

    def resolve(self, window_w: int) -> ROI:
        return ROI(x=window_w // 2 + self.dx, y=self.dy, w=self.w, h=self.h)


@dataclass(frozen=True)
class Layout:
    """Sub-ROI offsets shared by all seats of the same orientation."""
    stack: Offset
    current_bet: Offset
    cards: list[Offset]
    action_label: Offset
    chip_marker: Offset

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Layout:
        return cls(
            stack=Offset.from_dict(d["stack"]),
            current_bet=Offset.from_dict(d["current_bet"]),
            cards=[Offset.from_dict(c) for c in d["cards"]],
            action_label=Offset.from_dict(d["action_label"]),
            chip_marker=Offset.from_dict(d["chip_marker"]),
        )


@dataclass(frozen=True)
class SeatDef:
    name: str  # "hero", "v0", "v1", ...
    layout: str  # "bottom" | "top"
    rect: AnchoredROI

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SeatDef:
        return cls(name=d["name"], layout=d["layout"], rect=AnchoredROI.from_dict(d["rect"]))


@dataclass(frozen=True)
class WindowSize:
    w: int
    h: int


@dataclass
class Calibration:
    reference_size: WindowSize
    layouts: dict[str, Layout]
    seats: list[SeatDef]
    board: list[AnchoredROI]
    pot: AnchoredROI
    templates: dict[str, str] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> Calibration:
        data = json.loads(Path(path).read_text())
        ref = data.get("reference_size") or {"w": 1090, "h": 962}
        return cls(
            reference_size=WindowSize(w=ref["w"], h=ref["h"]),
            layouts={
                "bottom": Layout.from_dict(data["layout_bottom"]),
                "top": Layout.from_dict(data["layout_top"]),
            },
            seats=[SeatDef.from_dict(s) for s in data["seats"]],
            board=[AnchoredROI.from_dict(b) for b in data["board"]],
            pot=AnchoredROI.from_dict(data["pot"]),
            templates=data.get("templates", {}),
            raw=data,
        )


@dataclass
class ResolvedSeat:
    name: str
    layout: str
    rect: ROI
    stack: ROI
    current_bet: ROI
    cards: list[ROI]
    action_label: ROI
    chip_marker: ROI


@dataclass
class ResolvedCalibration:
    seats: list[ResolvedSeat]
    board: list[ROI]
    pot: ROI

    @property
    def hero(self) -> ResolvedSeat:
        return next(s for s in self.seats if s.name == "hero")

    def by_name(self, name: str) -> ResolvedSeat:
        return next(s for s in self.seats if s.name == name)


def resolve(calib: Calibration, window_w: int, window_h: int) -> ResolvedCalibration:
    """Resolve all ROIs to absolute window-relative pixels."""
    seats: list[ResolvedSeat] = []
    for s in calib.seats:
        rect = s.rect.resolve(window_w)
        lay = calib.layouts[s.layout]
        seats.append(
            ResolvedSeat(
                name=s.name,
                layout=s.layout,
                rect=rect,
                stack=lay.stack.resolve(rect),
                current_bet=lay.current_bet.resolve(rect),
                cards=[c.resolve(rect) for c in lay.cards],
                action_label=lay.action_label.resolve(rect),
                chip_marker=lay.chip_marker.resolve(rect),
            )
        )
    return ResolvedCalibration(
        seats=seats,
        board=[b.resolve(window_w) for b in calib.board],
        pot=calib.pot.resolve(window_w),
    )
