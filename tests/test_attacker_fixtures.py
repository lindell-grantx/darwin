"""v2 MVP: validate the 10 hand-curated attackers."""

from collections import Counter

from darwin.attacker.fixtures import MVP_ATTACKERS


def test_exactly_ten_attackers():
    assert len(MVP_ATTACKERS) == 10


def test_five_corpus_poison_five_prompt_injection():
    counts = Counter(a.attack_vector_type for a in MVP_ATTACKERS)
    assert counts["corpus_poison"] == 5
    assert counts["prompt_injection"] == 5


def test_all_attackers_have_payload():
    for a in MVP_ATTACKERS:
        assert a.payload.strip(), f"Attacker {a.id} has empty payload"


def test_attackers_target_diverse_query_classes():
    targets = {tuple(a.target_query_class) for a in MVP_ATTACKERS}
    assert len(targets) >= 4
