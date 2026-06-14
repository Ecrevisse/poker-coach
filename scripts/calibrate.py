"""Interactive ROI calibration helper.

Usage:
    uv run python scripts/calibrate.py --monitor 1 --out calibration/pokerth_1920x1080.json

Take a screenshot of PokerTH, then for each named region you draw a rectangle
by clicking top-left then bottom-right. ESC saves and exits.

TODO: implement properly with matplotlib selector. This is a stub.
"""

from __future__ import annotations

import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--monitor", type=int, default=1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    print(f"TODO: implement calibration UI. monitor={args.monitor} -> {args.out}")


if __name__ == "__main__":
    main()
