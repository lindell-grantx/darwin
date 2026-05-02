from __future__ import annotations

import asyncio

from pytest import MonkeyPatch

from darwin.agents.blackboard import CandidateAnswer
from darwin.agents.coordinator import coordinate, execute_protocol
from darwin.agents.runner import evaluate, run_genome
from darwin.fitness.judge import composite_score
from darwin.fitness.score import composite_fitness
from darwin.retrieval.retriever import RetrievedChunk, build_vector_pipeline


def test_vector_pipeline_uses_genome_model_path_and_index() -> None:
    pipeline = build_vector_pipeline(
        query_vector=[0.1, 0.2, 0.3],
        genes={"embedding_model": "voyage_4", "top_k": 3},
        top_k=3,
    )

    vector_stage = pipeline[0]["$vectorSearch"]
    assert vector_stage["index"] == "vec_voyage_4"
    assert vector_stage["path"] == "embeddings.voyage_4"
    assert vector_stage["queryVector"] == [0.1, 0.2, 0.3]
    assert vector_stage["limit"] == 6


def test_coordinate_highest_confidence_protocol(monkeypatch: MonkeyPatch) -> None:
    async def fake_generate(query: str, chunks: list[RetrievedChunk], agent_name: str) -> CandidateAnswer:
        confidence = {"retriever": 0.7, "skeptic": 0.4, "synthesizer": 0.9}[agent_name]
        return CandidateAnswer(agent_name=agent_name, answer=f"{agent_name} answer", confidence=confidence)

    monkeypatch.setattr("darwin.agents.coordinator.generate_candidate", fake_generate)

    answer, candidates = asyncio.run(
        coordinate(
            "How does Darwin retrieve context?",
            [RetrievedChunk("chunk-1", "Darwin uses vector search.", 0.8)],
            {"protocol": "vote", "consultation_count": 2, "disagreement_resolver": "highest_confidence"},
        )
    )

    assert answer == "synthesizer answer"
    assert [candidate.agent_name for candidate in candidates] == ["retriever", "skeptic", "synthesizer"]


def test_run_genome_wires_retrieval_coordination_and_judge(monkeypatch: MonkeyPatch) -> None:
    chunks = [RetrievedChunk("chunk-1", "Atlas Vector Search retrieves matching chunks.", 0.82)]

    async def fake_retrieve(query: str, genes: dict, top_k_override: int | None = None) -> list[RetrievedChunk]:
        assert query == "How are chunks retrieved?"
        assert genes["embedding_model"] == "voyage_4"
        return chunks

    async def fake_coordinate(
        query: str,
        retrieved: list[RetrievedChunk],
        genes: dict,
    ) -> tuple[str, list[CandidateAnswer]]:
        assert retrieved == chunks
        assert genes["protocol"] == "solo"
        return "Atlas Vector Search retrieves matching chunks.", [
            CandidateAnswer("synthesizer", "Atlas Vector Search retrieves matching chunks.", 0.82)
        ]

    async def fake_persist(result: object, **_kwargs: object) -> None:  # noqa: ARG001
        from darwin.agents.runner import AgentRunResult

        assert isinstance(result, AgentRunResult)
        assert result.genome_id == "genome-1"

    monkeypatch.setattr("darwin.agents.runner.retrieve", fake_retrieve)
    monkeypatch.setattr("darwin.agents.runner.coordinate", fake_coordinate)
    monkeypatch.setattr("darwin.agents.runner.persist_run_result", fake_persist)

    result = asyncio.run(
        run_genome(
            "How are chunks retrieved?",
            {
                "id": "genome-1",
                "retrieval_genes": {"embedding_model": "voyage_4"},
                "coordination_genes": {"protocol": "solo"},
            },
            ground_truth="Atlas Vector Search retrieves matching chunks.",
        )
    )

    assert result.genome_id == "genome-1"
    assert result.answer == "Atlas Vector Search retrieves matching chunks."
    assert result.fitness.composite > 0
    assert result.to_document()["retrieval_trace"][0]["chunk_id"] == "chunk-1"


def test_composite_score_rewards_quality_and_penalizes_slow_expensive_runs() -> None:
    strong = composite_score(0.9, 0.9, 0.8, latency_ms=500, cost_usd=0.005)
    weak = composite_score(0.4, 0.4, 0.3, latency_ms=5000, cost_usd=0.05)

    assert strong > weak
    assert 0.0 <= weak <= 1.0
    assert 0.0 <= strong <= 1.0


def test_dar_9_composite_fitness_signature() -> None:
    assert composite_fitness({"relevance": 1.0, "accuracy": 0.5, "coverage": 0.0}) == 0.6


def test_dar_9_execute_protocol_signature(monkeypatch: MonkeyPatch) -> None:
    chunks = [RetrievedChunk("chunk-1", "Darwin retrieves evidence.", 0.9)]

    async def fake_retrieve(query: str, genes: dict) -> list[RetrievedChunk]:
        return chunks

    async def fake_coordinate(
        query: str,
        retrieved: list[RetrievedChunk],
        genes: dict,
    ) -> tuple[str, list[CandidateAnswer]]:
        return "Darwin retrieves evidence.", [
            CandidateAnswer("synthesizer", "Darwin retrieves evidence.", 0.9)
        ]

    monkeypatch.setattr("darwin.retrieval.retriever.retrieve", fake_retrieve)
    monkeypatch.setattr("darwin.agents.coordinator.coordinate", fake_coordinate)

    from darwin.agents.blackboard import Blackboard

    blackboard = Blackboard(run_id="run-1", query="How?", genomes=[])
    answer, returned_chunks = asyncio.run(
        execute_protocol(
            {
                "id": "genome-1",
                "retrieval_genes": {},
                "coordination_genes": {"protocol": "solo"},
            },
            "How?",
            blackboard,
        )
    )

    assert answer == "Darwin retrieves evidence."
    assert returned_chunks == chunks
    assert blackboard.snapshot_for("genome-1")["proposal"]["confidence"] == 0.9


def test_dar_9_evaluate_signature(monkeypatch: MonkeyPatch) -> None:
    async def fake_run_genome(
        query: str,
        genome: dict,
        ground_truth: str | None = None,
        persist: bool = True,
        run_id: str | None = None,
        eval_split: str | None = None,
    ):
        from darwin.agents.runner import AgentRunResult
        from darwin.fitness.judge import JudgeScores

        return AgentRunResult(
            run_id=run_id or "run-1",
            genome_id="genome-1",
            answer="answer",
            chunks=[RetrievedChunk("chunk-1", "context", 0.8)],
            candidates=[CandidateAnswer("synthesizer", "answer", 0.8)],
            fitness=JudgeScores(0.8, 0.7, 0.6, 0.9, 100.0, 0.0, 0.72, "ok"),
        )

    inserts: list[dict] = []

    async def fake_insert(doc: dict) -> None:
        inserts.append(doc)

    monkeypatch.setattr("darwin.agents.runner.run_genome", fake_run_genome)
    monkeypatch.setattr("darwin.agents.runner._insert_evaluation_doc", fake_insert)

    from darwin.agents.blackboard import Blackboard

    bb = Blackboard(run_id="run-1", query="Question?", genomes=[])

    doc_train = asyncio.run(
        evaluate(
            {"id": "genome-1", "generation": 2},
            {"id": "query-1", "text": "Question?", "ground_truth": "Truth"},
            "run-1",
            bb,
        )
    )
    asyncio.run(
        evaluate(
            {"id": "genome-1", "generation": 2},
            {"id": "query-2", "text": "Question?", "ground_truth": "Truth"},
            "run-ho",
            bb,
            eval_split="holdout",
        )
    )

    doc = doc_train
    assert doc["query_id"] == "query-1"
    assert doc["generated_answer"] == "answer"
    assert doc["composite_fitness"] == 0.72
    assert inserts[0].get("eval_split") is None
    assert inserts[1].get("eval_split") == "holdout"
