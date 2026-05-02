"""Shared AnthropicVertex client + extended-thinking helpers.

All Claude calls in Darwin go through here. Defaults to Opus 4.6 with extended
thinking enabled (`thinking={"type": "enabled", "budget_tokens": ...}`). The
budget is the upper bound on thinking tokens; the model uses what it needs,
which gives the "adaptive" behaviour.

Env vars:
    ANTHROPIC_VERTEX_PROJECT_ID  (default: grantx-fleet)
    CLOUD_ML_REGION              (default: global)
    DARWIN_CLAUDE_MODEL          (default: claude-opus-4-6)
    DARWIN_THINKING_BUDGET       (default: 1024)
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Optional


DEFAULT_MODEL = "claude-opus-4-6"
DEFAULT_THINKING_BUDGET = 1024
DEFAULT_PROJECT = "grantx-fleet"
DEFAULT_REGION = "global"


_client = None


def _get_project() -> str:
    return os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID") or DEFAULT_PROJECT


def _get_region() -> str:
    return os.environ.get("CLOUD_ML_REGION") or DEFAULT_REGION


def is_vertex_configured() -> bool:
    """True if either ADC is available or VERTEX env vars are set."""

    if os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID"):
        return True
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        return True
    # Treat presence of `gcloud` ADC files as a positive signal.
    home = os.path.expanduser("~")
    return os.path.exists(os.path.join(home, ".config", "gcloud", "application_default_credentials.json"))


def get_vertex_client():
    """Lazy singleton AnthropicVertex client."""

    global _client
    if _client is not None:
        return _client
    try:
        from anthropic import AnthropicVertex
    except ImportError as exc:
        raise RuntimeError(
            "Install anthropic[vertex] to use the Vertex Claude client."
        ) from exc
    _client = AnthropicVertex(project_id=_get_project(), region=_get_region())
    return _client


def extract_text(message) -> str:
    """Concatenate text blocks from an Anthropic Message, ignoring thinking blocks."""

    parts: list[str] = []
    for block in message.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            parts.append(block.text)
    return "".join(parts)


def _budget_tokens() -> int:
    raw = os.environ.get("DARWIN_THINKING_BUDGET")
    if not raw:
        return DEFAULT_THINKING_BUDGET
    try:
        return max(64, int(raw))
    except ValueError:
        return DEFAULT_THINKING_BUDGET


def _model() -> str:
    return os.environ.get("DARWIN_CLAUDE_MODEL") or DEFAULT_MODEL


async def vertex_complete(
    *,
    system: Optional[str],
    user: str,
    max_tokens: int = 2048,
    thinking: bool = True,
    thinking_budget: Optional[int] = None,
) -> str:
    """Async wrapper for a single-turn Claude completion via Vertex.

    Returns the concatenated text content. Extended thinking is on by default;
    pass `thinking=False` to disable. When thinking is enabled, the API
    requires temperature=1, which we set automatically and silently — callers
    don't need to think about it.
    """

    if not is_vertex_configured():
        raise RuntimeError(
            "Vertex AI not configured. Set ANTHROPIC_VERTEX_PROJECT_ID or "
            "ensure ADC is available (gcloud auth application-default login)."
        )

    request: dict[str, Any] = {
        "model": _model(),
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user}],
    }
    if system is not None:
        request["system"] = system
    if thinking:
        # Adaptive thinking: the model self-determines the thinking budget
        # based on task complexity. No budget_tokens field — adaptive mode
        # rejects it.
        request["thinking"] = {"type": "adaptive"}
        request["temperature"] = 1.0
    else:
        request["temperature"] = 0.0

    def _call() -> str:
        client = get_vertex_client()
        message = client.messages.create(**request)
        return extract_text(message)

    return await asyncio.to_thread(_call)
