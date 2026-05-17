"""Pass 3: execute a RetrievalPipeline DAG against a query via discrete steps.

Pass 3 PR-3 update: this module no longer collapses the DAG into a flat legacy
genes dict and calls `retriever.retrieve()`. Instead it walks the topological
order and dispatches each node to the matching `retrieval.steps` callable
(`chunk_query` / `embed_query` / `vector_search` / `rerank_chunks`) plus a
`generate` step via `darwin.llm.vertex.vertex_complete`.

PR-4 wires up the optional stages (pre_embed_enrich / fuse / post_retrieve_filter
/ post_gen_refine) and full branching execution.
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
):
    """Execute the DAG end-to-end via discrete steps.

    Walks `pipeline.topological_sort()` and dispatches each node to its
    corresponding step function based on `node.stage`. Branching is NOT yet
    supported (PR-4 adds it). For PR-3, we expect linear DAGs only — the
    `default_linear_pipeline` output.

    Returns dict with `answer`, `chunks`, and `embedding` keys.
    """
    from darwin.retrieval.steps import (
        chunk_query,
        embed_query,
        vector_search,
        rerank_chunks,
    )

    sorted_nodes = pipeline.topological_sort()

    current_query: str = query
    embedding: list[float] = []
    chunks: list = []
    answer: str = ""
    embedding_model: str = "voyage-4"

    for node in sorted_nodes:
        kwargs = operator_to_legacy_kwargs(node)
        if node.stage == "chunk":
            current_query = await chunk_query(current_query, kwargs)
        elif node.stage == "embed":
            embedding_model = kwargs.get("model", "voyage-4")
            embedding = await embed_query(current_query, kwargs)
        elif node.stage == "retrieve":
            # vector_search needs the genes-shaped dict to pick the right Atlas
            # index/path; carry the embedding model from the embed node visited above.
            search_params = {
                "genes": {"embedding_model": embedding_model},
                "top_k": kwargs["top_k"],
                "confidence_threshold": kwargs["confidence_threshold"],
            }
            chunks = await vector_search(embedding, search_params)
        elif node.stage == "rerank":
            chunks = await rerank_chunks(current_query, chunks, kwargs)
        elif node.stage == "generate":
            from darwin.llm.vertex import vertex_complete

            model_alias = kwargs.get("model", "claude_haiku")
            model_id = _GENERATOR_MODEL_ALIASES.get(model_alias, model_alias)
            context = "\n\n".join(
                c.text if hasattr(c, "text") else str(c)
                for c in chunks[:10]
            )
            answer = await vertex_complete(
                system="Answer the user query using the retrieved context.",
                user=f"Query: {current_query}\n\nContext:\n{context}",
                max_tokens=512,
                model=model_id,
            )
        # pre_embed_enrich / fuse / post_retrieve_filter / post_gen_refine — PR-4 wires them.

    return {"answer": answer, "chunks": chunks, "embedding": embedding}
