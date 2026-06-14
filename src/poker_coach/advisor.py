"""Turn a GameState into a recommended Action + explanation."""

from __future__ import annotations

from dataclasses import dataclass

from .cards import Action, Card
from .engine import equity_monte_carlo, ev_call, ev_fold, pot_odds
from .ranges import open_range
from .state import GameState


@dataclass
class Advice:
    action: Action
    sizing: int | None
    equity: float
    pot_odds: float
    ev_fold: float
    ev_call: float
    ev_raise: float | None
    explanation: str


def estimate_villain_range(gs: GameState) -> list[tuple[Card, Card]] | None:
    """V1: take the most aggressive active villain's positional open-range.

    Returns None to mean 'random hand' (treated as wide range by engine).
    """
    aggressors = [v for v in gs.active_villains if v.last_bet > 0]
    if not aggressors:
        return None
    villain = max(aggressors, key=lambda v: v.last_bet)
    combos = open_range(villain.position)
    return combos or None


def advise(gs: GameState, iterations: int = 5000) -> Advice:
    n_v = max(1, len(gs.active_villains))
    villain_combos = estimate_villain_range(gs)
    eq = equity_monte_carlo(
        gs.hero_cards, gs.board, n_villains=n_v,
        villain_range=villain_combos, iterations=iterations,
    )
    po = pot_odds(gs.to_call, gs.pot)
    evc = ev_call(eq, gs.pot, gs.to_call)
    evf = ev_fold()

    if gs.to_call == 0:
        action = Action.CHECK
        reason = "No bet to face — check is free."
    elif evc > 0:
        action = Action.CALL
        reason = f"EV(call)={evc:+.1f} > 0, equity {eq:.1%} ≥ required {po:.1%}."
    else:
        action = Action.FOLD
        reason = f"EV(call)={evc:+.1f} < 0, equity {eq:.1%} < required {po:.1%}."

    expl = (
        f"Equity {eq:.1%} vs estimated range. "
        f"Pot odds {po:.1%}. EV(call)={evc:+.1f}, EV(fold)=0. → {action.value.upper()}. "
        f"{reason}"
    )
    return Advice(
        action=action,
        sizing=None,
        equity=eq,
        pot_odds=po,
        ev_fold=evf,
        ev_call=evc,
        ev_raise=None,
        explanation=expl,
    )
