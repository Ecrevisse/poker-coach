"""Pixels -> GameState. Resolves window-relative ROIs to absolute coords each frame."""

from __future__ import annotations

from .calibration import ROI, Calibration
from .capture import ScreenCapture
from .cards import Position
from .ocr import CardRecognizer, TextOCR
from .state import GameState, Villain
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

    def parse(self) -> GameState:
        bounds = self.window.find()
        calib = self.calib.resolved(bounds.w, bounds.h)
        frame = self.capture.grab_window(bounds)
        gs = GameState()
        for roi in calib.hero_cards:
            c = self.cards.recognize(self.capture.crop(frame, roi))
            if c:
                gs.hero_cards.append(c)
        for roi in calib.board:
            c = self.cards.recognize(self.capture.crop(frame, roi))
            if c:
                gs.board.append(c)
        gs.street = gs.derive_street()
        gs.pot = TextOCR.read_int(self.capture.crop(frame, calib.pot))
        gs.hero_stack = TextOCR.read_int(self.capture.crop(frame, calib.hero_stack))
        if calib.to_call:
            gs.to_call = TextOCR.read_int(self.capture.crop(frame, calib.to_call))
        for vcfg in calib.villains:
            stack = TextOCR.read_int(self.capture.crop(frame, ROI.from_dict(vcfg["stack"])))
            gs.villains.append(
                Villain(
                    seat=vcfg["seat"],
                    stack=stack,
                    position=Position(vcfg.get("position", "BTN")),
                )
            )
        return gs
