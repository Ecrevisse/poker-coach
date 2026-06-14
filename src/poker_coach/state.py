"""GameState + Villain."""

from __future__ import annotations

from dataclasses import dataclass, field

from .cards import Action, Card, Position, Street


@dataclass
class Villain:
    seat: int
    stack: int = 0
    position: Position = Position.BTN
    last_action: Action | None = None
    last_bet: int = 0
    in_hand: bool = True


@dataclass
class GameState:
    hero_cards: list[Card] = field(default_factory=list)
    board: list[Card] = field(default_factory=list)
    pot: int = 0
    hero_stack: int = 0
    hero_position: Position = Position.BTN
    to_call: int = 0
    big_blind: int = 20
    villains: list[Villain] = field(default_factory=list)
    street: Street = Street.PREFLOP

    @property
    def spr(self) -> float:
        return self.hero_stack / self.pot if self.pot else float("inf")

    @property
    def active_villains(self) -> list[Villain]:
        return [v for v in self.villains if v.in_hand]

    def derive_street(self) -> Street:
        return Street.from_board_len(len(self.board))

    def hash_key(self) -> str:
        h = "".join(str(c) for c in self.hero_cards)
        b = "".join(str(c) for c in self.board)
        return f"{h}|{b}|{self.pot}|{self.to_call}|{self.hero_stack}"
