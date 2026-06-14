from poker_coach.cards import Card, Rank, Street, Suit, full_deck


def test_card_str_roundtrip():
    c = Card(Rank.ACE, Suit.SPADES)
    assert str(c) == "As"
    assert Card.from_str("As") == c
    assert Card.from_str("td") == Card(Rank.TEN, Suit.DIAMONDS)


def test_rank_value_int():
    assert Rank.TWO.value_int == 2
    assert Rank.ACE.value_int == 14
    assert Rank.TEN.value_int == 10


def test_full_deck_unique():
    deck = full_deck()
    assert len(deck) == 52
    assert len({str(c) for c in deck}) == 52


def test_street_from_board_len():
    assert Street.from_board_len(0) == Street.PREFLOP
    assert Street.from_board_len(3) == Street.FLOP
    assert Street.from_board_len(4) == Street.TURN
    assert Street.from_board_len(5) == Street.RIVER


def test_treys_conversion():
    c = Card.from_str("Ah")
    assert isinstance(c.to_treys(), int)
