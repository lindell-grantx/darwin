"""Pass 2: RainbowPlus QD archive for evolved attackers.

Cells keyed by (risk_category x attack_style). Each cell holds the highest-fitness
attacker for that behavioral niche. Prevents attacker population collapse onto
one exploit family.

Reference: RainbowPlus (arXiv:2504.15047).
"""

from __future__ import annotations

from typing import Any

from darwin.db.schemas import Attacker


RISK_CATEGORIES: tuple[str, ...] = (
    "jailbreak",
    "data_exfiltration",
    "topic_shift",
    "factual_poison",
    "denial_of_service",
)


ATTACK_STYLES: tuple[str, ...] = (
    "instruction_override",
    "role_play",
    "context_injection",
    "encoding_smuggle",
    "authority_claim",
    "fact_inversion",
)


def cell_key_for_attacker(attacker: Attacker) -> tuple[str, str]:
    """Heuristic classification of an attacker into (risk_category, attack_style)."""
    payload_lower = attacker.payload.lower()
    notes_lower = (attacker.notes or "").lower()
    text = payload_lower + " " + notes_lower

    risk = _infer_risk_category(text, attacker.attack_vector_type)
    style = _infer_attack_style(text)
    return (risk, style)


def _infer_risk_category(text: str, attack_vector_type: str) -> str:
    if "ignore" in text or "override" in text or "system" in text:
        return "jailbreak"
    if "print" in text and ("chunks" in text or "metadata" in text or "embedding" in text):
        return "data_exfiltration"
    if "deprecat" in text or "instead" in text or "recommend" in text:
        return "topic_shift"
    if attack_vector_type == "corpus_poison":
        return "factual_poison"
    return "jailbreak"


def _infer_attack_style(text: str) -> str:
    if "ignore" in text or "[system" in text or "override" in text:
        return "instruction_override"
    if "you are" in text or "pretend" in text or "act as" in text:
        return "role_play"
    if "<!--" in text or "comment" in text or "hidden" in text:
        return "context_injection"
    if "base64" in text or "rot13" in text or "encoded" in text:
        return "encoding_smuggle"
    if "important" in text or "official" in text or "authorized" in text:
        return "authority_claim"
    return "fact_inversion"


def qd_admit(
    cells: dict[tuple[str, str], dict[str, Any]],
    cell_key: tuple[str, str],
    candidate: dict[str, Any],
) -> bool:
    """Admit candidate iff higher fitness than incumbent (or empty cell). Mutates cells in place."""
    incumbent = cells.get(cell_key)
    if incumbent is None:
        cells[cell_key] = candidate
        return True
    if candidate["composite_fitness"] > incumbent["composite_fitness"]:
        cells[cell_key] = candidate
        return True
    return False
