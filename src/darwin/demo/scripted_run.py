"""Deterministic terminal run for recording Darwin's backup demo.

Run with:
    PYTHONPATH=src python -m darwin.demo.scripted_run --seed 42 --generations 5
"""

from __future__ import annotations

import argparse
import asyncio

from darwin.demo.narrate import deterministic_state, render_plain, render_rich_layout


async def scripted_run(seed: int, generations: int, delay: float, plain: bool) -> None:
    """Render a deterministic generation-by-generation story."""
    try:
        from rich.console import Console
        from rich.live import Live
    except ModuleNotFoundError:
        plain = True

    if plain:
        for generation in range(generations + 1):
            state = deterministic_state(seed=seed, generations=generation)
            print(render_plain(state))
            print("\n" + "=" * 80 + "\n")
            await asyncio.sleep(delay)
        return

    console = Console()
    initial = deterministic_state(seed=seed, generations=0)
    with Live(render_rich_layout(initial), refresh_per_second=4, screen=False, console=console) as live:
        for generation in range(generations + 1):
            state = deterministic_state(seed=seed, generations=generation)
            live.update(render_rich_layout(state))
            await asyncio.sleep(delay)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Darwin's deterministic terminal demo")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--generations", type=int, default=5)
    parser.add_argument("--delay", type=float, default=0.5)
    parser.add_argument("--plain", action="store_true", help="Force plain terminal output")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(
        scripted_run(
            seed=args.seed,
            generations=args.generations,
            delay=args.delay,
            plain=args.plain,
        )
    )


if __name__ == "__main__":
    main()
