from __future__ import annotations

from darwin.fitness.eval_split import (
    generalization_gap,
    mongo_match_exclude_holdout,
    split_evaluation_queries,
    tag_eval_document,
)


def test_split_evaluation_queries_shuffle_deterministic() -> None:
    queries = [f"q{i}" for i in range(10)]
    train, holdout = split_evaluation_queries(
        queries, holdout_fraction=0.3, seed=123, stratify_key=None
    )
    train2, holdout2 = split_evaluation_queries(
        queries, holdout_fraction=0.3, seed=123, stratify_key=None
    )

    assert len(train) + len(holdout) == 10
    assert len(holdout) == round(10 * 0.3)
    assert sorted(train + holdout) == sorted(queries)
    assert train == train2 and holdout == holdout2


def test_split_evaluation_queries_stratified_by_difficulty() -> None:
    queries = [{"id": i, "text": f"t{i}", "difficulty": ["easy", "hard"][i % 2]} for i in range(8)]
    train, holdout = split_evaluation_queries(
        queries, holdout_fraction=0.5, seed=7, stratify_key="difficulty"
    )
    keys_tr = {q["difficulty"] for q in train}
    keys_ho = {q["difficulty"] for q in holdout}

    assert len(train) == 4 and len(holdout) == 4
    assert keys_tr <= {"easy", "hard"}
    assert keys_ho <= {"easy", "hard"}
    seen = {q["id"] for q in train} | {q["id"] for q in holdout}
    assert seen == set(range(8))


def test_mongo_match_exclude_holdout() -> None:
    assert mongo_match_exclude_holdout(3) == {
        "generation": 3,
        "$or": [
            {"eval_split": {"$exists": False}},
            {"eval_split": "train"},
        ],
    }


def test_tag_eval_document() -> None:
    doc: dict[str, object] = {"a": 1}
    tag_eval_document(doc, "holdout")
    assert doc["eval_split"] == "holdout"


def test_generalization_gap() -> None:
    assert generalization_gap([0.9, 1.0], [0.4, 0.5]) == 0.5
    assert generalization_gap([], [0.5]) is None
