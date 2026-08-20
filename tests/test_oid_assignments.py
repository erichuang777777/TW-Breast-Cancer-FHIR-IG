import configparser
import re
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "ig" / "sushi-config.yaml"
OIDS = ROOT / "ig" / "oids.ini"
IGNORED_WARNINGS = ROOT / "ig" / "input" / "ignoreWarnings.txt"
CANONICAL = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG"
OID_ROOT = f"2.25.{uuid.uuid5(uuid.NAMESPACE_URL, CANONICAL).int}"


def load_oids():
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(OIDS, encoding="utf-8-sig")
    return parser


def test_auto_oid_root_is_deterministically_derived_from_the_canonical():
    config = CONFIG.read_text(encoding="utf-8")
    assert f"canonical: {CANONICAL}" in config
    assert f"auto-oid-root: {OID_ROOT}" in config
    assert OID_ROOT == "2.25.37863882866210842446634463448013114893"


def test_committed_oid_register_is_complete_unique_and_under_the_root():
    parser = load_oids()
    declared_counts = {kind: int(count) for kind, count in parser["Key"].items()}
    assert declared_counts == {
        "NamingSystem": 2,
        "CodeSystem": 60,
        "ValueSet": 90,
        "ConceptMap": 50,
        "StructureDefinition": 46,
        "CapabilityStatement": 1,
        "Library": 1,
        "Measure": 20,
        "Questionnaire": 1,
    }

    assignments = []
    for resource_type, expected_count in declared_counts.items():
        section = dict(parser[resource_type])
        assert len(section) == expected_count
        assignments.extend(section.values())

    assert len(assignments) == 271
    assert len(set(assignments)) == len(assignments)
    assert all(
        re.fullmatch(re.escape(OID_ROOT) + r"\.\d+\.\d+", oid)
        for oid in assignments
    )


def test_retired_tcr_concept_map_oids_are_reserved_not_recycled():
    parser = load_oids()
    concept_maps = dict(parser["ConceptMap"])
    assert not list((ROOT / "ig" / "input" / "resources").glob(
        "ConceptMap-tcr-breast-*-to-standard.json"
    ))
    assert len([name for name in concept_maps if name.startswith("tcr-breast-")]) == 48
    assert {"QBCGenderToFHIRAdministrativeGender", "QBCLateralityToSNOMEDCT"} \
        <= set(concept_maps)


def test_oid_warnings_are_not_suppressed():
    ignored = IGNORED_WARNINGS.read_text(encoding="utf-8")
    assert "OID assigned" not in ignored
