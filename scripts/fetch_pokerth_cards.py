"""Download PokerTH card PNGs from upstream and save with poker-coach names.

Source: https://github.com/pokerth/pokerth (GPL).
Each deck PNG is renamed from `<id>.png` to `<rank><suit>.png` (e.g. `As.png`).
Mapping (verified visually): id // 13 = suit in [d, h, s, c]; id % 13 = rank in 2..A.
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

REPO_RAW = "https://raw.githubusercontent.com/pokerth/pokerth/stable/data/gfx/cards"
DECKS = ["default", "default4c", "default_800x480"]
ASSETS = Path(__file__).resolve().parent.parent / "assets" / "cards" / "pokerth"

SUITS = ["d", "h", "s", "c"]
RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]


def card_name(idx: int) -> str:
    return f"{RANKS[idx % 13]}{SUITS[idx // 13]}"


def fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return
    print(f"  -> {dest.name}")
    urllib.request.urlretrieve(url, dest)


def download_deck(deck: str) -> None:
    print(f"[{deck}]")
    out = ASSETS / deck
    for i in range(52):
        fetch(f"{REPO_RAW}/{deck}/{i}.png", out / f"{card_name(i)}.png")
    for extra in ("flipside.png", "preview.png"):
        try:
            fetch(f"{REPO_RAW}/{deck}/{extra}", out / extra)
        except Exception:
            pass


def main() -> int:
    for d in DECKS:
        download_deck(d)
    print(f"\nDone. Templates in {ASSETS}/<deck>/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
