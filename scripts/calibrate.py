"""Interactive ROI calibration for PokerTH.

Usage:
    uv run python scripts/calibrate.py --out calibration/pokerth.json

Captures the current PokerTH window via grim, opens a matplotlib window,
and prompts you to draw each ROI in sequence using a rubber-band selector.
Press ENTER to confirm a rectangle, BACKSPACE to redo, ESC to skip optional.
Writes calibration JSON with window-relative coords + reference_size.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from poker_coach.capture import ScreenCapture  # noqa: E402
from poker_coach.window import WindowLocator  # noqa: E402


@dataclass
class Task:
    key: str
    prompt: str
    optional: bool = False


TASKS: list[Task] = [
    Task("hero_cards[0]", "Hero LEFT card"),
    Task("hero_cards[1]", "Hero RIGHT card"),
    Task("board[0]", "Board card 1 (leftmost)"),
    Task("board[1]", "Board card 2"),
    Task("board[2]", "Board card 3"),
    Task("board[3]", "Board card 4 (turn position)"),
    Task("board[4]", "Board card 5 (river position)"),
    Task("pot", "Pot value (text)"),
    Task("hero_stack", "Hero stack (text)"),
    Task("to_call", "Amount to call (text, may be hidden)", optional=True),
]


def prompt_villains() -> int:
    while True:
        try:
            n = int(input("How many villain seats to calibrate? [0-9]: ").strip())
            if 0 <= n <= 9:
                return n
        except ValueError:
            pass
        print("  enter a number 0-9")


def select_roi(img, title: str) -> tuple[int, int, int, int] | None:
    """Show img, let user drag a rectangle, return (x,y,w,h) or None on skip."""
    result: dict = {"box": None}

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    ax.set_title(f"{title}\n[drag rect] ENTER=confirm  BACKSPACE=redo  ESC=skip(optional)")

    def on_select(eclick, erelease):
        x0, y0 = int(eclick.xdata), int(eclick.ydata)
        x1, y1 = int(erelease.xdata), int(erelease.ydata)
        x, y = min(x0, x1), min(y0, y1)
        w, h = abs(x1 - x0), abs(y1 - y0)
        result["box"] = (x, y, w, h)
        print(f"  -> ({x},{y},{w},{h})")

    def on_key(event):
        if event.key == "enter":
            if result["box"] is None:
                print("  draw a rectangle first")
                return
            plt.close(fig)
        elif event.key == "backspace":
            result["box"] = None
            print("  rectangle cleared, draw again")
        elif event.key == "escape":
            result["box"] = "SKIP"
            plt.close(fig)

    selector = RectangleSelector(
        ax, on_select, useblit=True, button=[1], interactive=True,
        minspanx=3, minspany=3, spancoords="pixels",
    )
    _ = selector  # keep ref
    fig.canvas.mpl_connect("key_press_event", on_key)
    plt.show()

    box = result["box"]
    if box == "SKIP" or box is None:
        return None
    return box


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="calibration/pokerth.json")
    ap.add_argument("--match", default="pokerth", help="window-class substring")
    ap.add_argument(
        "--only",
        default="",
        help="comma-separated keys to recalibrate (e.g. 'hero_cards[0],hero_cards[1]'). "
        "Other ROIs kept from existing --out file.",
    )
    args = ap.parse_args()

    print("Locating PokerTH window...")
    bounds = WindowLocator(match=args.match).find()
    print(f"  window: {bounds.w}x{bounds.h} at ({bounds.x},{bounds.y})")

    print("Capturing screenshot...")
    img = ScreenCapture().grab_window(bounds)

    out = Path(args.out)
    existing: dict = {}
    if out.exists():
        existing = json.loads(out.read_text())

    only_keys = {k.strip() for k in args.only.split(",") if k.strip()}

    if only_keys:
        n_villains = len(existing.get("villains", []))
        all_tasks = [t for t in TASKS if t.key in only_keys]
        all_tasks += [
            Task(f"villains[{i}].stack", f"Villain {i} stack (text)")
            for i in range(n_villains)
            if f"villains[{i}].stack" in only_keys
        ]
        if not all_tasks:
            print(f"No matching keys in --only={args.only}")
            return 1
    else:
        n_villains = prompt_villains()
        villain_tasks = [
            Task(f"villains[{i}].stack", f"Villain {i} stack (text)") for i in range(n_villains)
        ]
        all_tasks = TASKS + villain_tasks

    results: dict[str, tuple[int, int, int, int] | None] = {}
    for t in all_tasks:
        print(f"\n{t.key}: {t.prompt}{' (optional, ESC to skip)' if t.optional else ''}")
        box = select_roi(img, f"{t.key}: {t.prompt}")
        results[t.key] = box
        if box is None and not t.optional:
            print(f"  WARN: {t.key} not set (required)")

    def roi(key: str) -> dict | None:
        b = results.get(key)
        if b is None:
            return None
        return {"x": b[0], "y": b[1], "w": b[2], "h": b[3]}

    if only_keys:
        data = dict(existing)
        for key, box in results.items():
            if box is None:
                continue
            r = {"x": box[0], "y": box[1], "w": box[2], "h": box[3]}
            if key == "hero_cards[0]":
                data.setdefault("hero_cards", [None, None])[0] = r
            elif key == "hero_cards[1]":
                data.setdefault("hero_cards", [None, None])[1] = r
            elif key.startswith("board["):
                i = int(key[6:-1])
                board = data.setdefault("board", [None] * 5)
                while len(board) <= i:
                    board.append(None)
                board[i] = r
            elif key.startswith("villains["):
                i = int(key.split("[")[1].split("]")[0])
                for v in data.get("villains", []):
                    if v["seat"] == i:
                        v["stack"] = r
                        break
            else:
                data[key] = r
        data["hero_cards"] = [x for x in data.get("hero_cards", []) if x]
        data["board"] = [x for x in data.get("board", []) if x]
    else:
        data = {
            "reference_size": {"w": bounds.w, "h": bounds.h},
            "hero_cards": [roi("hero_cards[0]"), roi("hero_cards[1]")],
            "board": [roi(f"board[{i}]") for i in range(5)],
            "pot": roi("pot"),
            "hero_stack": roi("hero_stack"),
            "to_call": roi("to_call"),
            "villains": [
                {
                    "seat": i,
                    "stack": roi(f"villains[{i}].stack"),
                    "position": "BTN",
                }
                for i in range(n_villains)
                if roi(f"villains[{i}].stack")
            ],
        }
        data["hero_cards"] = [r for r in data["hero_cards"] if r]
        data["board"] = [r for r in data["board"] if r]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
