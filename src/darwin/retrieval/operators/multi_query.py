"""Pass 3: multi_query operator at chunk stage — HyDE-style query expansion.

Generates up to MAX_VARIANTS query variants via Vertex Haiku rewriting. Returns
a list of queries (original + variants).

PASS 3 SCOPE LIMITATION: This operator is registered + unit-tested, but
pipeline_runner.execute_pipeline does NOT yet iterate downstream subtrees per
variant. Full end-to-end multi-query -> multi-retrieve -> RRF fuse requires
execute_pipeline to detect list-valued outputs and run downstream nodes N
times with each variant. That's a Pass 4 follow-up. For Pass 3, the operator
exists for explicit use by code that wants to call generate_query_variants()
directly; DAG-driven invocation produces a list that the next node sees but
doesn't auto-fan-out.

The other Pass 3 novel operators (topic_summary, citation_check) integrate
cleanly with the existing single-context DAG walk because they don't change
the cardinality of the downstream subtree.
"""

from __future__ import annotations

import json
import logging


log = logging.getLogger(__name__)


MAX_VARIANTS: int = 5


def build_multi_query_prompt(query: str) -> str:
    return f"""You are a query-expansion module for a RAG system.

Generate UP TO 5 alternative phrasings of the user query below. Each variant must:
- Preserve the original intent (don't change topic)
- Use different wording, structure, or domain vocabulary
- Be retrievable on its own (a full question or statement)

Output a JSON object with one key: "variants" -> array of strings.

# Original query
{query}

Respond with JSON only, no surrounding text or markdown.
"""


def parse_variants_response(response: str, *, original: str) -> list[str]:
    """Parse variants. Always returns [original] + valid variants (capped)."""
    text = response.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return [original]
    if not isinstance(parsed, dict):
        return [original]
    variants = parsed.get("variants")
    if not isinstance(variants, list):
        return [original]
    valid = [v for v in variants if isinstance(v, str) and v.strip()][:MAX_VARIANTS]
    return [original] + valid


async def generate_query_variants(query: str) -> list[str]:
    """Vertex Haiku call to generate up to 5 query variants. Falls back to [query] on failure."""
    from darwin.llm.vertex import is_vertex_configured, vertex_complete

    if not is_vertex_configured():
        return [query]

    try:
        response = await vertex_complete(
            system="You are a query expansion module. Reply with JSON only.",
            user=build_multi_query_prompt(query),
            max_tokens=256,
            thinking=False,
        )
    except Exception as exc:
        log.warning("vertex_complete failed for multi_query: %s", exc)
        return [query]

    return parse_variants_response(response, original=query)
