"""Card, Rank, Suit, Street, Position, Action primitives."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Suit(StrEnum):
    SPADES = "s"
    HEARTS = "h"
    DIAMONDS = "d"
    CLUBS = "c"


class Rank(StrEnum):
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "T"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"

    @property
    def value_int(self) -> int:
        order = "23456789TJQKA"
        return order.index(self.value) + 2


@dataclass(frozen=True)
class Card:
    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        return f"{self.rank.value}{self.suit.value}"

    @classmethod
    def from_str(cls, s: str) -> Card:
        if len(s) != 2:
            raise ValueError(f"Invalid card string: {s!r}")
        return cls(Rank(s[0].upper()), Suit(s[1].lower()))

    def to_treys(self) -> int:
        from treys import Card as TC

        return TC.new(str(self))


class Street(StrEnum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"

    @classmethod
    def from_board_len(cls, n: int) -> Street:
        return {0: cls.PREFLOP, 3: cls.FLOP, 4: cls.TURN, 5: cls.RIVER}[n]


class Position(StrEnum):
    UTG = "UTG"
    MP = "MP"
    CO = "CO"
    BTN = "BTN"
    SB = "SB"
    BB = "BB"


class Action(StrEnum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALLIN = "allin"


def full_deck() -> list[Card]:
    return [Card(r, s) for r in Rank for s in Suit]
