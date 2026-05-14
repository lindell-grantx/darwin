"""Pass 2: execute a RetrievalPipeline DAG against a query.

For Pass 2 we route operators to the same underlying functions the legacy
flat-genes runner uses (chunk/embed/retrieve/rerank/generate). The DAG just
provides structure; per-stage behavior is unchanged. Pass 3+ can introduce
operators that don't exist in the legacy path (e.g., LightRAG-style graph
construction at retrieve, ColPali vision-direct embedding).

Concretely, the legacy `retrieve(query, genes, top_k_override)` already fuses
embed -> vector_search -> rerank in one call, driven by a flat genes dict. So
we walk the DAG, gather per-stage params into an equivalent flat genes dict,
make one `retrieve()` call, then run `generate` separately. This keeps the
embedding-cache hits identical to the legacy path.
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


def _assemble_legacy_genes(pipeline: RetrievalPipeline) -> dict[str, Any]:
    """Collapse the DAG's chunk/embed/retrieve/rerank nodes into a flat genes dict
    compatible with `darwin.retrieval.retriever.retrieve`.
    """
    genes: dict[str, Any] = {}
    for node in pipeline.topological_sort():
        kwargs = operator_to_legacy_kwargs(node)
        if node.stage == "chunk":
            genes["chunk_size"] = kwargs["chunk_size"]
            genes["chunk_overlap"] = kwargs["chunk_overlap"]
        elif node.stage == "embed":
            genes["embedding_model"] = kwargs["model"]
        elif node.stage == "retrieve":
            genes["top_k"] = kwargs["top_k"]
            genes["confidence_threshold"] = kwargs["confidence_threshold"]
            genes["source_routing"] = kwargs["source_routing"]
        elif node.stage == "rerank":
            genes["rerank"] = kwargs["method"]
    return genes


async def execute_pipeline(
    pipeline: RetrievalPipeline,
    query: str,
):
    """Execute the DAG end-to-end. Returns dict with `answer`, `chunks`.

    For Pass 2 this walks topological order and invokes the legacy functions.
    Future passes can introduce branching execution if multiple parallel
    retrieve-fuse paths exist.
    """
    from darwin.retrieval.retriever import retrieve

    sorted_nodes = pipeline.topological_sort()
    legacy_genes = _assemble_legacy_genes(pipeline)

    chunks = await retrieve(query, legacy_genes)

    answer: str = ""
    for node in sorted_nodes:
        if node.stage != "generate":
            continue
        from darwin.llm.vertex import vertex_complete

        gen_kwargs = operator_to_legacy_kwargs(node)
        model_alias = gen_kwargs.get("model", "claude_haiku")
        model_id = _GENERATOR_MODEL_ALIASES.get(model_alias, model_alias)
        context = "\n\n".join(
            c.text if hasattr(c, "text") else str(c) for c in chunks[:10]
        )
        answer = await vertex_complete(
            system="Answer the user query using the retrieved context.",
            user=f"Query: {query}\n\nContext:\n{context}",
            max_tokens=512,
            model=model_id,
        )
        break

    return {"answer": answer, "chunks": chunks}
