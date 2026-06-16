"""Card recognition (template matching) + numeric OCR (tesseract)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .cards import Card

_MATCH_THRESHOLD = 0.6
_SCALES = (0.85, 0.95, 1.05, 1.15, 1.25, 1.35)


_VALID_CARDS = {f"{r}{s}" for r in "23456789TJQKA" for s in "dhsc"}


class CardRecognizer:
    """Template-match a card crop against 52 known templates.

    Templates are BGR PNGs named like `As.png`, `Td.png` (rank + suit).
    Color is preserved so red (h/d) vs black (s/c) is discriminative.
    """

    def __init__(self, templates_dir: Path) -> None:
        import cv2

        self._cv2 = cv2
        self.templates: dict[str, np.ndarray] = {}
        for f in sorted(Path(templates_dir).glob("*.png")):
            if f.stem not in _VALID_CARDS:
                continue
            img = cv2.imread(str(f), cv2.IMREAD_COLOR)
            if img is None:
                continue
            self.templates[f.stem] = img

    def recognize(self, card_img: np.ndarray) -> Card | None:
        """Match a crop against templates with multi-scale search.

        PokerTH renders cards at a size that depends on window dims and may
        differ from the source PNG. We try multiple template scales and let
        TM_CCOEFF_NORMED slide the crop over the scaled template. Works for
        both full-card crops and partial crops (e.g. only the left strip of
        the obscured hero card in a fanned hand).
        """
        if not self.templates or card_img.size == 0:
            return None
        cv2 = self._cv2
        crop = card_img if card_img.ndim == 3 else cv2.cvtColor(card_img, cv2.COLOR_GRAY2BGR)
        ch, cw = crop.shape[:2]
        best_score = -1.0
        best_name: str | None = None
        for name, tmpl in self.templates.items():
            th, tw = tmpl.shape[:2]
            min_scale = max(cw / tw, ch / th)
            for s in _SCALES:
                if s < min_scale:
                    continue
                t = cv2.resize(tmpl, (int(tw * s) + 1, int(th * s) + 1))
                res = cv2.matchTemplate(t, crop, cv2.TM_CCOEFF_NORMED)
                score = float(res.max())
                if score > best_score:
                    best_score = score
                    best_name = name
        if best_name is None or best_score < _MATCH_THRESHOLD:
            return None
        return Card.from_str(best_name)


class TextOCR:
    """Tesseract wrapper for numeric reads (pot, stacks).

    PokerTH renders chip counts as small (~12px tall) white text on dark green.
    Raw OCR fails on that. We upscale 4x, grayscale, invert (text -> dark on
    light), Otsu threshold, then run tesseract with a digit whitelist.
    """

    @staticmethod
    def read_int(img: np.ndarray) -> int:
        import cv2
        import pytesseract

        if img.size == 0:
            return 0
        big = cv2.resize(img, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY) if big.ndim == 3 else big
        inv = cv2.bitwise_not(gray)
        _, thresh = cv2.threshold(inv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        txt = pytesseract.image_to_string(
            thresh,
            config="--psm 7 -c tessedit_char_whitelist=0123456789$,.",
        )
        digits = "".join(c for c in txt if c.isdigit())
        return int(digits) if digits else 0
