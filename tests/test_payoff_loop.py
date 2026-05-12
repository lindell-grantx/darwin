"""v2 MVP: payoff helpers + row-count math.

The full integration loop requires Mongo+Vertex; that's smoke-tested manually.
Here we only test the pure helper that computes expected row counts.
"""


def test_expected_row_count_pure_function():
    from darwin.evolution.payoff import expected_row_count

    # 3 defenders × 37 queries = 111 clean rows
    # 3 defenders × 10 attackers × 37 queries = 1110 attacker rows
    # Note: in practice not every (defender, attacker, query) triple
    # produces a row — only when attacker.target_query_class == query.domain_tags
    # so the actual count will be lower. This pure helper computes the
    # MAXIMUM possible row count assuming every attacker targets every query.
    assert expected_row_count(n_defenders=3, n_attackers=10, n_queries=37) == 3 * 37 + 3 * 10 * 37


def test_expected_row_count_zero_defenders():
    from darwin.evolution.payoff import expected_row_count

    assert expected_row_count(n_defenders=0, n_attackers=10, n_queries=37) == 0


def test_expected_row_count_zero_attackers_only_clean():
    from darwin.evolution.payoff import expected_row_count

    assert expected_row_count(n_defenders=2, n_attackers=0, n_queries=3) == 6


def test_expected_row_count_basic():
    from darwin.evolution.payoff import expected_row_count

    rows = expected_row_count(n_defenders=2, n_attackers=10, n_queries=3)
    assert rows == 66  # 2*3 clean + 2*10*3 attacker
