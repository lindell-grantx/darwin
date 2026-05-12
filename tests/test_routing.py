"""v2 MVP: routing layer matches incoming queries to query-type buckets."""

import pytest

from darwin.api.routing import cosine_similarity, route_query_to_bucket
from darwin.db.schemas import QueryTypeBucket


def test_cosine_similarity_known():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == pytest.approx(1.0)

    c = [0.0, 1.0, 0.0]
    assert cosine_similarity(a, c) == pytest.approx(0.0)

    d = [-1.0, 0.0, 0.0]
    assert cosine_similarity(a, d) == pytest.approx(-1.0)


def test_cosine_similarity_zero_vector_returns_zero():
    a = [0.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    assert cosine_similarity(a, b) == 0.0


def test_route_picks_highest_cosine():
    buckets = [
        QueryTypeBucket(
            bucket_key=("a",), embedding=[1.0, 0.0, 0.0], n_queries=5,
        ),
        QueryTypeBucket(
            bucket_key=("b",), embedding=[0.0, 1.0, 0.0], n_queries=5,
        ),
    ]
    query_emb = [0.9, 0.1, 0.0]
    chosen = route_query_to_bucket(query_emb, buckets)
    assert chosen.bucket_key == ("a",)


def test_route_empty_buckets_raises():
    with pytest.raises(ValueError):
        route_query_to_bucket([1.0, 0.0], [])
