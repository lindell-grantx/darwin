"""Pass 3: execute a RetrievalPipeline DAG against a query via discrete steps.

Pass 3 PR-3 update: this module no longer collapses the DAG into a flat legacy
genes dict and calls `retriever.retrieve()`. Instead it walks the topological
order and dispatches each node to the matching `retrieval.steps` callable
(`chunk_query` / `embed_query` / `vector_search` / `rerank_chunks`) plus a
`generate` step via `darwin.llm.vertex.vertex_complete`.

PR-4 wires up branching execution: each node reads upstream context from its
incoming edges, produces output context for downstream consumers, and fuse
nodes merge multiple upstream contexts via RRF.
"""

from __future__ import annotations

from typing import Any

from darwin.genome.pipeline import PipelineNode, RetrievalPipeline


_GENERATOR_MODEL_ALIASES = {
    "claude_haiku": "claude-haiku-4-5-20251001",
    "claude_sonnet": "claude-sonnet-4-6",
}


def operator_to_legacy_kwargs(node: PipelineNode) -> dict[str, Any]:
    """Translate a PipelineNode's operator + params into kwargs the legacy runner expects.

    Pure function — no I/O. The actual execution is orchestrated by execute_pipeline.
    """
    if node.stage == "chunk":
        return {
            "chunk_size": node.params.get("chunk_size", 512),
            "chunk_overlap": node.params.get("chunk_overlap", 0.1),
        }
    if node.stage == "embed":
        return {"model": node.params.get("model", "voyage-4")}
    if node.stage == "retrieve":
        return {
            "top_k": node.params.get("top_k", 10),
            "confidence_threshold": node.params.get("confidence_threshold", 0.5),
            "source_routing": node.params.get("source_routing", ["mongodb"]),
        }
    if node.stage == "rerank":
        # Legacy rerank takes `method`, not `strategy`. The operator name on a
        # rerank node IS the method (none / rrf / voyage_rerank_2).
        return {"method": node.operator}
    if node.stage == "generate":
        return {"model": node.params.get("model", "claude_haiku")}
    return dict(node.params)


async def execute_pipeline(
    pipeline: RetrievalPipeline,
    query: str,
    *,
    db=None,
):
    """Execute the DAG. Supports fan-out + RRF fuse.

    Walks topological order; each node reads upstream context from incoming
    edges, produces output context for downstream consumers. Fuse nodes merge
    multiple upstream contexts via the operator's fuse method (RRF).
    """
    from darwin.retrieval import steps as retrieval_steps

    sorted_nodes = pipeline.topological_sort()

    # incoming: dst_id -> list[src_id]
    incoming: dict[str, list[str]] = {n.node_id: [] for n in pipeline.nodes}
    for e in pipeline.edges:
        incoming[e.to_id].append(e.from_id)

    # Per-node output context dict
    contexts: dict[str, dict] = {}

    for node in sorted_nodes:
        upstream_ids = incoming[node.node_id]
        upstream_ctxs = [contexts[uid] for uid in upstream_ids if uid in contexts]

        # Compose input context from upstream
        if len(upstream_ctxs) > 1 and node.stage == "fuse":
            ctx = _fuse_contexts(upstream_ctxs, node)
        elif len(upstream_ctxs) >= 1:
            ctx = dict(upstream_ctxs[0])
        else:
            ctx = {"query": query, "embedding": [], "chunks": [], "answer": ""}

        kwargs = operator_to_legacy_kwargs(node)

        if node.stage == "chunk":
            ctx["query"] = await retrieval_steps.chunk_query(ctx.get("query", query), kwargs)
        elif node.stage == "embed":
            ctx["embedding"] = await retrieval_steps.embed_query(ctx.get("query", query), kwargs)
        elif node.stage == "retrieve":
            ctx["chunks"] = await retrieval_steps.vector_search(ctx.get("embedding", []), kwargs)
        elif node.stage == "rerank":
            ctx["chunks"] = await retrieval_steps.rerank_chunks(
                ctx.get("query", query), ctx.get("chunks", []), kwargs,
            )
        elif node.stage == "generate":
            from darwin.llm import vertex as vertex_mod
            chunks_for_ctx = ctx.get("chunks", [])
            context_text = "\n\n".join(
                c.text if hasattr(c, "text") else str(c)
                for c in chunks_for_ctx[:10]
            )
            ctx["answer"] = await vertex_mod.vertex_complete(
                system="Answer the user query using the retrieved context.",
                user=f"Query: {ctx.get('query', query)}\n\nContext:\n{context_text}",
                max_tokens=512,
            )
        # pre_embed_enrich / fuse / post_retrieve_filter / post_gen_refine —
        # fuse handled above by _fuse_contexts; others pass-through for now

        contexts[node.node_id] = ctx

    # Final output is the context of the last node
    final = contexts[sorted_nodes[-1].node_id]
    return {
        "answer": final.get("answer", ""),
        "chunks": final.get("chunks", []),
        "embedding": final.get("embedding", []),
    }


def _fuse_contexts(upstream_ctxs: list[dict], fuse_node) -> dict:
    """Merge multiple upstream contexts. For Pass 3, fuse method is 'rrf' on chunks."""
    if fuse_node.operator == "rrf":
        # Reciprocal Rank Fusion on chunks
        scores: dict[str, float] = {}
        chunk_by_id: dict[str, object] = {}
        for ctx in upstream_ctxs:
            for rank, chunk in enumerate(ctx.get("chunks", [])):
                cid = chunk.chunk_id if hasattr(chunk, "chunk_id") else str(chunk)
                scores[cid] = scores.get(cid, 0.0) + 1.0 / (60 + rank)
                chunk_by_id[cid] = chunk
        ranked_ids = sorted(scores, key=lambda c: -scores[c])
        merged = dict(upstream_ctxs[0])
        merged["chunks"] = [chunk_by_id[cid] for cid in ranked_ids]
        return merged

    # Identity fuse: take first upstream
    return dict(upstream_ctxs[0])
