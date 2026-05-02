"""Rich terminal dashboard for Darwin's evolution demo.

Run live mode with a configured backend or database:
    python -m darwin.demo.narrate --live

Run a deterministic preview without external services:
    python -m darwin.demo.narrate --preview
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import request


BLOCKS = "▁▂▃▄▅▆▇█"
DEFAULT_QUERY = "How do I tune Atlas Vector Search for high recall?"


@dataclass(frozen=True)
class DemoState:
    generation: int
    alive_count: int
    fitness_series: list[dict[str, float]]
    champion: dict[str, Any]
    ancestor: dict[str, Any]
    query_text: str
    answer: str
    agents: list[dict[str, str]]


def fitness_sparkline(series: list[float]) -> str:
    """Map values in [0.0, 1.0] to sparkline block characters."""
    if not series:
        return ""
    return "".join(BLOCKS[min(max(int(value * len(BLOCKS)), 0), len(BLOCKS) - 1)] for value in series)


def _genome(
    genome_id: str,
    generation: int,
    fitness: float,
    *,
    embedding: str = "voyage-3",
    chunk_size: int = 256,
    rerank: bool = False,
    top_k: int = 5,
    protocol: str = "solo",
    deference: str = "never",
) -> dict[str, Any]:
    return {
        "id": genome_id,
        "generation": generation,
        "retrieval_genes": {
            "embedding": embedding,
            "chunk_size": chunk_size,
            "rerank": rerank,
            "top_k": top_k,
        },
        "coordination_genes": {
            "protocol": protocol,
            "deference": deference,
        },
        "durability_genes": {
            "checkpoint_freq": "every_5",
            "recovery": "resume_checkpoint",
        },
        "fitness_composite": fitness,
    }


def deterministic_state(seed: int = 42, generations: int = 5) -> DemoState:
    """Create a deterministic story that mirrors the intended live demo."""
    rng = random.Random(seed)
    generations = max(0, generations)
    best = 0.42
    mean = 0.31
    diversity = 0.82
    series: list[dict[str, float]] = []

    for generation in range(generations + 1):
        if generation:
            best = min(0.94, best + rng.uniform(0.055, 0.095))
            mean = min(best - 0.04, mean + rng.uniform(0.045, 0.075))
            diversity = max(0.34, diversity - rng.uniform(0.035, 0.07))
        series.append(
            {
                "generation": generation,
                "best": round(best, 3),
                "mean": round(mean, 3),
                "diversity": round(diversity, 3),
            }
        )

    ancestor = _genome("g0_alpha", 0, series[0]["best"])
    if generations == 0:
        champion = ancestor
    else:
        champion = _genome(
            f"g{generations}_champ",
            generations,
            series[-1]["best"],
            embedding="voyage-4-large",
            chunk_size=512,
            rerank=True,
            top_k=10,
            protocol="consult",
            deference="on_low_confidence",
        )

    return DemoState(
        generation=generations,
        alive_count=24,
        fitness_series=series,
        champion=champion,
        ancestor=ancestor,
        query_text=DEFAULT_QUERY,
        answer=(
            "Atlas Vector Search recall improves when numCandidates is sized well "
            "above limit, embeddings match the index dimensions, and reranking is "
            "used on the candidate set for final ordering."
        ),
        agents=[
            {"name": "alpha", "status": "retrieving", "result": "ok"},
            {"name": "beta", "status": "reranking", "result": "ok"},
            {"name": "gamma", "status": "consulting", "result": "ok"},
        ],
    )


def _response_json(url: str, *, timeout: int = 10) -> dict[str, Any]:
    with request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_json(url: str, payload: dict[str, Any], *, timeout: int = 30) -> dict[str, Any]:
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_state_from_api(base_url: str, query_text: str = DEFAULT_QUERY) -> DemoState:
    """Read demo state from the TypeScript API if it is running."""
    base = base_url.rstrip("/")
    population = _response_json(f"{base}/population")
    curve = _response_json(f"{base}/fitness-curve")
    query = _post_json(f"{base}/query", {"text": query_text})

    genomes = population.get("genomes") or []
    champion = query.get("winning_genome") or (genomes[-1] if genomes else {})
    series = curve.get("series") or curve.get("points") or []
    if not series:
        series = deterministic_state().fitness_series

    generation = int(population.get("current_generation") or champion.get("generation") or series[-1]["generation"])
    ancestor = genomes[0] if genomes else deterministic_state().ancestor
    answer = query.get("answer") or "Backend accepted the query but no winning answer is available yet."

    return DemoState(
        generation=generation,
        alive_count=int(population.get("alive_count") or len(genomes) or 0),
        fitness_series=series,
        champion=champion or deterministic_state().champion,
        ancestor=ancestor,
        query_text=query_text,
        answer=answer,
        agents=[
            {"name": result.get("genome_id", "genome"), "status": "evaluated", "result": "ok"}
            for result in query.get("all_genome_results", [])[:3]
        ]
        or deterministic_state().agents,
    )


async def fetch_state_from_mongo(mongo_uri: str, db_name: str = "darwin") -> DemoState:
    """Read the latest demo state directly from MongoDB when Motor is installed."""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
    except ModuleNotFoundError as exc:
        raise RuntimeError("Motor is required for --mongo live mode") from exc

    client = AsyncIOMotorClient(mongo_uri)
    try:
        db = client[db_name]
        generations = await db.generations.find({}).sort("generation", 1).to_list(length=50)
        genomes = await db.genomes.find({"status": {"$ne": "retired"}}).sort("fitness.composite", -1).to_list(length=24)

        if not generations or not genomes:
            return deterministic_state()

        series = [
            {
                "generation": item.get("generation", index),
                "best": item.get("best_fitness", 0.0),
                "mean": item.get("mean_fitness", 0.0),
                "diversity": item.get("diversity_index", 0.0),
            }
            for index, item in enumerate(generations)
        ]
        champion = genomes[0]
        ancestor = genomes[-1]
        return DemoState(
            generation=int(series[-1]["generation"]),
            alive_count=len(genomes),
            fitness_series=series,
            champion=champion,
            ancestor=ancestor,
            query_text=DEFAULT_QUERY,
            answer="Live MongoDB state loaded. Submit a query through the API for generated answers.",
            agents=deterministic_state().agents,
        )
    finally:
        client.close()


def make_layout() -> Any:
    """Create the Rich layout object."""
    from rich.layout import Layout

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="query", size=12),
    )
    layout["body"].split_row(Layout(name="curve"), Layout(name="champion"))
    return layout


def _gene_rows(genome: dict[str, Any], ancestor: dict[str, Any]) -> list[tuple[str, Any, Any]]:
    rows: list[tuple[str, Any, Any]] = []
    for group in ("retrieval_genes", "coordination_genes", "durability_genes"):
        genes = genome.get(group, {})
        old_genes = ancestor.get(group, {})
        if isinstance(genes, dict):
            for key, value in genes.items():
                old_value = old_genes.get(key) if isinstance(old_genes, dict) else None
                rows.append((f"{group}.{key}", value, old_value))
    return rows


def _gene_explanation(path: str) -> str:
    explanations = {
        "retrieval_genes.embedding": "Embedding model used to turn text into vectors for search.",
        "retrieval_genes.chunk_size": "Evidence chunk size; larger chunks preserve more context.",
        "retrieval_genes.rerank": "Whether retrieved chunks are reordered by a stronger relevance model.",
        "retrieval_genes.top_k": "How many candidate chunks are considered for the answer.",
        "coordination_genes.protocol": "How agents collaborate: solo, voting, consult, or debate.",
        "coordination_genes.deference": "When an agent should yield to a stronger specialist.",
        "durability_genes.checkpoint_freq": "How often long-running state is saved.",
        "durability_genes.recovery": "How the system resumes after interruption.",
    }
    return explanations.get(path, "Genome setting used by the retrieval strategy.")


def _best_trend_explanation(series: list[float]) -> str:
    if len(series) <= 1:
        return "Meaning: this is the baseline before evolution has produced children."
    return "Meaning: the best strategy in the population improved over time."


def _mean_trend_explanation(series: list[float]) -> str:
    if len(series) <= 1:
        return "Meaning: this is the starting population average."
    return "Meaning: the overall population also improved, not only one lucky genome."


def render_rich_layout(state: DemoState) -> Any:
    """Render the full Rich dashboard."""
    from rich import box
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    layout = make_layout()
    best = [float(point.get("best", 0.0)) for point in state.fitness_series]
    mean = [float(point.get("mean", 0.0)) for point in state.fitness_series]

    layout["header"].update(
        Panel(
            "DARWIN - Evolutionary Adaptive Retrieval\n"
            f"Generation {state.generation}: {state.alive_count} active genomes are competing. "
            "Higher fitness means better answer quality.",
            style="bold cyan",
        )
    )

    curve = Table.grid(expand=True)
    curve.add_column(ratio=1)
    curve.add_row("Fitness is a 0-1 score from the judge. Best = champion score; mean = population average.")
    curve.add_row(f"best  {fitness_sparkline(best)}  {best[0]:.2f} -> {best[-1]:.2f}")
    curve.add_row(f"mean  {fitness_sparkline(mean)}  {mean[0]:.2f} -> {mean[-1]:.2f}")
    curve.add_row(_best_trend_explanation(best))
    curve.add_row(_mean_trend_explanation(mean))
    curve.add_row("")
    for point in state.fitness_series:
        curve.add_row(
            f"Gen {int(point.get('generation', 0)):>2}: "
            f"best={float(point.get('best', 0.0)):.2f} "
            f"mean={float(point.get('mean', 0.0)):.2f} "
            f"diversity={float(point.get('diversity', 0.0)):.2f}"
        )
    layout["curve"].update(Panel(curve, title="Fitness Over Generations", border_style="green"))

    champion_table = Table(box=box.SIMPLE, expand=True)
    champion_table.add_column("Gene")
    champion_table.add_column("Current")
    champion_table.add_column("Gen 0")
    champion_table.add_column("Why it matters")
    for path, value, old_value in _gene_rows(state.champion, state.ancestor):
        changed = old_value is not None and value != old_value
        champion_table.add_row(
            path,
            Text(str(value), style="bold yellow" if changed else ""),
            Text(str(old_value), style="dim" if changed else ""),
            _gene_explanation(path),
        )
    lineage = " <- ".join(f"g{i}" for i in range(state.generation, -1, -1))
    champion_panel = Table.grid(expand=True)
    champion_panel.add_row(
        f"{state.champion.get('id', 'unknown')} "
        f"(fitness {float(state.champion.get('fitness_composite', 0.0)):.2f})"
    )
    champion_panel.add_row("Changed values show what evolution selected compared with the gen-0 baseline.")
    champion_panel.add_row(champion_table)
    champion_panel.add_row(f"Lineage: {lineage}")
    layout["champion"].update(Panel(champion_panel, title="Champion Genome", border_style="magenta"))

    query_table = Table.grid(expand=True)
    query_table.add_row("The same user query is evaluated by multiple genome strategies.")
    query_table.add_row(f"> {state.query_text}")
    query_table.add_row("")
    for agent in state.agents:
        query_table.add_row(f"{agent['name']} {agent['status']}... {agent['result']}")
    query_table.add_row("")
    query_table.add_row(
        f"WINNER: {state.champion.get('id', 'unknown')} "
        f"(fitness {float(state.champion.get('fitness_composite', 0.0)):.2f})"
    )
    query_table.add_row("The winner is the genome whose retrieval and coordination strategy scored highest.")
    query_table.add_row(state.answer)
    layout["query"].update(Panel(query_table, title="Live Query", border_style="cyan"))

    return layout


def render_plain(state: DemoState) -> str:
    """Plain-text fallback for environments without Rich installed."""
    best = [float(point.get("best", 0.0)) for point in state.fitness_series]
    mean = [float(point.get("mean", 0.0)) for point in state.fitness_series]
    rows = [
        "DARWIN TERMINAL DEMO - Evolutionary Adaptive Retrieval",
        "Goal: show a population of retrieval strategies improving through selection.",
        "",
        "1) POPULATION STATE",
        f"- Current generation: {state.generation}",
        f"- Active genomes: {state.alive_count}",
        "- Meaning: each genome is one retrieval + coordination strategy still competing.",
        "",
        "2) FITNESS OVER GENERATIONS",
        "- Fitness is a 0-1 judge score. Higher means the answer was more relevant, accurate, and complete.",
        f"- Best fitness  {fitness_sparkline(best)}  {best[0]:.2f} -> {best[-1]:.2f}",
        f"- {_best_trend_explanation(best)}",
        f"- Mean fitness  {fitness_sparkline(mean)}  {mean[0]:.2f} -> {mean[-1]:.2f}",
        f"- {_mean_trend_explanation(mean)}",
        "",
        "3) CHAMPION GENOME",
        f"- Winner: {state.champion.get('id')} with fitness={float(state.champion.get('fitness_composite', 0.0)):.2f}",
        "- Meaning: this is the current strongest retrieval strategy selected by the system.",
        "- Changed values show what evolution selected compared with the generation-0 baseline.",
    ]
    for path, value, old_value in _gene_rows(state.champion, state.ancestor):
        suffix = f" (was {old_value})" if old_value is not None and value != old_value else ""
        rows.append(f"- {path}: {value}{suffix}")
        rows.append(f"  Why it matters: {_gene_explanation(path)}")
    rows.extend(
        [
            "",
            "4) LIVE QUERY TOURNAMENT",
            "- Meaning: multiple genome strategies evaluate the same query; the highest scoring one wins.",
            f"> {state.query_text}",
        ]
    )
    for agent in state.agents:
        rows.append(f"- {agent['name']}: {agent['status']}... {agent['result']}")
    rows.extend(
        [
            "",
            "5) WINNING ANSWER",
            f"- Winning genome: {state.champion.get('id')}",
            f"- Winning fitness: {float(state.champion.get('fitness_composite', 0.0)):.2f}",
            "- Meaning: this answer came from the strategy Darwin currently trusts most.",
            state.answer,
        ]
    )
    return "\n".join(rows)


async def live_loop(args: argparse.Namespace) -> None:
    """Run a reactive live display from API, MongoDB, or deterministic preview data."""
    try:
        from rich.live import Live
        from rich.console import Console
    except ModuleNotFoundError:
        state = await _state_for_args(args)
        print(render_plain(state))
        return

    console = Console()
    state = await _state_for_args(args)
    with Live(render_rich_layout(state), refresh_per_second=4, screen=args.screen, console=console) as live:
        iterations = 0
        while args.once or iterations < args.max_updates:
            state = await _state_for_args(args)
            live.update(render_rich_layout(state))
            iterations += 1
            if args.once:
                break
            await asyncio.sleep(args.interval)


async def _state_for_args(args: argparse.Namespace) -> DemoState:
    if args.api_url:
        return fetch_state_from_api(args.api_url, args.query)
    if args.mongo_uri:
        return await fetch_state_from_mongo(args.mongo_uri, args.db_name)
    return deterministic_state(args.seed, args.generations)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Darwin Rich terminal dashboard")
    parser.add_argument("--live", action="store_true", help="Run a live dashboard loop")
    parser.add_argument("--preview", action="store_true", help="Render deterministic preview data")
    parser.add_argument("--api-url", default=os.environ.get("DARWIN_API_URL"))
    parser.add_argument("--mongo-uri", default=os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URI"))
    parser.add_argument("--db-name", default=os.environ.get("DB_NAME", "darwin"))
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--generations", type=int, default=5)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--max-updates", type=int, default=1)
    parser.add_argument("--once", action="store_true", help="Render one update and exit")
    parser.add_argument("--screen", action="store_true", help="Use Rich alternate screen mode")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if not args.live and not args.preview:
        args.preview = True
        args.once = True
    asyncio.run(live_loop(args))


if __name__ == "__main__":
    main()
