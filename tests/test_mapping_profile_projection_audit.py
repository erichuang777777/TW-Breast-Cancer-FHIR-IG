import csv
from pathlib import Path

import pytest

from scripts.audit_mapping_profile_projection import (
    CANONICAL_ROOT,
    REGISTER_COLUMNS,
    read_mapping,
    read_register,
    resolve_element,
)


ROOT = Path(__file__).resolve().parents[1]
MAPPING = ROOT / "mappings" / "case-management" / "breast-common-to-case-management.csv"
REGISTER = ROOT / "mappings" / "publication" / "mapping-profile-projection-register.csv"


def profile(elements):
    return {
        "resourceType": "StructureDefinition",
        "id": "synthetic-observation",
        "url": CANONICAL_ROOT + "synthetic-observation",
        "name": "SyntheticObservation",
        "type": "Observation",
        "snapshot": {"element": elements},
    }


def test_register_covers_exact_34_facts_and_55_target_alternatives():
    mappings = read_mapping(MAPPING)
    rows = read_register(REGISTER)
    assert len(mappings) == 34
    assert len(rows) == 55
    assert tuple(rows[0]) == REGISTER_COLUMNS
    assert {row["mapping_id"] for row in rows} == {
        row["mapping_id"] for row in mappings
    }
    assert sum(row["projection_mode"] == "local-profile-element" for row in rows) == 49
    assert sum(row["projection_mode"] == "derived-rule" for row in rows) == 1
    assert sum(row["technical_status"].startswith("blocked-") for row in rows) == 5
    assert sum(bool(row["required_unit"]) for row in rows) == 3


def test_exact_thirteen_projection_gap_facts_remain_visible():
    rows = read_register(REGISTER)
    blocked = {
        row["mapping_id"] for row in rows
        if row["fact_coverage_status"] in {
            "blocked", "partial", "blocked-semantic-profile-gap"
        }
    }
    assert blocked == {
        "CM-BC-006", "CM-BC-007", "CM-BC-018", "CM-BC-020",
        "CM-BC-021", "CM-BC-022", "CM-BC-024", "CM-BC-025",
        "CM-BC-032", "CM-BC-034", "CM-BC-035", "CM-BC-037", "CM-BC-038"
    }
    assert all(
        row["blocking_issue"] for row in rows
        if row["fact_coverage_status"] in {
            "blocked", "partial", "blocked-semantic-profile-gap"
        }
    )


def test_known_resource_semantic_mismatches_do_not_masquerade_as_valid_paths():
    rows = read_register(REGISTER)
    semantic_gaps = {
        row["mapping_id"]: row for row in rows
        if row["technical_status"] == "resolved-profile-element-semantic-profile-gap"
    }
    assert set(semantic_gaps) == {
        "CM-BC-006", "CM-BC-007", "CM-BC-018", "CM-BC-020",
        "CM-BC-021", "CM-BC-022", "CM-BC-025", "CM-BC-035"
    }
    assert sum(
        row["technical_status"] == "resolved-profile-element-semantic-profile-gap"
        for row in rows
    ) == 12
    assert "does not constrain Observation.code" in semantic_gaps["CM-BC-006"]["blocking_issue"]
    assert any(
        row["mapping_id"] == "CM-BC-020"
        and "order/request" in row["blocking_issue"]
        for row in rows
    )
    assert "intended performer" in semantic_gaps["CM-BC-025"]["blocking_issue"]


def test_prior_year_cohort_requires_more_than_an_episode_start_date():
    row = next(
        row for row in read_register(REGISTER)
        if row["mapping_id"] == "CM-BC-038"
    )
    assert row["fact_coverage_status"] == "partial"
    assert "new-diagnosis discriminator" in row["blocking_issue"]


def test_molecular_subtype_derivation_uses_current_mapping_ids_not_legacy_ids():
    mappings = {row["mapping_id"]: row for row in read_mapping(MAPPING)}
    expression = mappings["CM-BC-013"]["target_path"]
    assert expression == (
        "derived from CM-BC-008 CM-BC-009 CM-BC-010 CM-BC-011 CM-BC-012"
    )
    assert "QI-BC-" not in expression


def test_choice_type_and_unit_resolve_to_snapshot_element():
    observation = profile([
        {
            "id": "Observation.value[x]",
            "path": "Observation.value[x]",
            "type": [{"code": "Quantity"}, {"code": "CodeableConcept"}],
        }
    ])
    element, choice_type, child, unit = resolve_element(
        observation, "Observation.valueQuantity{%}"
    )
    assert element["id"] == "Observation.value[x]"
    assert choice_type == "Quantity"
    assert child == ""
    assert unit == "%"


def test_choice_type_not_allowed_by_profile_is_rejected():
    observation = profile([
        {
            "id": "Observation.value[x]",
            "path": "Observation.value[x]",
            "type": [{"code": "CodeableConcept"}],
        }
    ])
    with pytest.raises(ValueError, match="does not allow selected type Quantity"):
        resolve_element(observation, "Observation.valueQuantity")


def test_unresolved_named_slice_is_rejected_instead_of_matching_base_extension():
    condition = profile([
        {"id": "Condition.extension", "path": "Condition.extension"}
    ])
    condition["type"] = "Condition"
    with pytest.raises(ValueError, match="slice 'histology' does not exist"):
        resolve_element(condition, "Condition.extension[histology]")


def test_period_child_is_resolved_through_the_declared_datatype():
    episode = profile([
        {
            "id": "EpisodeOfCare.period",
            "path": "EpisodeOfCare.period",
            "type": [{"code": "Period"}],
        }
    ])
    episode["type"] = "EpisodeOfCare"
    element, selected_type, child, unit = resolve_element(
        episode, "EpisodeOfCare.period.start"
    )
    assert element["id"] == "EpisodeOfCare.period"
    assert selected_type == "Period"
    assert child == "start"
    assert unit == ""


def test_register_header_is_not_silently_extended_or_reduced():
    with REGISTER.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        list(reader)
    assert tuple(reader.fieldnames or ()) == REGISTER_COLUMNS
