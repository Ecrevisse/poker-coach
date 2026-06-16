"""Advisor V2: position-aware ranges + EV(call) + EV(raise) with fold-equity."""

from __future__ import annotations

from dataclasses import dataclass

from .cards import Action, Card, Street
from .engine import equity_monte_carlo, ev_call, ev_fold, ev_raise, pot_odds
from .ranges import open_range
from .state import GameState

# Per-villain fold equity vs a pot-sized aggressive bet, by street.
# Coarse priors; can be tuned later with player profiling.
_FE_PER_VILLAIN: dict[Street, float] = {
    Street.PREFLOP: 0.45,
    Street.FLOP:    0.40,
    Street.TURN:    0.35,
    Street.RIVER:   0.30,
}

# Raise sizing as multiple of effective_pot.
_RAISE_SIZING_FACTOR = 0.75


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


def _villain_ranges(gs: GameState) -> list[list[tuple[Card, Card]] | None]:
    """Per-active-villain estimated combo range based on their position."""
    ranges: list[list[tuple[Card, Card]] | None] = []
    for v in gs.active_villains:
        combos = open_range(v.position)
        ranges.append(combos if combos else None)
    return ranges


def _combined_fold_equity(gs: GameState) -> float:
    """Probability that ALL active villains fold to a pot-sized raise.
    Independence assumption per villain (rough)."""
    fe = _FE_PER_VILLAIN.get(gs.street, 0.35)
    n = len(gs.active_villains)
    if n == 0:
        return 1.0
    return fe ** n


def advise(gs: GameState, iterations: int = 5000) -> Advice:
    n_v = max(1, len(gs.active_villains))
    ranges = _villain_ranges(gs)
    # Pad to n_v in case active list and n_v differ (defensive).
    while len(ranges) < n_v:
        ranges.append(None)

    eq = equity_monte_carlo(
        gs.hero_cards, gs.board, n_villains=n_v,
        villain_ranges=ranges if any(r for r in ranges) else None,
        iterations=iterations,
    )
    eff_pot = gs.effective_pot
    po = pot_odds(gs.to_call, eff_pot)
    evf = ev_fold()
    evc = ev_call(eq, eff_pot, gs.to_call)

    raise_size = max(gs.big_blind, int(eff_pot * _RAISE_SIZING_FACTOR))
    raise_size = min(raise_size, max(0, gs.hero_stack - gs.to_call))
    fe = _combined_fold_equity(gs)
    evr = ev_raise(eq, eff_pot, gs.to_call, raise_size, fe) if raise_size > 0 else None

    # Decision: highest EV wins; CHECK if no bet to face and raise not justified.
    candidates: list[tuple[float, Action, int | None]] = [(evf, Action.FOLD, None)]
    if gs.to_call == 0:
        candidates.append((evf, Action.CHECK, None))
    else:
        candidates.append((evc, Action.CALL, None))
    if evr is not None:
        candidates.append((evr, Action.RAISE if gs.to_call > 0 else Action.BET, raise_size))

    best_ev, best_action, best_sizing = max(candidates, key=lambda x: x[0])

    # CHECK preferred over FOLD when free (both EV=0).
    if gs.to_call == 0 and best_action == Action.FOLD:
        best_action = Action.CHECK

    reason_parts = [
        f"Equity {eq:.1%} vs {n_v} villains",
        f"effective pot ${eff_pot}",
        f"to_call ${gs.to_call}",
        f"pot odds {po:.1%}",
        f"EV(call)={evc:+.1f}",
    ]
    if evr is not None:
        reason_parts.append(f"EV(raise ${raise_size}, FE {fe:.0%})={evr:+.1f}")
    expl = " | ".join(reason_parts) + f" → {best_action.value.upper()}"

    return Advice(
        action=best_action,
        sizing=best_sizing,
        equity=eq,
        pot_odds=po,
        ev_fold=evf,
        ev_call=evc,
        ev_raise=evr,
        explanation=expl,
    )
