"""Pass 3: citation_check operator at post_gen_refine stage.

Runs a Vertex Haiku call against (answer, chunks) to verify each claim in the
answer maps to actual chunk content. Flags hallucinations.

Opt-in per defender via params.enabled=true.
"""

from __future__ import annotations

import json
import logging


log = logging.getLogger(__name__)


def build_citation_check_prompt(answer: str, chunks: list) -> str:
    chunk_texts = "\n\n".join(
        f"[CHUNK {i}] {c.get('text', '') if isinstance(c, dict) else getattr(c, 'text', str(c))}"
        for i, c in enumerate(chunks[:10])
    )
    return f"""You are a citation verifier for a RAG answer.

Read the answer and the retrieved chunks. For each substantive claim in the answer,
verify it is supported by at least one chunk. Flag any claim that has no chunk support.

# Answer
{answer}

# Chunks
{chunk_texts}

# Task
Output a JSON object with two keys:
- passed: true if every substantive claim has chunk support; false otherwise
- issues: array of strings, one per unsupported claim (empty array if passed)

Respond with the JSON object only.
"""


def parse_citation_check_response(response: str) -> dict:
    """Parse response. Returns {passed: bool, issues: list[str]}. Invalid → passed=True."""
    text = response.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
        text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {"passed": True, "issues": []}
    if not isinstance(parsed, dict):
        return {"passed": True, "issues": []}
    if "passed" not in parsed:
        return {"passed": True, "issues": []}
    issues = parsed.get("issues", [])
    if not isinstance(issues, list):
        issues = []
    return {"passed": bool(parsed["passed"]), "issues": issues}


async def check_citations(answer: str, chunks: list) -> dict:
    """Vertex Haiku citation check. Returns {passed: bool, issues: list[str]}."""
    from darwin.llm.vertex import is_vertex_configured, vertex_complete

    if not is_vertex_configured():
        return {"passed": True, "issues": []}

    try:
        response = await vertex_complete(
            system="You verify RAG answer citations against retrieved chunks. Reply with JSON only.",
            user=build_citation_check_prompt(answer, chunks),
            max_tokens=512,
            thinking=False,
        )
    except Exception as exc:
        log.warning("vertex_complete failed for citation_check: %s", exc)
        return {"passed": True, "issues": []}

    return parse_citation_check_response(response)
