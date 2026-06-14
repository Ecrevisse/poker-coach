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


def _fmt_cards(cards: list) -> str:
    if not cards:
        return "—"
    parts = []
    for c in cards:
        parts.append(f"[{_SUIT_COLOR[c.suit]}]{c}[/]")
    return " ".join(parts)


def render(gs: GameState, adv: Advice) -> Panel:
    t = Table(show_header=False, expand=True)
    t.add_column("k", style="bold")
    t.add_column("v")
    t.add_row("Hero", _fmt_cards(gs.hero_cards))
    t.add_row("Board", _fmt_cards(gs.board))
    t.add_row("Street", gs.street.value)
    t.add_row("Pot", str(gs.pot))
    t.add_row("To call", str(gs.to_call))
    t.add_row("Hero stack", str(gs.hero_stack))
    t.add_row("SPR", f"{gs.spr:.1f}")
    t.add_row("Equity", f"{adv.equity:.1%}")
    t.add_row("Pot odds", f"{adv.pot_odds:.1%}")
    t.add_row("EV call", f"{adv.ev_call:+.1f}")
    t.add_row("DECISION", f"[bold green]{adv.action.value.upper()}[/]")
    return Panel(t, title="Poker Coach", subtitle=adv.explanation)
