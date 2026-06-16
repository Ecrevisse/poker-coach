"""Card recognition (template matching) + numeric OCR (tesseract)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .cards import Card

_MATCH_THRESHOLD = 0.45
_MATCH_MARGIN = 0.03  # best score must beat 2nd best by this much
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

    def recognize_left_half(self, card_img: np.ndarray) -> Card | None:
        """Match a partial crop showing only the LEFT portion of a card.

        For hero_cards[0] in fanned hands. The rank+suit indicator (top-left
        of card) is the most discriminative feature when only a strip of the
        card is visible. We compare the TOP ~40% of the crop against the
        top-left region of each template (sliding to allow small offsets).
        """
        if not self.templates or card_img.size == 0:
            return None
        cv2 = self._cv2
        crop = card_img if card_img.ndim == 3 else cv2.cvtColor(card_img, cv2.COLOR_GRAY2BGR)
        ch, cw = crop.shape[:2]
        top = crop[: max(1, int(ch * 0.4)), :]
        tch, tcw = top.shape[:2]
        scores: list[tuple[float, str]] = []
        for name, tmpl in self.templates.items():
            th, tw = tmpl.shape[:2]
            best = -1.0
            for s in _SCALES:
                nw, nh = int(tw * s) + 1, int(th * s) + 1
                if nw < tcw or nh < tch:
                    continue
                ts = cv2.resize(tmpl, (nw, nh))
                # Search top-left region of template (with small margin to allow drift).
                region_h = min(nh, tch + 10)
                region_w = min(nw, tcw + 5)
                region = ts[:region_h, :region_w]
                if region.shape[0] < tch or region.shape[1] < tcw:
                    continue
                res = cv2.matchTemplate(region, top, cv2.TM_CCOEFF_NORMED)
                best = max(best, float(res.max()))
            scores.append((best, name))
        scores.sort(reverse=True)
        if not scores or scores[0][0] < _MATCH_THRESHOLD:
            return None
        # Reduced margin: same-rank-diff-suit (e.g. 5s vs 5c) is acceptable
        # since at this resolution black suits are visually indistinguishable.
        if len(scores) > 1 and scores[0][1][0] != scores[1][1][0]:
            # Different ranks at top -> require margin
            if scores[0][0] - scores[1][0] < _MATCH_MARGIN:
                return None
        return Card.from_str(scores[0][1])

    def recognize(self, card_img: np.ndarray) -> Card | None:
        """Match a full-card crop against templates with multi-scale search.

        Tries the crop as-is and shrunken versions (1, 3, and 6 px borders
        removed). Shrinking handles ROIs that include table padding around
        the card edge, which kills TM_CCOEFF_NORMED correlation.
        """
        if not self.templates or card_img.size == 0:
            return None
        cv2 = self._cv2
        full = card_img if card_img.ndim == 3 else cv2.cvtColor(card_img, cv2.COLOR_GRAY2BGR)
        candidates = [full]
        for pad in (3, 6):
            if full.shape[0] > 2 * pad + 10 and full.shape[1] > 2 * pad + 10:
                candidates.append(full[pad:-pad, pad:-pad])

        scores: dict[str, float] = {}
        for crop in candidates:
            ch, cw = crop.shape[:2]
            for name, tmpl in self.templates.items():
                th, tw = tmpl.shape[:2]
                min_scale = max(cw / tw, ch / th)
                best = scores.get(name, -1.0)
                for s in _SCALES:
                    if s < min_scale:
                        continue
                    t = cv2.resize(tmpl, (int(tw * s) + 1, int(th * s) + 1))
                    res = cv2.matchTemplate(t, crop, cv2.TM_CCOEFF_NORMED)
                    best = max(best, float(res.max()))
                scores[name] = best

        ranked = sorted(((v, k) for k, v in scores.items()), reverse=True)
        if not ranked or ranked[0][0] < _MATCH_THRESHOLD:
            return None
        ref_w = next(iter(self.templates.values())).shape[1]
        cw = full.shape[1]
        if cw < 0.7 * ref_w and len(ranked) > 1:
            if ranked[0][0] - ranked[1][0] < _MATCH_MARGIN:
                return None
        return Card.from_str(ranked[0][1])


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
        # Empty area (uniform green felt, no chips/text) -> 0. Tesseract loves
        # to hallucinate digits on near-uniform inputs.
        # Empty green felt has std ~31-35; real text on felt has std ~40+.
        if float(img.std()) < 38.0:
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
