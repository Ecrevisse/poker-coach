"""Calibration: seat-rect + layout resolution."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from poker_coach.calibration import (
    ROI,
    AnchoredROI,
    Calibration,
    Offset,
    resolve,
)


def test_anchored_roi_resolves() -> None:
    r = AnchoredROI(dx=-100, dy=400, w=53, h=80)
    assert r.resolve(window_w=1000) == ROI(x=400, y=400, w=53, h=80)


def test_offset_resolves_against_parent() -> None:
    parent = ROI(x=500, y=600, w=200, h=120)
    o = Offset(dx=10, dy=20, w=40, h=70)
    assert o.resolve(parent) == ROI(x=510, y=620, w=40, h=70)


@pytest.fixture
def calib_data() -> dict:
    layout = {
        "stack":        {"dx": 60, "dy": 110, "w": 84, "h": 12},
        "current_bet":  {"dx": 60, "dy": 80,  "w": 60, "h": 14},
        "cards":        [
            {"dx": 5,  "dy": 10, "w": 26, "h": 76},
            {"dx": 30, "dy": 10, "w": 48, "h": 76},
        ],
        "action_label": {"dx": 50, "dy": 50, "w": 80, "h": 18},
        "chip_marker":  {"dx": 100, "dy": 30, "w": 25, "h": 25},
    }
    return {
        "reference_size": {"w": 1090, "h": 962},
        "layout_bottom": layout,
        "layout_top": layout,  # same for simplicity
        "seats": [
            {"name": "hero", "layout": "bottom",
             "rect": {"anchor": "window_center", "dx": -100, "dy": 600, "w": 200, "h": 130}},
            {"name": "v0", "layout": "bottom",
             "rect": {"anchor": "window_center", "dx": -300, "dy": 600, "w": 200, "h": 130}},
            {"name": "v3", "layout": "top",
             "rect": {"anchor": "window_center", "dx": 0,    "dy": 30,  "w": 200, "h": 130}},
        ],
        "board": [
            {"anchor": "window_center", "dx": -130, "dy": 348, "w": 53, "h": 80},
        ],
        "pot": {"anchor": "window_center", "dx": -200, "dy": 378, "w": 72, "h": 14},
        "templates": {
            "card_back": "x.png",
            "chip_dealer": "d.png",
            "chip_sb": "sb.png",
            "chip_bb": "bb.png",
        },
    }


@pytest.fixture
def calib_file(tmp_path: Path, calib_data: dict) -> Path:
    p = tmp_path / "c.json"
    p.write_text(json.dumps(calib_data))
    return p


def test_loads_two_layouts(calib_file: Path) -> None:
    c = Calibration.load(calib_file)
    assert "bottom" in c.layouts
    assert "top" in c.layouts


def test_resolve_seats_apply_layout(calib_file: Path) -> None:
    c = Calibration.load(calib_file)
    r = resolve(c, window_w=1200, window_h=962)
    hero = r.hero
    # window_center=600, hero rect dx=-100 -> x=500, dy=600 -> y=600
    assert hero.rect == ROI(x=500, y=600, w=200, h=130)
    # stack offset (60, 110) inside hero rect
    assert hero.stack == ROI(x=560, y=710, w=84, h=12)
    # cards[0] offset (5, 10)
    assert hero.cards[0] == ROI(x=505, y=610, w=26, h=76)
    # chip_marker offset (100, 30)
    assert hero.chip_marker == ROI(x=600, y=630, w=25, h=25)


def test_resize_shifts_all_seats_by_half_width(calib_file: Path) -> None:
    c = Calibration.load(calib_file)
    r1 = resolve(c, 1090, 962)
    r2 = resolve(c, 1500, 962)
    diff = (1500 - 1090) // 2
    assert r2.hero.rect.x - r1.hero.rect.x == diff
    assert r2.hero.stack.x - r1.hero.stack.x == diff
    assert r2.hero.cards[0].x - r1.hero.cards[0].x == diff
    assert r2.board[0].x - r1.board[0].x == diff
    # y unchanged
    assert r1.hero.rect.y == r2.hero.rect.y
    assert r1.hero.stack.y == r2.hero.stack.y


def test_by_name_lookup(calib_file: Path) -> None:
    c = Calibration.load(calib_file)
    r = resolve(c, 1200, 962)
    # window_center 600, v0 dx -300 -> x=300, w=200, h=130
    assert r.by_name("v0").rect == ROI(x=300, y=600, w=200, h=130)
    assert r.by_name("v3").layout == "top"
