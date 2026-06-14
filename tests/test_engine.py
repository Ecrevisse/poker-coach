import random

from poker_coach.cards import Card
from poker_coach.engine import (
    equity_monte_carlo,
    ev_call,
    ev_fold,
    pot_odds,
    required_equity,
)


def _h(s: str) -> list[Card]:
    return [Card.from_str(c) for c in s.split()]


def test_pot_odds():
    assert pot_odds(25, 75) == 0.25
    assert pot_odds(0, 100) == 0.0
    assert pot_odds(50, 0) == 1.0


def test_ev_fold():
    assert ev_fold() == 0.0


def test_ev_call_positive():
    # 60% equity, pot 100, to_call 50 -> 0.6*150 - 0.4*50 = 90 - 20 = 70
    assert ev_call(0.6, 100, 50) == 70.0


def test_required_equity_matches_pot_odds():
    assert required_equity(50, 150) == pot_odds(50, 150)


def test_equity_aa_vs_random_heads_up():
    rng = random.Random(42)
    eq = equity_monte_carlo(_h("As Ah"), [], n_villains=1, iterations=2000, rng=rng)
    assert 0.80 < eq < 0.90


def test_equity_72o_vs_aks_unfavored():
    rng = random.Random(42)
    eq = equity_monte_carlo(
        _h("7d 2c"),
        [],
        n_villains=1,
        villain_range=[(Card.from_str("As"), Card.from_str("Ks"))],
        iterations=2000,
        rng=rng,
    )
    assert eq < 0.40


def test_equity_made_flush_river():
    rng = random.Random(42)
    # Hero has nut flush on river vs random
    eq = equity_monte_carlo(
        _h("As Ks"),
        _h("Qs Js 2s 3d 4c"),
        n_villains=1,
        iterations=1500,
        rng=rng,
    )
    # Royal flush — must always win
    assert eq == 1.0
