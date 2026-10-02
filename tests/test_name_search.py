from football_intelligence.name_search import name_score


def test_exact_partial_and_accented_names_match():
    assert name_score("lamine yamal", "Lamine Yamal") == 1.0
    assert name_score("fermin", "Fermín") == 1.0
    assert name_score("vini", "Vinícius Júnior") == 1.0


def test_close_misspellings_match_but_rank_below_exact():
    typo = name_score("raphina", "Raphinha")
    assert 0 < typo < 1.0
    assert name_score("lamine yamaal", "Lamine Yamal") > 0


def test_unrelated_and_empty_queries_do_not_match():
    assert name_score("raphina", "Pedri") == 0
    assert name_score("lamine messi", "Lamine Yamal") == 0
    assert name_score("", "Pedri") == 0 and name_score("pedri", "") == 0
    assert name_score("ab", "Abde Ezzalzouli") == 1.0  # short tokens still match as substrings
    assert name_score("xyz", "Pedri") == 0
