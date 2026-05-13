"""ShinkaEvolve-style novelty rejection — reject candidates too similar to recent archive.

Reference: ShinkaEvolve (arXiv:2509.19349).
"""

from __future__ import annotations

import math
from typing import Sequence

from darwin.db.schemas import Genome


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def gene_vector(g: Genome) -> list[float]:
    """Encode a genome as a flat float vector for similarity comparison."""
    r = g.retrieval_genes
    c = g.coordination_genes
    gen = g.generation_genes

    EMBED_OPTS = ("voyage-4", "voyage-4-large", "voyage-4-lite", "voyage-4-nano")
    CHUNK_OPTS = (128, 256, 512, 1024)
    QT_OPTS = ("none", "hyde", "multi_query", "step_back")
    RR_OPTS = ("none", "rrf", "voyage-rerank-2")
    PROTO_OPTS = ("solo", "vote", "consult", "debate")
    GENMOD_OPTS = ("claude-haiku-4-5-20251001", "claude-sonnet-4-6")
    MODE_OPTS = ("skip", "single_shot", "iterative", "agentic")
    HIER_OPTS = ("single_level", "dual_level", "dfs_pruning", "lca_stopping")
    GRAPH_OPTS = ("none", "entity_relation", "topic_summary", "rule_graph", "temporal")
    QUANT_OPTS = ("float32", "int8", "binary")

    def idx_norm(value, options):
        try:
            return float(options.index(value)) / max(1, len(options) - 1)
        except ValueError:
            return 0.0

    parts: list[float] = []

    # Retrieval
    parts.append(idx_norm(r.embedding_model, EMBED_OPTS))
    parts.append(idx_norm(r.chunk_size, CHUNK_OPTS))
    parts.append(r.chunk_overlap)
    parts.append(idx_norm(r.query_transform, QT_OPTS))
    parts.append(idx_norm(r.rerank, RR_OPTS))
    parts.append(r.confidence_threshold)
    parts.append(min(1.0, r.top_k / 50.0))
    parts.append(r.search_depth_policy)
    parts.append(idx_norm(r.retrieval_mode_router, MODE_OPTS))
    parts.append(idx_norm(r.hierarchical_traversal_strategy, HIER_OPTS))
    parts.append(idx_norm(r.graph_construction_mode, GRAPH_OPTS))
    parts.append(r.graph_eagerness)
    parts.append(min(1.0, r.embedding_compression_dim / 2560.0))
    parts.append(idx_norm(r.embedding_quantization, QUANT_OPTS))
    parts.append(r.context_utilization_ratio)

    # Coordination
    parts.append(idx_norm(c.protocol, PROTO_OPTS))
    parts.append(c.consult_threshold)
    parts.append(min(1.0, c.timeout_ms / 10000.0))
    parts.append(min(1.0, c.debate_rounds / 3.0))
    parts.append(c.signal_decay_rate)
    parts.append(c.pressure_response_sensitivity)
    parts.append((c.sycophancy_spectrum + 1.0) / 2.0)
    parts.append(c.confidence_calibration)
    parts.append(c.bid_aggressiveness)
    parts.append(c.value_density_estimator)
    parts.append(c.marginal_contribution_threshold)
    parts.append(c.leader_candidacy)
    parts.extend([(x + 1.0) / 2.0 for x in c.capability_embedding])

    # Generation
    parts.append(idx_norm(gen.model, GENMOD_OPTS))
    parts.append(min(1.0, gen.temperature / 1.5))
    parts.append(min(1.0, gen.max_tokens / 4096.0))

    return parts


def novelty_reject(
    candidate: Genome,
    archive: Sequence[Genome],
    *,
    threshold: float = 0.95,
) -> bool:
    if not archive:
        return False
    v = gene_vector(candidate)
    for g in archive:
        sim = cosine_similarity(v, gene_vector(g))
        if sim >= threshold:
            return True
    return False
