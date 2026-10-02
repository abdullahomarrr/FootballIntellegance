from football_intelligence.lineup import build_lineup


def p(pid, group, minutes, codes="", value=1.0, rating=None):
    return {
        "player_id": pid, "position_group": group, "minutes": minutes,
        "position_codes": codes, "market_value_eur": value, "rating": rating,
    }


def squad():
    return [
        p(1, "GK", 900), p(2, "GK", 90),
        p(10, "DF", 900, "LB"), p(11, "DF", 900, "CB"), p(12, "DF", 880, "CB"),
        p(13, "DF", 860, "RB"), p(14, "DF", 100, "CB"),
        p(20, "MD", 900, "CM"), p(21, "MD", 890, "LM"), p(22, "MD", 870, "RM"),
        p(23, "MD", 50, "CM"),
        p(30, "FW", 900, "ST"), p(31, "FW", 700, "LW"), p(32, "FW", 600, "RW"),
        p(33, "FW", 20, "ST"),
    ]


def test_lineup_picks_the_most_played_and_forms_lines():
    lineup = build_lineup(squad())
    ids = {s["player_id"] for s in lineup["starters"]}
    assert len(lineup["starters"]) == 11 and lineup["formation"] == "4-3-3"
    assert ids == {1, 10, 11, 12, 13, 20, 21, 22, 30, 31, 32}
    assert set(lineup["bench"]) == {2, 14, 23, 33}
    keeper = next(s for s in lineup["starters"] if s["player_id"] == 1)
    assert keeper["y"] > 80 and keeper["x"] == 50


def test_lines_are_ordered_left_to_right_from_position_codes():
    lineup = build_lineup(squad())
    xs = {s["player_id"]: s["x"] for s in lineup["starters"]}
    assert xs[10] < xs[11] < xs[13]  # left back, centre-backs, right back
    assert xs[21] < xs[20] < xs[22]  # left mid, centre mid, right mid
    assert xs[31] < xs[30] < xs[32]  # left wing, striker, right wing
    ys = {s["player_id"]: s["y"] for s in lineup["starters"]}
    assert ys[1] > ys[10] > ys[20] > ys[30]  # keeper at the back, forwards at the front


def test_a_short_line_is_filled_so_the_shape_stays_playable():
    players = [p(1, "GK", 900)]
    players += [p(100 + i, "MD", 900 - i) for i in range(7)]  # lots of midfielders
    players += [p(200 + i, "FW", 800 - i) for i in range(3)]
    players += [p(300 + i, "DF", 10 + i) for i in range(4)]  # defenders barely played
    lineup = build_lineup(players)
    defenders = [s for s in lineup["starters"] if s["y"] == 70.0]
    assert len(defenders) >= 3 and len(lineup["starters"]) == 11


def test_missing_data_does_not_break_the_lineup():
    players = [p(1, "GK", None), p(2, "DF", None), p(3, "MD", None), p(4, "FW", None)]
    lineup = build_lineup(players)
    assert len(lineup["starters"]) == 4 and lineup["formation"] == "1-1-1"
    assert build_lineup([])["starters"] == []


def test_five_busy_defenders_still_give_a_four_back_line():
    players = [p(1, "GK", 900)]
    players += [p(10 + i, "DF", 900 - i, "CB") for i in range(5)]
    players += [p(20 + i, "MD", 700 - i, "CM") for i in range(4)]
    players += [p(30 + i, "FW", 650 - i, "ST") for i in range(3)]
    lineup = build_lineup(players)
    assert lineup["formation"].startswith("4-") and len(lineup["starters"]) == 11
    assert 14 in lineup["bench"]  # the least-played of the five defenders sits out


def test_trimming_a_full_line_never_refills_another_full_line():
    players = [p(1, "GK", 900)]
    players += [p(10 + i, "DF", 800 - i, "CB") for i in range(4)]  # back line already full
    players += [p(20 + i, "MD", 900 - i, "CM") for i in range(7)]  # too many midfielders
    players += [p(30, "FW", 100, "ST"), p(31, "DF", 790, "CB")]  # a fifth defender waits
    lineup = build_lineup(players)
    defenders = [s for s in lineup["starters"] if s["y"] == 70.0]
    assert len(defenders) <= 4 and len(lineup["starters"]) == 11
