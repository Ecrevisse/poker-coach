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
    villain_range: list[tuple[Card, Card]] | None = None,
    iterations: int = 10_000,
    rng: random.Random | None = None,
) -> float:
    """Hero's win+tie probability vs n_villains uniformly drawn (or sampled from range).

    villain_range: list of allowed 2-card combos for *all* villains (sampled with
    replacement across villains; if None, villains get random hands).
    """
    if not hero:
        raise ValueError("hero cards required")
    if rng is None:
        rng = random.Random()

    hero_t = [c.to_treys() for c in hero]
    board_t = [c.to_treys() for c in board]
    used_initial = set(hero_t + board_t)

    range_t: list[tuple[int, int]] | None = None
    if villain_range is not None:
        range_t = [(a.to_treys(), b.to_treys()) for a, b in villain_range]

    wins = 0
    ties = 0
    for _ in range(iterations):
        used = set(used_initial)
        # Deal villain hands
        villain_hands: list[list[int]] = []
        ok = True
        for _v in range(n_villains):
            if range_t is not None:
                combo = _sample_combo(range_t, used, rng)
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
        # Complete board
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
    return (wins + ties / 2) / iterations


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


def pot_odds(to_call: int, pot: int) -> float:
    denom = pot + to_call
    return to_call / denom if denom else 0.0


def ev_call(equity: float, pot: int, to_call: int) -> float:
    return equity * (pot + to_call) - (1 - equity) * to_call


def ev_fold() -> float:
    return 0.0


def required_equity(to_call: int, pot: int) -> float:
    """Min equity for break-even call."""
    return pot_odds(to_call, pot)
