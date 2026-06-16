"""Preflop open-ranges per position + notation expander.

Notation supported:
  AA           -> only AA combos
  TT+          -> TT, JJ, QQ, KK, AA
  AKs          -> AK suited
  AKo          -> AK offsuit
  AK           -> AKs + AKo
  A2s+         -> A2s,A3s,...,AKs
  A2o+         -> A2o,A3o,...,AKo
  KTs-K7s      -> KTs,K9s,K8s,K7s (descending)
"""

from __future__ import annotations

from itertools import combinations

from .cards import Card, Position, Rank, Suit, full_deck

_RANK_ORDER = "23456789TJQKA"


def _rank_idx(r: str) -> int:
    return _RANK_ORDER.index(r)


def expand(tokens: set[str]) -> list[tuple[Card, Card]]:
    """Expand a set of poker-notation tokens into concrete 2-card combos."""
    hand_codes: set[str] = set()
    for tok in tokens:
        hand_codes.update(_expand_token(tok))
    combos: list[tuple[Card, Card]] = []
    deck = full_deck()
    for a, b in combinations(deck, 2):
        if _combo_code(a, b) in hand_codes:
            combos.append((a, b))
    return combos


def _combo_code(a: Card, b: Card) -> str:
    hi, lo = (a, b) if a.rank.value_int >= b.rank.value_int else (b, a)
    if hi.rank == lo.rank:
        return hi.rank.value + lo.rank.value
    suited = "s" if hi.suit == lo.suit else "o"
    return hi.rank.value + lo.rank.value + suited


def _expand_token(tok: str) -> set[str]:
    tok = tok.strip()
    # Pair "TT+"
    if len(tok) == 3 and tok[0] == tok[1] and tok.endswith("+"):
        i = _rank_idx(tok[0])
        return {_RANK_ORDER[j] * 2 for j in range(i, 13)}
    # Pair "TT"
    if len(tok) == 2 and tok[0] == tok[1]:
        return {tok}
    # "AKs+", "A2o+" -> walk lower card up to one below high
    if tok.endswith("+") and len(tok) == 4:
        hi, lo, su = tok[0], tok[1], tok[2]
        hi_i, lo_i = _rank_idx(hi), _rank_idx(lo)
        return {hi + _RANK_ORDER[j] + su for j in range(lo_i, hi_i)}
    # "KTs-K7s"
    if "-" in tok:
        a, b = tok.split("-")
        hi = a[0]
        su = a[2]
        top_lo = _rank_idx(a[1])
        bot_lo = _rank_idx(b[1])
        lo_hi, lo_lo = max(top_lo, bot_lo), min(top_lo, bot_lo)
        return {hi + _RANK_ORDER[j] + su for j in range(lo_lo, lo_hi + 1)}
    # "AKs" or "AKo"
    if len(tok) == 3 and tok[2] in ("s", "o"):
        return {tok}
    # "AK" -> AKs + AKo
    if len(tok) == 2:
        return {tok + "s", tok + "o"}
    raise ValueError(f"Unrecognized range token: {tok!r}")


PREFLOP_OPEN_RANGES: dict[Position, set[str]] = {
    Position.UTG: {"22+", "ATs+", "KTs+", "QTs+", "JTs", "T9s", "AJo+", "KQo"},
    Position.MP: {
        "22+", "A9s+", "K9s+", "Q9s+", "J9s", "T8s+", "98s",
        "ATo+", "KJo+", "QJo",
    },
    Position.CO: {
        "22+", "A2s+", "K7s+", "Q8s+", "J8s+", "T8s+", "97s+", "87s", "76s",
        "A9o+", "KTo+", "QTo+", "JTo",
    },
    Position.BTN: {
        "22+", "A2s+", "K2s+", "Q5s+", "J7s+", "T7s+", "96s+", "86s+",
        "75s+", "65s", "54s",
        "A2o+", "K9o+", "Q9o+", "J9o+", "T9o",
    },
    Position.SB: {
        "22+", "A2s+", "K7s+", "Q9s+", "JTs",
        "A8o+", "KTo+", "QTo+", "JTo",
    },
    Position.BB: set(),  # defense modeled separately
}


def open_range(position: Position) -> list[tuple[Card, Card]]:
    return expand(PREFLOP_OPEN_RANGES.get(position, set()))


# Hands that typically 3-bet rather than flat-call. A caller's range should
# exclude these (they would have re-raised instead of calling).
_THREEBET_HANDS = {"JJ", "QQ", "KK", "AA", "AKs", "AKo"}


def cold_call_range(position: Position) -> list[tuple[Card, Card]]:
    """Range a villain calls a raise with (open_range minus 3-betting hands)."""
    combos = expand(PREFLOP_OPEN_RANGES.get(position, set()))
    return [c for c in combos if _combo_code(c[0], c[1]) not in _THREEBET_HANDS]


# Limp range: wide, weak holdings (small/medium pairs, suited connectors,
# suited aces). No premiums (they would raise).
_LIMP_RANGE_TOKENS = {
    "22", "33", "44", "55", "66", "77", "88", "99",
    "A2s", "A3s", "A4s", "A5s", "A6s", "A7s", "A8s", "A9s",
    "T9s", "98s", "87s", "76s", "65s", "54s", "43s",
    "J9s", "JTs", "T8s", "97s", "86s", "75s",
    "QJs", "KJs", "QTs", "KTs",
    "JTo", "QJo", "KJo", "QTo", "KTo", "T9o", "98o", "87o", "76o",
    "A9o", "A8o", "A7o", "A6o", "A5o", "A4o", "A3o", "A2o",
}


def limp_range() -> list[tuple[Card, Card]]:
    return expand(_LIMP_RANGE_TOKENS)


__all__ = [
    "expand", "open_range", "cold_call_range", "limp_range", "PREFLOP_OPEN_RANGES",
]


# Silence unused-import warning while keeping symbols available for callers.
_ = (Suit, Rank)
