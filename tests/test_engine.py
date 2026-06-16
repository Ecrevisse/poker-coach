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
    # 60% equity, effective_pot 100 (includes villain's bet already), to_call 50
    # Win: take effective_pot (net of own call) = 100. Lose: lose 50.
    # EV = 0.6*100 - 0.4*50 = 60 - 20 = 40
    assert ev_call(0.6, 100, 50) == 40.0


def test_ev_call_break_even_matches_pot_odds():
    eq = pot_odds(50, 100)
    assert abs(ev_call(eq, 100, 50)) < 1e-9


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
        villain_ranges=[[(Card.from_str("As"), Card.from_str("Ks"))]],
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
