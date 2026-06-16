"""Pixels -> GameState. Uses SeatReader to extract per-seat state from the frame."""

from __future__ import annotations

from .calibration import Calibration, resolve
from .capture import ScreenCapture
from .ocr import CardRecognizer
from .seat_reader import SeatReader
from .state import GameState
from .window import WindowLocator


class StateParser:
    def __init__(
        self,
        calib: Calibration,
        card_rec: CardRecognizer,
        capture: ScreenCapture | None = None,
        window: WindowLocator | None = None,
    ) -> None:
        self.calib = calib
        self.cards = card_rec
        self.capture = capture or ScreenCapture()
        self.window = window or WindowLocator()
        self.reader = SeatReader(calib, card_rec)

    def parse(self) -> GameState:
        bounds = self.window.find()
        resolved = resolve(self.calib, bounds.w, bounds.h)
        frame = self.capture.grab_window(bounds)
        return self.reader.read(frame, resolved)
