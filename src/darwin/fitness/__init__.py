"""Fitness judging for Darwin answers."""

from darwin.fitness.eval_split import (
    EvalSplit,
    generalization_gap,
    mongo_match_exclude_holdout,
    split_evaluation_queries,
    tag_eval_document,
)
from darwin.fitness.judge import JudgeScores, evaluate_answer
from darwin.fitness.score import composite_fitness

__all__ = [
    "EvalSplit",
    "JudgeScores",
    "composite_fitness",
    "evaluate_answer",
    "generalization_gap",
    "mongo_match_exclude_holdout",
    "split_evaluation_queries",
    "tag_eval_document",
]
