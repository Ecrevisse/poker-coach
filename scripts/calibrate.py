"""Interactive ROI calibration for PokerTH (seat-rect + layout model).

Three phases:
  1. Window-center ROIs on full screenshot: hero_rect, N villain_rects,
     board[0..4], pot.
  2. After a recapture: layout_bottom offsets drawn inside the hero_rect crop
     (stack, current_bet, cards x2, action_label, chip_marker).
  3. layout_top offsets drawn inside a chosen top-row villain rect crop.

Templates (D/SB/BB pucks + card_back) are pre-bundled in assets/pokerth/templates/.
The output JSON is a self-contained calibration any window size can resolve.

Usage:
    uv run python scripts/calibrate.py
    uv run python scripts/calibrate.py --villains 9 --top-sample v3
    uv run python scripts/calibrate.py --only "seats.v0,layout_bottom.stack"
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
from matplotlib.widgets import RectangleSelector

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from poker_coach.capture import ScreenCapture  # noqa: E402
from poker_coach.window import WindowLocator  # noqa: E402

DEFAULT_TEMPLATES = {
    "card_back":   "assets/pokerth/templates/card_back.png",
    "chip_dealer": "assets/pokerth/templates/dealerPuck.png",
    "chip_sb":     "assets/pokerth/templates/smallblindPuck.png",
    "chip_bb":     "assets/pokerth/templates/bigblindPuck.png",
}


@dataclass
class Task:
    key: str
    prompt: str
    optional: bool = False


def bottom_villains(n: int) -> list[int]:
    """Indices of villains that share layout_bottom (close to hero on each side)."""
    if n == 0:
        return []
    if n <= 4:
        # Pair them around hero: first half on hero's right (v0..), last on hero's left
        half = n // 2
        return list(range(half)) + list(range(n - (n - half), n))[: n - half]
    # 5..9 villains: 2 to hero's right, 2 to hero's left (4 total).
    return [0, 1, n - 2, n - 1]


def select_roi(img, title: str) -> tuple[int, int, int, int] | None:
    result: dict = {"box": None}
    h, w = img.shape[:2]
    fig_w = min(16, max(8, w / 100))
    fig_h = min(12, max(6, h / 100))
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    ax.set_title(f"{title}\n[drag rect] ENTER=confirm  BACKSPACE=redo  ESC=skip(optional)")

    def on_select(eclick, erelease):
        x0, y0 = int(eclick.xdata), int(eclick.ydata)
        x1, y1 = int(erelease.xdata), int(erelease.ydata)
        x, y = min(x0, x1), min(y0, y1)
        ww, hh = abs(x1 - x0), abs(y1 - y0)
        result["box"] = (x, y, ww, hh)
        print(f"  -> ({x},{y},{ww},{hh})")

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
        minspanx=2, minspany=2, spancoords="pixels",
    )
    _ = selector
    fig.canvas.mpl_connect("key_press_event", on_key)
    plt.show()
    box = result["box"]
    if box == "SKIP" or box is None:
        return None
    return box


def to_wc(box: tuple[int, int, int, int], window_w: int) -> dict:
    x, y, w, h = box
    return {"anchor": "window_center", "dx": x - window_w // 2, "dy": y, "w": w, "h": h}


def to_offset(box: tuple[int, int, int, int]) -> dict:
    x, y, w, h = box
    return {"dx": x, "dy": y, "w": w, "h": h}


def collect_phase1(img, n_villains: int) -> dict[str, tuple[int, int, int, int]]:
    """Phase 1: draw all window-center anchored ROIs on full window screenshot."""
    tasks: list[Task] = [Task("hero_rect", "HERO RECTANGLE — full area with hero info")]
    for i in range(n_villains):
        tasks.append(Task(f"seats.v{i}", f"Villain v{i} rectangle"))
    for i in range(5):
        tasks.append(Task(f"board[{i}]", f"Board card {i + 1}"))
    tasks.append(Task("pot", "Pot value (text)"))

    results: dict[str, tuple[int, int, int, int]] = {}
    for t in tasks:
        print(f"\n[window_center] {t.key}: {t.prompt}")
        box = select_roi(img, f"{t.key}: {t.prompt}")
        if box is None and not t.optional:
            print(f"  WARN: required key {t.key} not set")
            continue
        if box is not None:
            results[t.key] = box
    return results


def collect_layout(crop_img, layout_name: str) -> dict[str, tuple[int, int, int, int]]:
    """Phase 2/3: draw layout offsets inside a seat_rect crop."""
    tasks: list[Task] = [
        Task("stack",         "Stack (text, full chips amount)"),
        Task("current_bet",   "Current bet on table (text, may be empty between hands)"),
        Task("cards[0]",      "LEFT card (partially visible — half hidden by right card)"),
        Task("cards[1]",      "RIGHT card (fully visible)"),
        Task("action_label",  "Action label (fold/check/call/raise text)"),
        Task("chip_marker",   "Chip marker position (where D/SB/BB sits when present)"),
    ]
    results: dict[str, tuple[int, int, int, int]] = {}
    for t in tasks:
        print(f"\n[{layout_name}] {t.key}: {t.prompt}")
        box = select_roi(crop_img, f"{t.key} in {layout_name}: {t.prompt}")
        if box is None:
            print(f"  WARN: {t.key} not set")
            continue
        results[t.key] = box
    return results


def recapture_window(match: str, prev_w: int, prev_h: int) -> tuple:
    print("\nPosition PokerTH for hero details (deal a hand, blinds posted). "
          "Press ENTER to recapture...")
    input()
    bounds = WindowLocator(match=match).find()
    img = ScreenCapture().grab_window(bounds)
    if (bounds.w, bounds.h) != (prev_w, prev_h):
        print(f"  window resized {prev_w}x{prev_h} -> {bounds.w}x{bounds.h}")
    return bounds, img


def resolve_rect_for_window(rect_dict: dict, window_w: int) -> tuple[int, int, int, int]:
    """Resolve a window-center anchored ROI dict to (x, y, w, h)."""
    return (
        window_w // 2 + rect_dict["dx"],
        rect_dict["dy"],
        rect_dict["w"],
        rect_dict["h"],
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="calibration/pokerth.json")
    ap.add_argument("--match", default="pokerth")
    ap.add_argument("--villains", type=int, default=9, help="number of villain seats")
    ap.add_argument(
        "--top-sample", default="v3",
        help="which villain seat to crop for layout_top calibration (default v3)",
    )
    ap.add_argument(
        "--only", default="",
        help="Comma-separated window-center keys to recalibrate "
        "(e.g. 'seats.v2,pot,board[0]'). Skips phase 2/3, merges into existing JSON.",
    )
    args = ap.parse_args()

    out = Path(args.out)
    only_keys = {k.strip() for k in args.only.split(",") if k.strip()}

    if only_keys:
        if not out.exists():
            print(f"ERROR: --only requires existing {out}")
            return 1
        existing = json.loads(out.read_text())
        bounds = WindowLocator(match=args.match).find()
        print(f"window: {bounds.w}x{bounds.h}")
        img = ScreenCapture().grab_window(bounds)
        results: dict[str, tuple[int, int, int, int]] = {}
        for key in only_keys:
            print(f"\n[window_center] {key}")
            box = select_roi(img, key)
            if box is None:
                print(f"  WARN: {key} skipped")
                continue
            results[key] = box
        # Merge into existing JSON, preserving sizes for seats (normalize to layout proto).
        proto_dims: dict[str, tuple[int, int]] = {}
        for s in existing["seats"]:
            if s["layout"] not in proto_dims:
                proto_dims[s["layout"]] = (s["rect"]["w"], s["rect"]["h"])
        for key, box in results.items():
            x, y, w, h = box
            entry = {"anchor": "window_center", "dx": x - bounds.w // 2, "dy": y, "w": w, "h": h}
            if key.startswith("seats.v") or key == "seats.hero" or key == "hero_rect":
                name = "hero" if key in ("seats.hero", "hero_rect") else key.split(".")[1]
                found = False
                for s in existing["seats"]:
                    if s["name"] == name:
                        pw, ph = proto_dims.get(s["layout"], (w, h))
                        entry["w"], entry["h"] = pw, ph
                        s["rect"] = entry
                        found = True
                        break
                if not found:
                    print(f"  WARN: seat {name} not in existing JSON")
            elif key.startswith("board["):
                i = int(key[6:-1])
                board = existing.setdefault("board", [])
                while len(board) <= i:
                    board.append(None)
                board[i] = entry
            elif key == "pot":
                existing["pot"] = entry
            else:
                print(f"  WARN: unknown key {key}, ignored")
        existing["board"] = [b for b in existing.get("board", []) if b]
        out.write_text(json.dumps(existing, indent=2))
        print(f"\nUpdated {out}")
        return 0

    print("Locating PokerTH window...")
    bounds = WindowLocator(match=args.match).find()
    print(f"  window: {bounds.w}x{bounds.h} at ({bounds.x},{bounds.y})")

    print("Capturing screenshot...")
    img = ScreenCapture().grab_window(bounds)

    # --- Phase 1: window-center anchored ---
    print(f"\n=== Phase 1: {args.villains} villain seats + board + pot ===")
    wc_results = collect_phase1(img, args.villains)

    if "hero_rect" not in wc_results:
        print("ERROR: hero_rect is required.")
        return 1
    top_key = f"seats.{args.top_sample}"
    if top_key not in wc_results:
        print(f"ERROR: --top-sample {args.top_sample} rect not calibrated.")
        return 1

    # --- Recapture for inner layout phases ---
    bounds2, img2 = recapture_window(args.match, bounds.w, bounds.h)
    # Re-resolve seat rect positions for the new window width.
    hero_dict = to_wc(wc_results["hero_rect"], bounds.w)
    top_dict = to_wc(wc_results[top_key], bounds.w)
    hrx, hry, hrw, hrh = resolve_rect_for_window(hero_dict, bounds2.w)
    tx, ty, tw, th = resolve_rect_for_window(top_dict, bounds2.w)

    # --- Phase 2: bottom layout (inside hero_rect) ---
    print("\n=== Phase 2: layout_bottom (offsets inside hero_rect) ===")
    hero_crop = img2[hry : hry + hrh, hrx : hrx + hrw]
    bottom_offsets = collect_layout(hero_crop, "layout_bottom")

    # --- Phase 3: top layout (inside top-sample villain rect) ---
    print(f"\n=== Phase 3: layout_top (offsets inside {args.top_sample}_rect) ===")
    top_crop = img2[ty : ty + th, tx : tx + tw]
    top_offsets = collect_layout(top_crop, "layout_top")

    # --- Build JSON ---
    bottom_idx = set(bottom_villains(args.villains))
    top_sample_dict = to_wc(wc_results[top_key], bounds.w)
    # Normalize all seats of a given layout to the prototype's w/h, since the
    # layout offsets only make sense relative to that exact rect size.
    bottom_w, bottom_h = hero_dict["w"], hero_dict["h"]
    top_w, top_h = top_sample_dict["w"], top_sample_dict["h"]

    def _seat_dict(box: tuple[int, int, int, int], layout: str) -> dict:
        x, y, _, _ = box
        if layout == "bottom":
            w, h = bottom_w, bottom_h
        else:
            w, h = top_w, top_h
        return {"anchor": "window_center", "dx": x - bounds.w // 2, "dy": y, "w": w, "h": h}

    seats: list[dict] = [
        {"name": "hero", "layout": "bottom",
         "rect": _seat_dict(wc_results["hero_rect"], "bottom")},
    ]
    for i in range(args.villains):
        key = f"seats.v{i}"
        if key not in wc_results:
            continue
        layout = "bottom" if i in bottom_idx else "top"
        seats.append({
            "name": f"v{i}",
            "layout": layout,
            "rect": _seat_dict(wc_results[key], layout),
        })

    def layout_dict(offsets: dict) -> dict:
        return {
            "stack":        to_offset(offsets["stack"]),
            "current_bet":  to_offset(offsets["current_bet"]),
            "cards":        [to_offset(offsets["cards[0]"]), to_offset(offsets["cards[1]"])],
            "action_label": to_offset(offsets["action_label"]),
            "chip_marker":  to_offset(offsets["chip_marker"]),
        }

    data = {
        "reference_size": {"w": bounds.w, "h": bounds.h},
        "layout_bottom": layout_dict(bottom_offsets),
        "layout_top": layout_dict(top_offsets),
        "seats": seats,
        "board": [
            to_wc(wc_results[f"board[{i}]"], bounds.w)
            for i in range(5) if f"board[{i}]" in wc_results
        ],
        "pot": to_wc(wc_results["pot"], bounds.w),
        "templates": DEFAULT_TEMPLATES,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2))
    print(f"\nWrote {out}")
    print(f"  bottom layout used by: hero, {', '.join('v' + str(i) for i in sorted(bottom_idx))}")
    print(f"  top layout used by: {', '.join('v' + str(i) for i in range(args.villains) if i not in bottom_idx)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
