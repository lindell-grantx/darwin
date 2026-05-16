"""Pass 2: MAP-Elites defender archive with Dominated-Novelty-Search fallback.

Behavior descriptors (BCs):
1. retrieval_strategy_class: vector / hybrid / agentic
2. response_style: from generation_genes.system_style
3. citation_density_bucket: low / medium / high

Decision criterion (per spec):
- If end of week 6 sees >40% of cells populated → MAP-Elites
- Else fall back to Dominated Novelty Search (fitness penalized by density)
"""

from __future__ import annotations

from typing import Any

from darwin.db.schemas import Genome


BC_DIMS: tuple[str, ...] = (
    "retrieval_strategy_class",
    "response_style",
    "citation_density_bucket",
)


def behavior_descriptor(genome: Genome) -> tuple[str, str, str]:
    """Compute the 3D BC for a defender genome."""
    retrieval_class = _retrieval_strategy_class(genome)
    response_style = genome.generation_genes.system_style
    citation_density = _citation_density_bucket(genome)
    return (retrieval_class, response_style, citation_density)


def _retrieval_strategy_class(g: Genome) -> str:
    if g.pipeline is not None:
        stages_present = {n.stage for n in g.pipeline.nodes}
        if "fuse" in stages_present:
            return "hybrid"
        if "post_gen_refine" in stages_present:
            return "agentic"
        return "vector"
    mode = g.retrieval_genes.retrieval_mode_router
    if mode == "agentic":
        return "agentic"
    if mode == "iterative":
        return "hybrid"
    return "vector"


def _citation_density_bucket(g: Genome) -> str:
    t = g.retrieval_genes.confidence_threshold
    if t < 0.3:
        return "high"
    if t < 0.7:
        return "medium"
    return "low"


def map_elites_admit(
    cells: dict,
    cell_key,
    candidate: dict[str, Any],
) -> bool:
    """Admit candidate iff higher fitness or empty cell. Mutates cells in place."""
    incumbent = cells.get(cell_key)
    if incumbent is None:
        cells[cell_key] = candidate
        return True
    if candidate["composite_fitness"] > incumbent["composite_fitness"]:
        cells[cell_key] = candidate
        return True
    return False


def dns_score(base_fitness: float, *, neighborhood_density: int) -> float:
    """DNS effective fitness: base - 0.05 * density. Used as fallback when MAP-Elites too sparse."""
    return base_fitness - 0.05 * neighborhood_density
