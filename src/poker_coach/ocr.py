"""Card recognition (template matching) + numeric OCR (tesseract)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from .cards import Card

_MATCH_THRESHOLD = 0.75


class CardRecognizer:
    """Template-match a card crop against 52 known templates.

    Templates are PNGs named like `As.png`, `Td.png` in `templates_dir`.
    """

    def __init__(self, templates_dir: Path) -> None:
        import cv2

        self._cv2 = cv2
        self.templates: dict[str, np.ndarray] = {}
        for f in sorted(Path(templates_dir).glob("*.png")):
            img = cv2.imread(str(f), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            self.templates[f.stem] = img

    def recognize(self, card_img: np.ndarray) -> Card | None:
        if not self.templates:
            return None
        cv2 = self._cv2
        gray = cv2.cvtColor(card_img, cv2.COLOR_BGR2GRAY) if card_img.ndim == 3 else card_img
        best_score = -1.0
        best_name: str | None = None
        for name, tmpl in self.templates.items():
            resized = cv2.resize(tmpl, (gray.shape[1], gray.shape[0]))
            res = cv2.matchTemplate(gray, resized, cv2.TM_CCOEFF_NORMED)
            score = float(res.max())
            if score > best_score:
                best_score = score
                best_name = name
        if best_name is None or best_score < _MATCH_THRESHOLD:
            return None
        return Card.from_str(best_name)


class TextOCR:
    """Tesseract wrapper for numeric reads (pot, stacks)."""

    @staticmethod
    def read_int(img: np.ndarray) -> int:
        import cv2
        import pytesseract

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        txt = pytesseract.image_to_string(
            thresh,
            config="--psm 7 -c tessedit_char_whitelist=0123456789",
        )
        digits = "".join(c for c in txt if c.isdigit())
        return int(digits) if digits else 0
