"""Visual debug of the live capture pipeline (seat-rect model).

Captures the PokerTH window, draws every resolved ROI on it with a label,
saves crops per seat, and prints recognition + OCR results.

Usage:
    uv run python scripts/debug_capture.py
    uv run python scripts/debug_capture.py --open
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from poker_coach.calibration import ROI, Calibration, resolve  # noqa: E402
from poker_coach.capture import ScreenCapture  # noqa: E402
from poker_coach.ocr import CardRecognizer, TextOCR  # noqa: E402
from poker_coach.seat_reader import SeatReader  # noqa: E402
from poker_coach.window import WindowLocator  # noqa: E402

OUT_DIR = Path("/tmp/poker_coach_debug")


def draw_roi(img, roi: ROI, label: str, color=(0, 255, 0), thickness=2) -> None:
    cv2.rectangle(img, (roi.x, roi.y), (roi.x + roi.w, roi.y + roi.h), color, thickness)
    cv2.putText(
        img, label, (roi.x, max(roi.y - 4, 12)),
        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA,
    )


def safe_crop(img, roi: ROI):
    h, w = img.shape[:2]
    x = max(0, roi.x)
    y = max(0, roi.y)
    x2 = min(w, roi.x + roi.w)
    y2 = min(h, roi.y + roi.h)
    if x2 <= x or y2 <= y:
        return None
    return img[y:y2, x:x2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--calibration", default="calibration/pokerth.json")
    ap.add_argument("--templates", default="assets/cards/pokerth/default_800x480")
    ap.add_argument("--open", action="store_true")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for f in OUT_DIR.glob("*"):
        f.unlink()

    bounds = WindowLocator().find()
    calib = Calibration.load(args.calibration)
    print(f"window: {bounds.w}x{bounds.h} at ({bounds.x},{bounds.y})")
    print(f"ref:    {calib.reference_size.w}x{calib.reference_size.h}")

    img = ScreenCapture().grab_window(bounds)
    cv2.imwrite(str(OUT_DIR / "00_raw.png"), img)

    r = resolve(calib, bounds.w, bounds.h)
    cr = CardRecognizer(Path(args.templates))
    reader = SeatReader(calib, cr)
    print(f"templates: {len(cr.templates)} cards | "
          f"pucks D/SB/BB={int(reader.tpl_dealer is not None)}"
          f"/{int(reader.tpl_sb is not None)}/{int(reader.tpl_bb is not None)} | "
          f"card_back={int(reader.tpl_card_back is not None)}")

    annotated = img.copy()

    # Board + pot
    print("\n--- board / pot ---")
    for i, roi in enumerate(r.board):
        crop = safe_crop(img, roi)
        if crop is not None:
            cv2.imwrite(str(OUT_DIR / f"board_{i}.png"), crop)
            card = cr.recognize(crop)
            print(f"  board_{i}: -> {card}")
        draw_roi(annotated, roi, f"board_{i}", (255, 200, 0))
    crop = safe_crop(img, r.pot)
    if crop is not None:
        cv2.imwrite(str(OUT_DIR / "pot.png"), crop)
        print(f"  pot:     -> {TextOCR.read_int(crop)}")
    draw_roi(annotated, r.pot, "pot", (255, 0, 255))

    # Seats
    print("\n--- seats ---")
    for seat in r.seats:
        draw_roi(annotated, seat.rect, seat.name,
                 (0, 255, 0) if seat.name == "hero" else (200, 200, 200), 1)
        prefix = OUT_DIR / seat.name
        for sub_name, sub in [
            ("stack", seat.stack),
            ("current_bet", seat.current_bet),
            ("cards_0", seat.cards[0]),
            ("cards_1", seat.cards[1]) if len(seat.cards) > 1 else (None, None),
            ("action_label", seat.action_label),
            ("chip_marker", seat.chip_marker),
        ]:
            if sub_name is None:
                continue
            crop = safe_crop(img, sub)
            if crop is not None:
                cv2.imwrite(str(prefix.with_name(f"{seat.name}_{sub_name}.png")), crop)
            color = {
                "stack": (255, 0, 255),
                "current_bet": (200, 100, 255),
                "cards_0": (0, 255, 255),
                "cards_1": (0, 255, 255),
                "action_label": (100, 200, 255),
                "chip_marker": (0, 200, 255),
            }[sub_name]
            draw_roi(annotated, sub, "", color, 1)

        def _crop_or_empty(roi):
            c = safe_crop(img, roi)
            return c if c is not None else img[:0, :0]

        stack = TextOCR.read_int(_crop_or_empty(seat.stack))
        bet = TextOCR.read_int(_crop_or_empty(seat.current_bet))
        chip_crop = safe_crop(img, seat.chip_marker)
        role = reader._chip_role(chip_crop) if chip_crop is not None else None
        cards_crop = safe_crop(img, seat.cards[0]) if seat.cards else None
        in_hand = reader._has_cards(cards_crop) if cards_crop is not None else False
        extra = ""
        if seat.name == "hero" and seat.cards:
            c0 = cr.recognize_left_half(_crop_or_empty(seat.cards[0]))
            c1 = cr.recognize(_crop_or_empty(seat.cards[1])) if len(seat.cards) > 1 else None
            extra = f"  cards={c0} {c1}"
        print(f"  {seat.name:6s} [{seat.layout}]  stack={stack:7d}  bet={bet:5d}  "
              f"chip={role or '-':3s}  in_hand={in_hand}{extra}")

    out_annot = OUT_DIR / "annotated.png"
    cv2.imwrite(str(out_annot), annotated)
    print(f"\nWrote {out_annot}")
    if args.open:
        subprocess.Popen(["xdg-open", str(out_annot)])
    return 0


if __name__ == "__main__":
    sys.exit(main())
