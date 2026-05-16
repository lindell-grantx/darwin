"""GEPA-style reflective mutation: LLM reads execution trace, proposes targeted gene edit.

Reference: GEPA (arXiv:2507.19457). Beats GRPO by 6-19pp using 35x fewer rollouts;
the key insight is that textual reflection on traces is a denser learning signal
than scalar rewards.

This module implements:
- build_mutation_prompt: serialize (genome, trace, judge feedback) into LLM prompt
- parse_edit_response: extract a single-gene-edit JSON from the LLM's response
- apply_edit: clamp + apply the proposed edit to a genome
- reflect_and_mutate: the integrated async entry point used by birth_offspring
"""

from __future__ import annotations

import json
import logging
import random
from typing import Any

from darwin.db.schemas import Genome


log = logging.getLogger(__name__)


def build_mutation_prompt(genome: Genome, trace: dict, judge: dict) -> str:
    """Serialize the parent + trace + judge feedback into a mutation prompt.

    The LLM is asked to propose ONE single-gene edit with rationale.
    """
    genome_dict = {
        "retrieval_genes": genome.retrieval_genes.model_dump(),
        "coordination_genes": genome.coordination_genes.model_dump(),
        "generation_genes": genome.generation_genes.model_dump(),
    }
    return f"""You are a mutation operator for an evolutionary RAG system.

The parent genome below was evaluated and produced a poor result. Read the trace
and judge feedback, then propose ONE single-gene edit that would likely improve
fitness next generation.

# Parent genome
```json
{json.dumps(genome_dict, indent=2)}
```

# Execution trace
```json
{json.dumps(trace, indent=2, default=str)}
```

# Judge feedback (rubric vector + rationale)
```json
{json.dumps(judge, indent=2, default=str)}
```

# Task
Identify the single gene whose change is most likely to improve the lowest-scoring
predicate in the judge feedback. Output a JSON object with:

- gene_path: dot-separated path like "retrieval_genes.confidence_threshold"
- new_value: the proposed new value (number, string, list, or boolean as appropriate)
- rationale: 1-2 sentences explaining why this edit should help

Respond with the JSON object only, no surrounding text or markdown.
"""


def parse_edit_response(response: str) -> dict | None:
    """Extract the edit JSON. Tolerates code fences. Returns None on parse failure."""
    text = response.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
        text = text.strip()
    try:
        edit = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(edit, dict):
        return None
    if not all(k in edit for k in ("gene_path", "new_value", "rationale")):
        return None
    return edit


def apply_edit(genome: Genome, edit: dict) -> Genome:
    """Apply a single-gene edit. Clamps to field bounds; preserves other genes.

    On invalid path or type mismatch, returns the genome unchanged with a warning log.
    """
    path = edit["gene_path"]
    value = edit["new_value"]
    parts = path.split(".")
    if len(parts) != 2:
        log.warning("invalid gene_path %r (expected layer.field)", path)
        return genome

    layer_name, field_name = parts
    if not hasattr(genome, layer_name):
        log.warning("unknown gene layer %r", layer_name)
        return genome

    layer = getattr(genome, layer_name)
    if not hasattr(layer, field_name):
        log.warning("unknown field %r in layer %r", field_name, layer_name)
        return genome

    layer_dict = layer.model_dump()
    layer_dict[field_name] = value
    try:
        new_layer = layer.__class__.model_validate(layer_dict)
    except Exception as exc:
        log.warning("invalid edit %r: %s — clamping or skipping", edit, exc)
        from pydantic_core import ValidationError
        if isinstance(exc, ValidationError):
            for err in exc.errors():
                if err.get("type") in ("greater_than", "greater_than_equal"):
                    bound = err.get("ctx", {}).get("ge") or err.get("ctx", {}).get("gt") or 0.0
                    layer_dict[field_name] = bound
                elif err.get("type") in ("less_than", "less_than_equal"):
                    bound = err.get("ctx", {}).get("le") or err.get("ctx", {}).get("lt") or 1.0
                    layer_dict[field_name] = bound
            try:
                new_layer = layer.__class__.model_validate(layer_dict)
            except Exception:
                return genome
        else:
            return genome

    update = {layer_name: new_layer}
    return genome.model_copy(update=update)


async def reflect_and_mutate(
    parent: Genome,
    trace: dict,
    judge: dict,
    *,
    rng: random.Random,
    fallback_rate: float = 0.1,
    model: str | None = None,
) -> tuple[Genome, dict[str, Any]]:
    """Returns (mutated_genome, mutation_metadata).

    Falls back to mechanical mutation on any LLM/parse/apply failure
    so evolution doesn't stall.

    `model` overrides the Vertex model for this call (e.g., "claude-opus-4-7"
    on plateau triggers); None uses the configured default.
    """
    from darwin.llm.vertex import vertex_complete, is_vertex_configured
    from darwin.genome.mutate import mutate

    model_label = model if model is not None else "vertex-default"

    if not is_vertex_configured():
        return mutate(parent, fallback_rate, rng=rng), {
            "mutation_type": "mechanical_fallback",
            "target_gene": None,
            "rationale": "vertex_not_configured",
            "model_used": None,
        }

    prompt = build_mutation_prompt(parent, trace, judge)
    try:
        response = await vertex_complete(
            system="You are a mutation operator. Reply with JSON only.",
            user=prompt,
            max_tokens=512,
            thinking=False,
            model=model,
        )
    except Exception as exc:
        log.warning("reflective mutation Vertex call failed: %s", exc)
        return mutate(parent, fallback_rate, rng=rng), {
            "mutation_type": "mechanical_fallback",
            "target_gene": None,
            "rationale": f"vertex_call_failed: {exc}",
            "model_used": None,
        }

    edit = parse_edit_response(response)
    if edit is None:
        return mutate(parent, fallback_rate, rng=rng), {
            "mutation_type": "mechanical_fallback",
            "target_gene": None,
            "rationale": "parse_failed",
            "model_used": model_label,
        }

    mutated = apply_edit(parent, edit)
    return mutated, {
        "mutation_type": "reflective",
        "target_gene": edit["gene_path"],
        "rationale": edit.get("rationale", ""),
        "model_used": model_label,
        "edit_diff": {edit["gene_path"]: edit["new_value"]},
    }
