"""Poker math: Monte Carlo equity, pot odds, expected value."""

from __future__ import annotations

import random

from treys import Card as TC
from treys import Evaluator

from .cards import Card, full_deck

_EVALUATOR = Evaluator()
_DECK_TREYS: list[int] = [TC.new(str(c)) for c in full_deck()]


def equity_monte_carlo(
    hero: list[Card],
    board: list[Card],
    n_villains: int,
    villain_ranges: list[list[tuple[Card, Card]] | None] | None = None,
    iterations: int = 10_000,
    rng: random.Random | None = None,
) -> float:
    """Hero's win+tie probability vs n_villains.

    villain_ranges: per-villain allowed 2-card combos. Each entry may be None
    for "random hand". If `villain_ranges` is None, all villains get random hands.
    Length must equal n_villains when provided.
    """
    if not hero:
        raise ValueError("hero cards required")
    if rng is None:
        rng = random.Random()
    if villain_ranges is not None and len(villain_ranges) != n_villains:
        raise ValueError("villain_ranges length must match n_villains")

    hero_t = [c.to_treys() for c in hero]
    board_t = [c.to_treys() for c in board]
    used_initial = set(hero_t + board_t)

    ranges_t: list[list[tuple[int, int]] | None] | None = None
    if villain_ranges is not None:
        ranges_t = [
            [(a.to_treys(), b.to_treys()) for a, b in r] if r else None
            for r in villain_ranges
        ]

    wins = 0
    ties = 0
    valid = 0
    for _ in range(iterations):
        used = set(used_initial)
        villain_hands: list[list[int]] = []
        ok = True
        for vi in range(n_villains):
            r = ranges_t[vi] if ranges_t is not None else None
            if r is not None:
                combo = _sample_combo(r, used, rng)
                if combo is None:
                    ok = False
                    break
                villain_hands.append(list(combo))
                used.update(combo)
            else:
                avail = [c for c in _DECK_TREYS if c not in used]
                pair = rng.sample(avail, 2)
                villain_hands.append(pair)
                used.update(pair)
        if not ok:
            continue
        valid += 1
        avail = [c for c in _DECK_TREYS if c not in used]
        rng.shuffle(avail)
        sim_board = board_t + avail[: 5 - len(board_t)]
        hero_rank = _EVALUATOR.evaluate(sim_board, hero_t)
        v_ranks = [_EVALUATOR.evaluate(sim_board, vh) for vh in villain_hands]
        best_v = min(v_ranks)
        if hero_rank < best_v:
            wins += 1
        elif hero_rank == best_v:
            ties += 1
    return (wins + ties / 2) / valid if valid else 0.0


def _sample_combo(
    combos: list[tuple[int, int]],
    used: set[int],
    rng: random.Random,
) -> tuple[int, int] | None:
    for _ in range(20):
        a, b = rng.choice(combos)
        if a not in used and b not in used:
            return (a, b)
    return None


def pot_odds(to_call: int, effective_pot: int) -> float:
    """Break-even equity for a call: tc / (effective_pot + tc).

    `effective_pot` should include current-street bets (everything hero is
    actually fighting for), NOT just the swept pot.
    """
    denom = effective_pot + to_call
    return to_call / denom if denom else 0.0


def ev_call(equity: float, effective_pot: int, to_call: int) -> float:
    """EV of calling. Win: take effective_pot net of own contribution = effective_pot.
    Lose: lose to_call."""
    return equity * effective_pot - (1 - equity) * to_call


def ev_fold() -> float:
    return 0.0


def ev_raise(
    equity: float,
    effective_pot: int,
    to_call: int,
    raise_size: int,
    fold_equity: float,
) -> float:
    """EV of raising by `raise_size` extra chips on top of any to_call.

    Outcomes:
      - villains fold (prob `fold_equity`): hero wins current pot.
      - villains call (prob 1 - fold_equity): hero invests to_call + raise_size,
        plays for an effective_pot inflated by 2 * raise_size (hero's + caller's).
        Equity stays the same simplification (no implied odds modelling).
    """
    win_now = fold_equity * effective_pot
    new_pot = effective_pot + 2 * raise_size
    invest = to_call + raise_size
    play_ev = (1 - fold_equity) * (equity * new_pot - (1 - equity) * invest)
    return win_now + play_ev


def required_equity(to_call: int, effective_pot: int) -> float:
    return pot_odds(to_call, effective_pot)
