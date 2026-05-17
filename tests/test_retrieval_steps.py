"""Pass 3 PR-3: discrete retrieval steps (pure-function tests)."""

import pytest


def test_step_signatures_exist():
    """All 4 steps are importable + async."""
    from darwin.retrieval.steps import (
        chunk_query,
        embed_query,
        vector_search,
        rerank_chunks,
    )
    import inspect
    for fn in (chunk_query, embed_query, vector_search, rerank_chunks):
        assert inspect.iscoroutinefunction(fn)


@pytest.mark.asyncio
async def test_chunk_query_is_noop_passthrough():
    """Pass 3 ships chunk_query as a no-op placeholder for future query rewriting."""
    from darwin.retrieval.steps import chunk_query
    result = await chunk_query("how do I create a vector index?", {})
    assert result == "how do I create a vector index?"


def test_chunk_query_handles_dict_params():
    """params is a dict; chunk_query ignores it in Pass 3 but must accept it."""
    import asyncio
    from darwin.retrieval.steps import chunk_query
    result = asyncio.run(chunk_query("q", {"unused": "param"}))
    assert result == "q"
