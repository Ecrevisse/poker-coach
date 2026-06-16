"""Rich terminal UI."""

from __future__ import annotations

from rich.panel import Panel
from rich.table import Table

from .advisor import Advice
from .cards import Suit
from .state import GameState

_SUIT_COLOR = {
    Suit.SPADES: "white",
    Suit.CLUBS: "green",
    Suit.HEARTS: "red",
    Suit.DIAMONDS: "blue",
}

_ACTION_COLOR = {
    "fold":  "red",
    "check": "yellow",
    "call":  "yellow",
    "bet":   "green",
    "raise": "green",
    "allin": "magenta",
}


def _fmt_cards(cards: list) -> str:
    if not cards:
        return "—"
    return " ".join(f"[{_SUIT_COLOR[c.suit]}]{c}[/]" for c in cards)


def render(gs: GameState, adv: Advice) -> Panel:
    t = Table(show_header=False, expand=True)
    t.add_column("k", style="bold")
    t.add_column("v")
    t.add_row("Hero", f"{_fmt_cards(gs.hero_cards)}  [dim]({gs.hero_position.value})[/]")
    t.add_row("Board", f"{_fmt_cards(gs.board)}  [dim]({gs.street.value})[/]")
    t.add_row("Pot / Eff", f"${gs.pot} / [bold]${gs.effective_pot}[/]")
    t.add_row("To call", f"${gs.to_call}")
    t.add_row("Hero stack", f"${gs.hero_stack}  (SPR {gs.spr:.1f})")
    t.add_row("Active vs", str(len(gs.active_villains)))
    t.add_row("Equity", f"{adv.equity:.1%}")
    t.add_row("Pot odds", f"{adv.pot_odds:.1%}  [dim](need)[/]")
    t.add_row("EV fold",  f"{adv.ev_fold:+.1f}")
    t.add_row("EV call",  f"{adv.ev_call:+.1f}")
    if adv.ev_raise is not None:
        sizing = f" ${adv.sizing}" if adv.sizing else ""
        t.add_row("EV raise" + sizing, f"{adv.ev_raise:+.1f}")
    color = _ACTION_COLOR.get(adv.action.value, "green")
    t.add_row("DECISION", f"[bold {color}]{adv.action.value.upper()}[/]")
    return Panel(t, title="Poker Coach", subtitle=adv.explanation)
