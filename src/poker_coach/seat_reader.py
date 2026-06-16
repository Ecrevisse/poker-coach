"""Read per-seat state from a captured frame.

For each seat: stack OCR, current_bet OCR, cards detection (face-up for hero,
card-back presence for villains), chip_marker template match (D/SB/BB).
Then derives positions clockwise from the dealer button.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .calibration import Calibration, ResolvedCalibration
from .cards import Action, Position
from .ocr import CardRecognizer, TextOCR
from .state import GameState, Villain

_CHIP_THRESHOLD = 0.45
_TEMPLATE_SCALES = (0.75, 0.9, 1.0, 1.15, 1.3)

# Card back detection: pixel std is much higher on pattern than empty green felt
# (cross-hatch teal vs flat green). Combined with hue being teal-ish (~80-90)
# vs pure green (~50-60) gives a robust signal that ignores template alignment.
_CARDBACK_STD_MIN = 38.0
_CARDBACK_HUE_MIN = 70
_CARDBACK_HUE_MAX = 105

# Position ring clockwise from BTN. We only have 6 Position enum values so we
# collapse early-position seats to UTG, late to CO. Generated per active count.
_BASE_RING = (Position.BTN, Position.SB, Position.BB)


def _position_ring(n: int) -> tuple[Position, ...]:
    """Clockwise positions for `n` active seats starting from BTN."""
    if n <= 0:
        return ()
    if n <= 3:
        return _BASE_RING[:n]
    # Slots after BB are distributed: UTG... then MP... then CO (to fill).
    remaining = n - 3
    # Pattern: as we approach BTN going clockwise, we get late positions.
    # Allocate evenly: 1/3 UTG, 1/3 MP, 1/3 CO (rounded).
    n_co = max(1, remaining // 3)
    n_mp = max(1, remaining // 3) if remaining >= 2 else 0
    n_utg = remaining - n_co - n_mp
    return (
        _BASE_RING
        + (Position.UTG,) * n_utg
        + (Position.MP,) * n_mp
        + (Position.CO,) * n_co
    )


def _load_template(path: str) -> tuple[np.ndarray, np.ndarray | None] | None:
    """Returns (BGR image, alpha mask or None)."""
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if img.ndim == 3 and img.shape[2] == 4:
        bgr = img[:, :, :3].copy()
        mask = img[:, :, 3].copy()
        return bgr, mask
    return img, None


def _safe_crop(frame: np.ndarray, roi) -> np.ndarray:
    h, w = frame.shape[:2]
    x = max(0, roi.x)
    y = max(0, roi.y)
    x2 = min(w, roi.x + roi.w)
    y2 = min(h, roi.y + roi.h)
    if x2 <= x or y2 <= y:
        return np.empty((0, 0, 3), dtype=np.uint8)
    return frame[y:y2, x:x2]


def _template_match_score(
    crop: np.ndarray,
    template: tuple[np.ndarray, np.ndarray | None] | None,
) -> float:
    """Multi-scale TM_CCOEFF_NORMED with alpha mask if template has one."""
    if template is None or crop.size == 0:
        return 0.0
    tmpl, mask = template
    ch, cw = crop.shape[:2]
    th, tw = tmpl.shape[:2]
    base_scale = min(cw / tw, ch / th)
    if base_scale < 0.3:
        return 0.0
    best = -1.0
    for s in _TEMPLATE_SCALES:
        scale = base_scale * s
        nw, nh = int(tw * scale), int(th * scale)
        if nw < 8 or nh < 8 or nw > cw or nh > ch:
            continue
        t_resized = cv2.resize(tmpl, (nw, nh))
        m_resized = cv2.resize(mask, (nw, nh)) if mask is not None else None
        if m_resized is not None:
            res = cv2.matchTemplate(crop, t_resized, cv2.TM_CCOEFF_NORMED, mask=m_resized)
        else:
            res = cv2.matchTemplate(crop, t_resized, cv2.TM_CCOEFF_NORMED)
        # matchTemplate with mask can produce inf for areas with zero mask sum
        res_clean = res[np.isfinite(res)]
        if res_clean.size == 0:
            continue
        best = max(best, float(res_clean.max()))
    return best if best > -1.0 else 0.0


class SeatReader:
    def __init__(self, calib: Calibration, card_rec: CardRecognizer) -> None:
        self.calib = calib
        self.cards = card_rec
        self.tpl_card_back = _load_template(calib.templates.get("card_back", ""))
        self.tpl_dealer = _load_template(calib.templates.get("chip_dealer", ""))
        self.tpl_sb = _load_template(calib.templates.get("chip_sb", ""))
        self.tpl_bb = _load_template(calib.templates.get("chip_bb", ""))

    def _chip_role(self, crop: np.ndarray) -> str | None:
        """Returns 'BTN', 'SB', 'BB', or None."""
        scores = {
            "BTN": _template_match_score(crop, self.tpl_dealer),
            "SB":  _template_match_score(crop, self.tpl_sb),
            "BB":  _template_match_score(crop, self.tpl_bb),
        }
        role = max(scores, key=scores.get)
        return role if scores[role] >= _CHIP_THRESHOLD else None

    def _has_cards(self, crop: np.ndarray) -> bool:
        if crop.size == 0:
            return False
        std = float(crop.std())
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        hue_mean = float(hsv[:, :, 0].mean())
        return std >= _CARDBACK_STD_MIN and _CARDBACK_HUE_MIN <= hue_mean <= _CARDBACK_HUE_MAX

    def read(self, frame: np.ndarray, resolved: ResolvedCalibration) -> GameState:
        gs = GameState()

        # Board cards
        for roi in resolved.board:
            c = self.cards.recognize(_safe_crop(frame, roi))
            if c:
                gs.board.append(c)
        gs.street = gs.derive_street()
        gs.pot = TextOCR.read_int(_safe_crop(frame, resolved.pot))

        # Hero
        hero = resolved.hero
        gs.hero_stack = TextOCR.read_int(_safe_crop(frame, hero.stack))
        # Hero cards: cards[0] = partially covered left, cards[1] = right
        if len(hero.cards) >= 1:
            c0 = self.cards.recognize_left_half(_safe_crop(frame, hero.cards[0]))
            if c0:
                gs.hero_cards.append(c0)
        if len(hero.cards) >= 2:
            c1 = self.cards.recognize(_safe_crop(frame, hero.cards[1]))
            if c1:
                gs.hero_cards.append(c1)
        gs.hero_current_bet = TextOCR.read_int(_safe_crop(frame, hero.current_bet))

        # Villains + dealer detection
        roles: dict[str, str] = {}  # seat name -> "BTN"/"SB"/"BB"
        for seat in resolved.seats:
            role = self._chip_role(_safe_crop(frame, seat.chip_marker))
            if role:
                roles[seat.name] = role

        # Derive positions: find BTN seat, assign clockwise.
        # Seat order in calib is assumed clockwise starting from hero.
        ordered_names = [s.name for s in resolved.seats]
        btn_name = next((n for n, r in roles.items() if r == "BTN"), None)
        positions: dict[str, Position] = {}
        if btn_name and btn_name in ordered_names:
            active_seats = [s for s in resolved.seats if s.name == "hero" or self._has_cards(_safe_crop(frame, s.cards[0]))]
            n_active = len(active_seats)
            active_names = [s.name for s in active_seats]
            ring = _position_ring(n_active)
            if btn_name in active_names:
                start = active_names.index(btn_name)
                for i, pos in enumerate(ring):
                    positions[active_names[(start + i) % n_active]] = pos

        gs.hero_position = positions.get("hero", Position.BTN)

        # Now fill villains
        for seat in resolved.seats:
            if seat.name == "hero":
                continue
            in_hand = self._has_cards(_safe_crop(frame, seat.cards[0]))
            stack = TextOCR.read_int(_safe_crop(frame, seat.stack))
            last_bet = TextOCR.read_int(_safe_crop(frame, seat.current_bet))
            pos = positions.get(seat.name, Position.BTN)
            seat_idx = int(seat.name.lstrip("v")) if seat.name.startswith("v") else -1
            gs.villains.append(
                Villain(
                    seat=seat_idx,
                    stack=stack,
                    position=pos,
                    last_bet=last_bet,
                    last_action=Action.FOLD if not in_hand else None,
                    in_hand=in_hand,
                )
            )

        # to_call = max villain bet - hero's own bet on this street
        max_villain_bet = max((v.last_bet for v in gs.villains if v.in_hand), default=0)
        gs.to_call = max(0, max_villain_bet - gs.hero_current_bet)
        return gs
