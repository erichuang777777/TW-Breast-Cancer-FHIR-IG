import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "cql"
CASES = FIXTURES / "bc-qi-01-cases.json"
VALUE_SETS = FIXTURES / "bc-qi-01-value-sets.json"
EXPECTED_REPORT = FIXTURES / "MeasureReport-bc-qi-01-synthetic.json"
RUNNER = ROOT / "ig" / "tools" / "cql-evaluation" / "run-bc-qi-01.js"
WORKFLOW = ROOT / ".github" / "workflows" / "build.yml"
TASK_PAGE = ROOT / "ig" / "input" / "pagecontent" / "task-case-management.md"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_bc_qi_01_cases_are_explicitly_synthetic_and_have_unique_patients():
    cases = load(CASES)
    patient_ids = []
    for case in cases:
        bundle = case["bundle"]
        assert bundle["meta"]["tag"] == [
            {"system": "https://example.org/tags", "code": "synthetic"}
        ]
        patients = [
            entry["resource"]
            for entry in bundle["entry"]
            if entry["resource"]["resourceType"] == "Patient"
        ]
        assert len(patients) == 1
        patient_ids.append(patients[0]["id"])
    assert len(cases) == 5
    assert len(patient_ids) == len(set(patient_ids))


def test_bc_qi_01_expected_cases_cover_the_population_boundaries():
    cases = {case["id"]: case for case in load(CASES)}
    expected = {case_id: case["expected"] for case_id, case in cases.items()}
    assert expected["eligible-treated"] == {
        "Initial Population": True,
        "Denominator 1": True,
        "Denominator 1 Exclusion": False,
        "Numerator 1": True,
    }
    assert expected["eligible-untreated"]["Numerator 1"] is False
    assert expected["low-er-excluded"]["Denominator 1 Exclusion"] is True
    assert expected["missing-er-excluded"]["Denominator 1 Exclusion"] is True
    assert expected["stage-iv-not-denominator"]["Denominator 1"] is False
    assert expected["stage-iv-not-denominator"]["Denominator 1 Exclusion"] is True

    treated_types = {
        entry["resource"]["resourceType"]
        for entry in cases["eligible-treated"]["bundle"]["entry"]
    }
    untreated_types = {
        entry["resource"]["resourceType"]
        for entry in cases["eligible-untreated"]["bundle"]["entry"]
    }
    assert "MedicationAdministration" in treated_types
    assert "MedicationRequest" not in treated_types
    assert "MedicationRequest" in untreated_types
    assert "MedicationAdministration" not in untreated_types


def test_test_only_terminology_cannot_be_mistaken_for_published_codes():
    value_sets = load(VALUE_SETS)
    assert value_sets
    for versions in value_sets.values():
        assert set(versions) == {"synthetic-test-only"}
        for code in versions["synthetic-test-only"]:
            assert code["system"].startswith("https://example.org/")


def test_expected_measure_report_matches_the_case_counts():
    cases = load(CASES)
    results = [case["expected"] for case in cases]
    expected_counts = {
        "initial-population": sum(result["Initial Population"] for result in results),
        "denominator": sum(result["Denominator 1"] for result in results),
        "denominator-exclusion": sum(
            result["Denominator 1"] and result["Denominator 1 Exclusion"]
            for result in results
        ),
        "numerator": sum(
            result["Denominator 1"]
            and not result["Denominator 1 Exclusion"]
            and result["Numerator 1"]
            for result in results
        ),
    }
    report = load(EXPECTED_REPORT)
    actual_counts = {
        population["code"]["coding"][0]["code"]: population["count"]
        for population in report["group"][0]["population"]
    }
    assert actual_counts == expected_counts


def test_ci_executes_the_elm_instead_of_only_translating_it():
    runner = RUNNER.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "exec_expression" in runner
    assert "cql-exec-fhir" in runner
    assert "Execute bc-qi-01 synthetic CQL cases" in workflow
    assert "run-bc-qi-01.js" in workflow


def test_published_task_status_matches_executable_and_data_evidence_boundaries():
    page = TASK_PAGE.read_text(encoding="utf-8")
    assert "尚未翻譯執行" not in page
    assert "46 個唯一 expression（共 62 個使用點）" in page
    assert "20/20 Measure 都有 asserted synthetic branch cases" in page
    assert "synthetic-test-only" in page
    assert "RC-05 要求的獨立逐案重算" in page
    assert "RC-06 要求的一個完整報告期間原始資料 golden cohort" in page
    assert "不能宣稱指標數字已具臨床正確性" in page
