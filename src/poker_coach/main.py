"""Event loop: capture -> parse -> advise -> render."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from rich.console import Console
from rich.live import Live

from .advisor import advise
from .calibration import Calibration
from .capture import ScreenCapture
from .ocr import CardRecognizer
from .parser import StateParser
from .ui import render

console = Console()


def main() -> None:
    ap = argparse.ArgumentParser(prog="poker-coach")
    ap.add_argument(
        "--calibration", "-c",
        default="calibration/pokerth_1920x1080.json",
        help="Path to ROI calibration JSON.",
    )
    ap.add_argument(
        "--templates", "-t",
        default="assets/cards/pokerth/default",
        help="Directory of 52 card template PNGs.",
    )
    ap.add_argument("--monitor", "-m", type=int, default=1)
    ap.add_argument("--interval", type=float, default=0.5)
    ap.add_argument("--iterations", type=int, default=5000)
    args = ap.parse_args()

    calib_path = Path(args.calibration)
    if not calib_path.exists():
        console.print(f"[red]Calibration file missing:[/] {calib_path}")
        console.print("Run scripts/calibrate.py first.")
        return

    calib = Calibration.load(calib_path)
    cards = CardRecognizer(Path(args.templates))
    if not cards.templates:
        console.print(f"[yellow]Warning:[/] no card templates found in {args.templates}")

    capture = ScreenCapture(monitor_idx=args.monitor)
    parser = StateParser(calib, cards, capture)

    last_hash: str | None = None
    with Live(refresh_per_second=4, console=console) as live:
        while True:
            try:
                gs = parser.parse()
                if not gs.hero_cards:
                    time.sleep(args.interval)
                    continue
                h = gs.hash_key()
                if h != last_hash:
                    adv = advise(gs, iterations=args.iterations)
                    live.update(render(gs, adv))
                    last_hash = h
                time.sleep(args.interval)
            except KeyboardInterrupt:
                break
            except Exception as e:  # noqa: BLE001
                console.print(f"[red]Error:[/] {e}")
                time.sleep(1)


if __name__ == "__main__":
    main()
