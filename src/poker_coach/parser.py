"""Pixels -> GameState."""

from __future__ import annotations

from .calibration import Calibration
from .capture import ScreenCapture
from .cards import Position
from .ocr import CardRecognizer, TextOCR
from .state import GameState, Villain


class StateParser:
    def __init__(
        self,
        calib: Calibration,
        card_rec: CardRecognizer,
        capture: ScreenCapture | None = None,
    ) -> None:
        self.calib = calib
        self.cards = card_rec
        self.capture = capture or ScreenCapture()

    def parse(self) -> GameState:
        frame = self.capture.grab()
        gs = GameState()
        for roi in self.calib.hero_cards:
            c = self.cards.recognize(self.capture.crop(frame, roi))
            if c:
                gs.hero_cards.append(c)
        for roi in self.calib.board:
            c = self.cards.recognize(self.capture.crop(frame, roi))
            if c:
                gs.board.append(c)
        gs.street = gs.derive_street()
        gs.pot = TextOCR.read_int(self.capture.crop(frame, self.calib.pot))
        gs.hero_stack = TextOCR.read_int(self.capture.crop(frame, self.calib.hero_stack))
        if self.calib.to_call:
            gs.to_call = TextOCR.read_int(self.capture.crop(frame, self.calib.to_call))
        for vcfg in self.calib.villains:
            from .calibration import ROI

            stack = TextOCR.read_int(self.capture.crop(frame, ROI.from_dict(vcfg["stack"])))
            gs.villains.append(
                Villain(
                    seat=vcfg["seat"],
                    stack=stack,
                    position=Position(vcfg.get("position", "BTN")),
                )
            )
        return gs
