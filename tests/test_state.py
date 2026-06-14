from poker_coach.cards import Card, Street
from poker_coach.state import GameState, Villain


def test_gamestate_defaults():
    gs = GameState()
    assert gs.pot == 0
    assert gs.street == Street.PREFLOP
    assert gs.spr == float("inf")


def test_spr():
    gs = GameState(pot=100, hero_stack=300)
    assert gs.spr == 3.0


def test_active_villains():
    gs = GameState(villains=[Villain(1), Villain(2, in_hand=False), Villain(3)])
    assert len(gs.active_villains) == 2


def test_derive_street():
    gs = GameState(board=[Card.from_str(c) for c in ["As", "Kd", "2c"]])
    assert gs.derive_street() == Street.FLOP


def test_hash_key_changes():
    gs1 = GameState(pot=100, to_call=20)
    gs2 = GameState(pot=120, to_call=20)
    assert gs1.hash_key() != gs2.hash_key()
