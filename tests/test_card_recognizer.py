"""Smoke test: each template must recognize itself."""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from poker_coach.cards import Card, Rank, Suit
from poker_coach.ocr import CardRecognizer

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "cards" / "pokerth" / "default_800x480"


@pytest.fixture(scope="module")
def recognizer() -> CardRecognizer:
    if not TEMPLATES.exists():
        pytest.skip("Templates missing: run scripts/fetch_pokerth_cards.py")
    return CardRecognizer(TEMPLATES)


def test_loads_52_templates(recognizer: CardRecognizer) -> None:
    assert len(recognizer.templates) == 52


@pytest.mark.parametrize("rank", list(Rank))
@pytest.mark.parametrize("suit", list(Suit))
def test_template_self_match(recognizer: CardRecognizer, rank: Rank, suit: Suit) -> None:
    card = Card(rank, suit)
    img = cv2.imread(str(TEMPLATES / f"{card}.png"), cv2.IMREAD_COLOR)
    assert img is not None
    assert recognizer.recognize(img) == card
