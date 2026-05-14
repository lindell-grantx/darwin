"""Pass 2 PR-2: Attacker schema gains evolution fields + AttackerArchive collection."""

from darwin.db.schemas import (
    Attacker,
    AttackerArchive,
    COLLECTION_ATTACKER_ARCHIVE,
)


def test_attacker_has_generation_default_zero():
    a = Attacker(
        attack_vector_type="corpus_poison",
        target_query_class=("mongodb", "vector-search"),
        payload="x",
    )
    assert a.generation == 0


def test_attacker_has_parent_ids_default_empty():
    a = Attacker(
        attack_vector_type="corpus_poison",
        target_query_class=("mongodb", "vector-search"),
        payload="x",
    )
    assert a.parent_ids == []


def test_attacker_has_composite_fitness_default_zero():
    a = Attacker(
        attack_vector_type="corpus_poison",
        target_query_class=("mongodb", "vector-search"),
        payload="x",
    )
    assert a.composite_fitness == 0.0


def test_attacker_archive_minimal():
    arch = AttackerArchive(
        cell_key=("jailbreak", "instruction_override"),
        attacker_ids=["a", "b", "c"],
    )
    assert arch.cell_key == ("jailbreak", "instruction_override")
    assert arch.attacker_ids == ["a", "b", "c"]


def test_collection_constant():
    assert COLLECTION_ATTACKER_ARCHIVE == "attacker_archive"
