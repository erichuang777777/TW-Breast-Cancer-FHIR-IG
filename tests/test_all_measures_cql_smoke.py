import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CQL = ROOT / "ig" / "input" / "cql" / "BreastCancerCaseManagement.cql"
MEASURES = ROOT / "ig" / "input" / "fsh" / "case-management-measures.fsh"
CASES = ROOT / "tests" / "fixtures" / "cql" / "all-measures-smoke-cases.json"
VALUE_SETS = ROOT / "tests" / "fixtures" / "cql" / "all-measures-value-sets.json"
RUNNER = ROOT / "ig" / "tools" / "cql-evaluation" / "run-all-measures-smoke.js"
WORKFLOW = ROOT / ".github" / "workflows" / "build.yml"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_smoke_fixture_is_explicitly_synthetic_and_patient_scoped():
    cases = load(CASES)
    assert len(cases) == 1
    case = cases[0]
    assert case["bundle"]["meta"]["tag"] == [
        {"system": "https://example.org/tags", "code": "synthetic"}
    ]
    patients = [
        entry["resource"]
        for entry in case["bundle"]["entry"]
        if entry["resource"]["resourceType"] == "Patient"
    ]
    assert len(patients) == 1
    assert case["expected"]["Initial Population"] is False
    assert case["expected"]["Quarterly Caseload"] is False
    assert case["expected"]["Prior Year And Current New Diagnosis Cohort"] is False


def test_smoke_terminology_covers_every_cql_valueset_without_publishing_test_codes():
    cql_text = CQL.read_text(encoding="utf-8")
    declared = set(re.findall(r'^valueset "[^"]+": \'([^\']+)\'$', cql_text, re.M))
    value_sets = load(VALUE_SETS)
    assert set(value_sets) == declared
    for versions in value_sets.values():
        assert set(versions) == {"synthetic-test-only"}
        assert versions["synthetic-test-only"]
        for code in versions["synthetic-test-only"]:
            assert code["system"].startswith("https://example.org/")


def test_runner_discovers_exactly_the_twenty_measure_artifacts_and_executes_criteria():
    measure_ids = set(re.findall(r'^\* id = "(bc-(?:qi|qr)-\d+)"$', MEASURES.read_text(encoding="utf-8"), re.M))
    assert len(measure_ids) == 20
    assert {f"bc-qi-{number:02d}" for number in range(1, 7)} <= measure_ids
    assert {f"bc-qr-{number:02d}" for number in range(1, 6)} <= measure_ids
    assert {f"bc-qr-{number}" for number in range(10, 19)} <= measure_ids

    runner = RUNNER.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "assert.equal(measures.length, 20" in runner
    assert "population.criteria.expression" in runner
    assert "stratifier.criteria.expression" in runner
    assert "exec_expression" in runner
    assert "Smoke-execute all 20 Measure criteria" in workflow
    assert "run-all-measures-smoke.js" in workflow


def test_smoke_is_not_misrepresented_as_branch_or_clinical_validation():
    runner = RUNNER.read_text(encoding="utf-8")
    cases = CASES.read_text(encoding="utf-8")
    assert "smoke" in RUNNER.name
    assert "smoke" in cases
    assert "golden" not in runner.lower()
    assert "clinical" not in runner.lower()
