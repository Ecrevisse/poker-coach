from poker_coach.ranges import PREFLOP_OPEN_RANGES, expand, open_range


def test_expand_pair():
    combos = expand({"AA"})
    assert len(combos) == 6  # C(4,2)


def test_expand_pair_plus():
    combos = expand({"TT+"})  # TT JJ QQ KK AA -> 5 pairs * 6 combos
    assert len(combos) == 30


def test_expand_suited():
    combos = expand({"AKs"})
    assert len(combos) == 4


def test_expand_offsuit():
    combos = expand({"AKo"})
    assert len(combos) == 12


def test_expand_axs_plus():
    combos = expand({"A2s+"})  # A2s..AKs -> 12 hands * 4 combos
    assert len(combos) == 48


def test_open_range_btn_largest():
    btn = len(open_range(PREFLOP_OPEN_RANGES.__iter__().__next__()))  # noqa: B019
    # smoke: BTN range expansion does not crash
    from poker_coach.cards import Position

    assert len(open_range(Position.BTN)) > len(open_range(Position.UTG)) > 0
    _ = btn
