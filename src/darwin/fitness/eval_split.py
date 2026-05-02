"""Train / holdout splits for evaluations — reduce evolutionary overfitting to the query train set.

Fitness rows may carry ``eval_split: "train" | "holdout"``. Evolution selection defaults to
excluding holdout averages (see ``aggregate_mean_fitness_by_generation``).

Documents without ``eval_split`` are treated like **train** (backwards-compatible).
"""

from __future__ import annotations

from collections import defaultdict
from random import Random
from typing import Any, Literal, Mapping, MutableMapping, Sequence, TypeVar

T = TypeVar("T")

EvalSplit = Literal["train", "holdout"]


def split_evaluation_queries(
    queries: Sequence[T],
    *,
    holdout_fraction: float = 0.2,
    seed: int = 42,
    stratify_key: str | None = "difficulty",
) -> tuple[list[T], list[T]]:
    """Partition ``queries`` into (train, holdout) deterministically.

    - When ``stratify_key`` is set and **every** item is a ``Mapping`` that contains
      that key, the split is **stratified** per bucket (stable bucket order).
    - Otherwise performs a global seeded shuffle and takes the trailing slice as holdout.

    ``holdout_fraction`` is capped so at least one query stays in **train** when
    ``len(queries) > 1``.
    """

    queries_list = list(queries)
    n = len(queries_list)
    if n == 0:
        return [], []

    frac = float(holdout_fraction)
    frac = max(0.0, min(frac, 0.999))
    nh = round(n * frac)
    nh = max(0, nh)
    if n > 1 and nh >= n:
        nh = n - 1

    if stratify_key is not None:
        keyed = [_strat_bucket(item, stratify_key) for item in queries_list]
        if "__missing__" not in keyed:
            indices_by_bucket: dict[Any, list[int]] = defaultdict(list)
            for i, bucket in enumerate(keyed):
                indices_by_bucket[bucket].append(i)
            rng = Random(seed)
            train_ix: list[int] = []
            holdout_ix: list[int] = []
            for bucket in sorted(indices_by_bucket, key=lambda b: repr(b)):
                ix = indices_by_bucket[bucket][:]
                rng.shuffle(ix)
                n_b = len(ix)
                nh_b = max(0, min(round(n_b * frac), n_b))
                if n_b > 1 and nh_b >= n_b:
                    nh_b = n_b - 1
                holdout_ix.extend(ix[-nh_b:])
                train_ix.extend(ix[:-nh_b] if nh_b else ix)
            train = [queries_list[i] for i in sorted(train_ix)]
            holdout = [queries_list[i] for i in sorted(holdout_ix)]
            return train, holdout

    rng = Random(seed)
    idx = list(range(n))
    rng.shuffle(idx)
    holdout_ix = idx[-nh:] if nh else []
    train_ix = idx[:-nh] if nh else idx[:]
    train = [queries_list[i] for i in sorted(train_ix)]
    holdout = [queries_list[i] for i in sorted(holdout_ix)]
    return train, holdout


def _strat_bucket(item: T, key: str) -> Any:
    if isinstance(item, Mapping):
        mapping: Mapping[Any, Any] = item
        if key not in mapping:
            return "__missing__"
        return mapping[key]
    return "__missing__"


def generalization_gap(
    train_scores: Sequence[float],
    holdout_scores: Sequence[float],
) -> float | None:
    """Mean(train) − mean(holdout). Positive ⇒ likely overfitting to train queries.

    Returns ``None`` if either sequence is empty.
    """

    if not train_scores or not holdout_scores:
        return None
    tm = sum(train_scores) / len(train_scores)
    hm = sum(holdout_scores) / len(holdout_scores)
    return round(tm - hm, 4)


def tag_eval_document(
    doc: MutableMapping[str, Any],
    split: EvalSplit | None,
) -> None:
    """In-place annotate a fitness evaluation payload with ``eval_split``."""

    if split is None:
        return
    doc["eval_split"] = split


def mongo_match_exclude_holdout(generation: int) -> dict[str, Any]:
    """``$match`` stage: one generation row, omit holdout-labelled evaluations."""

    return {
        "generation": generation,
        "$or": [
            {"eval_split": {"$exists": False}},
            {"eval_split": "train"},
        ],
    }
