"""Calibration: ROI scaling + window translation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from poker_coach.calibration import ROI, Calibration


@pytest.fixture
def calib_file(tmp_path: Path) -> Path:
    data = {
        "reference_size": {"w": 1280, "h": 720},
        "hero_cards": [{"x": 100, "y": 200, "w": 60, "h": 90}],
        "board": [{"x": 500, "y": 300, "w": 60, "h": 90}],
        "pot": {"x": 600, "y": 280, "w": 80, "h": 20},
        "hero_stack": {"x": 600, "y": 600, "w": 80, "h": 20},
        "to_call": None,
        "villains": [{"seat": 1, "stack": {"x": 200, "y": 100, "w": 80, "h": 20}, "position": "BTN"}],
    }
    p = tmp_path / "calib.json"
    p.write_text(json.dumps(data))
    return p


def test_loads_reference_size(calib_file: Path) -> None:
    c = Calibration.load(calib_file)
    assert c.reference_size.w == 1280
    assert c.reference_size.h == 720


def test_scale_position_keeps_size_fixed() -> None:
    r = ROI(x=100, y=200, w=60, h=90)
    scaled = r.scale_position(2.0, 1.5)
    assert scaled == ROI(x=200, y=300, w=60, h=90)


def test_resolved_scales_and_translates(calib_file: Path) -> None:
    c = Calibration.load(calib_file)
    # current window 1920x1080 at monitor offset (50, 30)
    r = c.resolved(current_w=1920, current_h=1080, win_x=50, win_y=30)
    assert r.hero_cards[0].x == int(100 * 1920 / 1280) + 50  # 150 + 50 = 200
    assert r.hero_cards[0].y == int(200 * 1080 / 720) + 30   # 300 + 30 = 330
    assert r.hero_cards[0].w == 60  # unchanged
    assert r.hero_cards[0].h == 90


def test_resolved_villain_stack(calib_file: Path) -> None:
    c = Calibration.load(calib_file)
    r = c.resolved(current_w=2560, current_h=1440, win_x=0, win_y=0)
    v = r.villains[0]["stack"]
    assert v["x"] == int(200 * 2560 / 1280)  # 400
    assert v["y"] == int(100 * 1440 / 720)   # 200
    assert v["w"] == 80
    assert v["h"] == 20


def test_resolved_identity_when_same_size(calib_file: Path) -> None:
    c = Calibration.load(calib_file)
    r = c.resolved(current_w=1280, current_h=720, win_x=0, win_y=0)
    assert r.pot == ROI(x=600, y=280, w=80, h=20)
