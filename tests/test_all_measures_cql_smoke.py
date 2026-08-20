import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CQL = ROOT / "ig" / "input" / "cql" / "BreastCancerCaseManagement.cql"
MEASURES = ROOT / "ig" / "input" / "fsh" / "case-management-measures.fsh"
CASES = ROOT / "tests" / "fixtures" / "cql" / "all-measures-smoke-cases.json"
VALUE_SETS = ROOT / "tests" / "fixtures" / "cql" / "all-measures-value-sets.json"
RUNNER = ROOT / "ig" / "tools" / "cql-evaluation" / "run-all-measures-smoke.js"
ASSERTED_RUNNER = ROOT / "ig" / "tools" / "cql-evaluation" / "run-asserted-cases.js"
QI02_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qi-02-cases.json"
QI03_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qi-03-cases.json"
QI04_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qi-04-cases.json"
QI05_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qi-05-cases.json"
QI06_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qi-06-cases.json"
QR01_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qr-01-cases.json"
QR02_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qr-02-cases.json"
QR03_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qr-03-cases.json"
QR04_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qr-04-cases.json"
QR05_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qr-05-cases.json"
QR10_12_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qr-10-12-cases.json"
QR13_15_CASES = ROOT / "tests" / "fixtures" / "cql" / "bc-qr-13-15-cases.json"
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


def test_bc_qi_02_assertions_cover_eligibility_missing_and_order_boundaries():
    cases = load(QI02_CASES)
    by_id = {case["id"]: case for case in cases}
    assert set(by_id) == {
        "eligible-slnb",
        "eligible-without-slnb",
        "systemic-therapy-before-surgery",
        "missing-node-category",
        "clinical-stage-iii-outside-denominator",
    }
    patient_ids = []
    for case in cases:
        assert case["bundle"]["meta"]["tag"] == [
            {"system": "https://example.org/tags", "code": "synthetic"}
        ]
        patients = [
            entry["resource"]
            for entry in case["bundle"]["entry"]
            if entry["resource"]["resourceType"] == "Patient"
        ]
        assert len(patients) == 1
        patient_ids.append(patients[0]["id"])
    assert len(patient_ids) == len(set(patient_ids))

    assert by_id["eligible-slnb"]["expected"]["Denominator 2"] is True
    assert by_id["eligible-slnb"]["expected"]["Numerator 2"] is True
    assert by_id["eligible-without-slnb"]["expected"]["Numerator 2"] is False
    assert by_id["systemic-therapy-before-surgery"]["expected"]["Surgery Was First Treatment"] is False
    assert by_id["missing-node-category"]["expected"]["Denominator 2"] is False
    assert by_id["clinical-stage-iii-outside-denominator"]["expected"]["Denominator 2"] is False


def test_ci_executes_bc_qi_02_assertions_with_per_case_runner():
    runner = ASSERTED_RUNNER.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "testCase.parameters" in runner
    assert runner.index("FHIRv401()") > runner.index("for (const [expression, expected]")
    assert "assert.deepEqual(result[expression], expected" in runner
    assert "Execute bc-qi-02 asserted CQL branches" in workflow
    assert "bc-qi-02-cases.json" in workflow


def test_bc_qi_03_assertions_cover_radiotherapy_exclusion_node_and_missing_stage():
    by_id = {case["id"]: case["expected"] for case in load(QI03_CASES)}
    assert set(by_id) == {
        "eligible-radiotherapy",
        "eligible-without-radiotherapy",
        "metastatic-exclusion",
        "n1-below-node-boundary",
        "missing-pathological-stage",
    }
    assert by_id["eligible-radiotherapy"] == {
        "Initial Population": True,
        "Denominator 3": True,
        "Denominator 3 Exclusion": False,
        "Numerator 3": True,
    }
    assert by_id["eligible-without-radiotherapy"]["Numerator 3"] is False
    assert by_id["metastatic-exclusion"]["Denominator 3 Exclusion"] is True
    assert by_id["n1-below-node-boundary"]["Denominator 3"] is False
    assert by_id["missing-pathological-stage"]["Denominator 3"] is False

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Execute bc-qi-03 asserted CQL branches" in workflow
    assert "bc-qi-03-cases.json" in workflow


def test_bc_qi_04_assertions_cover_ihc_ish_node_treatment_and_metastatic_branches():
    by_id = {case["id"]: case["expected"] for case in load(QI04_CASES)}
    assert set(by_id) == {
        "ihc-3-positive-treated",
        "ihc-3-positive-untreated",
        "ihc-2-ish-positive-boundary",
        "ihc-2-without-positive-ish",
        "node-negative-outside-denominator",
        "metastatic-exclusion",
    }
    assert by_id["ihc-3-positive-treated"]["Numerator 4"] is True
    assert by_id["ihc-3-positive-untreated"]["Numerator 4"] is False
    assert by_id["ihc-2-ish-positive-boundary"]["HER2 ISH Positive"] is True
    assert by_id["ihc-2-ish-positive-boundary"]["Denominator 4"] is True
    assert by_id["ihc-2-without-positive-ish"]["HER2 Positive"] is False
    assert by_id["node-negative-outside-denominator"]["Denominator 4"] is False
    assert by_id["metastatic-exclusion"]["Denominator 4 Exclusion"] is True

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Execute bc-qi-04 asserted CQL branches" in workflow
    assert "bc-qi-04-cases.json" in workflow


def test_bc_qi_05_assertions_cover_biopsy_timing_stage_and_missing_data():
    by_id = {case["id"]: case["expected"] for case in load(QI05_CASES)}
    assert set(by_id) == {
        "biopsy-day-before-surgery",
        "same-day-biopsy-boundary",
        "missing-biopsy",
        "metastatic-exclusion",
        "stage-zero-exclusion",
        "missing-stage",
    }
    assert by_id["biopsy-day-before-surgery"]["Numerator 5"] is True
    assert by_id["same-day-biopsy-boundary"]["Numerator 5"] is False
    assert by_id["missing-biopsy"]["Numerator 5"] is False
    assert by_id["metastatic-exclusion"]["Denominator 5 Exclusion"] is True
    assert by_id["stage-zero-exclusion"]["Denominator 5"] is False
    assert by_id["stage-zero-exclusion"]["Denominator 5 Exclusion"] is True
    assert by_id["missing-stage"]["Denominator 5"] is False

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Execute bc-qi-05 asserted CQL branches" in workflow
    assert "bc-qi-05-cases.json" in workflow


def test_bc_qi_06_assertions_keep_practice_and_definition_variants_distinct():
    cases = load(QI06_CASES)
    by_id = {case["id"]: case for case in cases}
    assert set(by_id) == {
        "eligible-radiotherapy-after-surgery",
        "eligible-without-radiotherapy",
        "radiotherapy-before-surgery",
        "age-70-node-positive-practice",
        "age-70-node-positive-definition",
        "age-69-node-negative-practice",
        "age-69-node-negative-definition",
        "tis-noninvasive",
        "missing-pathological-stage",
    }
    assert by_id["eligible-radiotherapy-after-surgery"]["expected"]["Numerator 6"] is True
    assert by_id["eligible-without-radiotherapy"]["expected"]["Numerator 6"] is False
    assert by_id["radiotherapy-before-surgery"]["expected"]["Numerator 6"] is False

    for prefix in ("age-70-node-positive", "age-69-node-negative"):
        practice = by_id[f"{prefix}-practice"]
        definition = by_id[f"{prefix}-definition"]
        assert practice["parameters"]["Indicator 6 Variant"] == "practice"
        assert definition["parameters"]["Indicator 6 Variant"] == "definition"
        assert practice["expected"]["Denominator 6 Exclusion"] is True
        assert definition["expected"]["Denominator 6 Exclusion"] is False

    assert by_id["tis-noninvasive"]["expected"]["Is Invasive Disease"] is False
    assert by_id["missing-pathological-stage"]["expected"]["Denominator 6"] is False

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Execute bc-qi-06 asserted CQL branches" in workflow
    assert "bc-qi-06-cases.json" in workflow


def test_bc_qr_01_assertions_cover_retention_exclusions_staging_and_cohort():
    cases = load(QR01_CASES)
    by_id = {case["id"]: case for case in cases}
    assert set(by_id) == {
        "new-diagnosis-stays",
        "transfer-during-staging",
        "considering-return-excluded",
        "temporary-unknown-stage-excluded",
        "existing-case-outside-denominator",
    }
    assert all(case["bundle"]["meta"]["tag"] == [
        {"system": "https://example.org/tags", "code": "synthetic"}
    ] for case in cases)
    assert by_id["new-diagnosis-stays"]["expected"]["Numerator QR1"] is True
    assert by_id["transfer-during-staging"]["expected"]["Numerator QR1 Exclusion"] is True
    assert by_id["considering-return-excluded"]["expected"]["Denominator QR1 Exclusion"] is True
    assert by_id["temporary-unknown-stage-excluded"]["expected"]["Staging In Progress"] is True
    assert by_id["existing-case-outside-denominator"]["expected"]["Denominator QR1"] is False

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Execute bc-qr-01 asserted CQL branches" in workflow
    assert "bc-qr-01-cases.json" in workflow


def test_bc_qr_02_assertions_require_the_governed_reporting_system_root():
    cases = load(QR02_CASES)
    by_id = {case["id"]: case for case in cases}
    assert set(by_id) == {
        "stay-counts-without-system-parameter",
        "transfer-to-reporting-system",
        "transfer-to-other-system",
        "transfer-without-system-parameter",
        "qr1-exclusion-removed-from-denominator",
    }
    assert by_id["transfer-to-reporting-system"]["parameters"] == {
        "Reporting Organization System Root": "ntuh-system"
    }
    assert by_id["transfer-to-reporting-system"]["expected"]["Numerator QR2"] is True
    assert by_id["transfer-to-other-system"]["expected"]["Numerator QR2"] is False
    assert by_id["transfer-without-system-parameter"]["expected"]["Transferred Within NTUH System"] is False
    assert by_id["qr1-exclusion-removed-from-denominator"]["expected"]["Denominator QR2"] is False

    cql = CQL.read_text(encoding="utf-8")
    assert 'parameter "Reporting Organization System Root" String default null' in cql
    assert '= "Reporting Organization System Root"' in cql
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Execute bc-qr-02 asserted CQL branches" in workflow
    assert "bc-qr-02-cases.json" in workflow


def test_bc_qr_03_assertions_cover_completion_running_exclusions_and_missing_admin_data():
    cases = load(QR03_CASES)
    by_id = {case["id"]: case["expected"] for case in cases}
    assert set(by_id) == {
        "completed-here",
        "administratively-in-treatment",
        "clinical-treatment-resource-running",
        "noncurative-exclusion",
        "incomplete-interrupted",
        "death-before-treatment",
        "existing-case-outside-denominator",
    }
    assert by_id["completed-here"]["Numerator QR3"] is True
    assert by_id["administratively-in-treatment"]["Curative Treatment Still Running"] is True
    assert by_id["clinical-treatment-resource-running"]["Curative Treatment Still Running"] is True
    assert by_id["noncurative-exclusion"]["Denominator QR3 Exclusion"] is True
    assert by_id["incomplete-interrupted"]["Numerator QR3 Exclusion"] is True
    assert by_id["death-before-treatment"]["Died Before Curative Treatment"] is True
    assert by_id["existing-case-outside-denominator"] == {
        "Denominator QR3": False,
        "Denominator QR3 Exclusion": False,
        "Numerator QR3": False,
        "Numerator QR3 Exclusion": False,
    }

    cql = CQL.read_text(encoding="utf-8")
    assert 'Coalesce("Treatment Completion" in {' in cql
    assert 'Coalesce("Curative Treatment Disposition" = ' in cql
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Execute bc-qr-03 asserted CQL branches" in workflow
    assert "bc-qr-03-cases.json" in workflow


def test_bc_qr_04_assertions_cover_cohort_gate_death_and_one_year_boundary():
    cases = load(QR04_CASES)
    by_id = {case["id"]: case for case in cases}
    assert set(by_id) == {
        "cohort-not-loaded",
        "current-new-diagnosis-living-explicit-false",
        "prior-year-cohort-member",
        "deceased-cohort-member-excluded",
        "last-contact-exactly-one-year",
        "last-contact-one-day-inside-year",
        "missing-last-contact-not-inferred-lost",
    }
    assert by_id["cohort-not-loaded"]["expected"]["Denominator QR4"] is False
    assert by_id["current-new-diagnosis-living-explicit-false"]["expected"]["Patient Is Deceased"] is False
    assert by_id["prior-year-cohort-member"]["expected"]["Denominator QR4"] is True
    assert by_id["deceased-cohort-member-excluded"]["expected"]["Denominator QR4"] is False
    assert by_id["last-contact-exactly-one-year"]["expected"]["Numerator QR4"] is True
    assert by_id["last-contact-one-day-inside-year"]["expected"]["Numerator QR4"] is False
    assert by_id["missing-last-contact-not-inferred-lost"]["expected"]["Last Contact Date"] is None

    cql = CQL.read_text(encoding="utf-8")
    assert 'define "Patient Is Deceased":' in cql
    assert '"Last Contact Date" same day or before' in cql
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Execute bc-qr-04 asserted CQL branches" in workflow
    assert "bc-qr-04-cases.json" in workflow


def test_bc_qr_05_candidate_assertions_cover_temporal_and_missing_date_branches():
    cases = load(QR05_CASES)
    by_id = {case["id"]: case["expected"] for case in cases}
    assert set(by_id) == {
        "resumed-day-after-interruption",
        "treatment-same-day-not-after",
        "treatment-before-interruption",
        "missing-interruption-date",
        "completion-field-creates-denominator",
        "ordinary-case-outside-denominator",
    }
    assert by_id["resumed-day-after-interruption"]["Numerator QR5"] is True
    assert by_id["treatment-same-day-not-after"]["Numerator QR5"] is False
    assert by_id["treatment-before-interruption"]["Numerator QR5"] is False
    assert by_id["missing-interruption-date"]["Interruption Date"] is None
    assert by_id["missing-interruption-date"]["Numerator QR5"] is False
    assert by_id["completion-field-creates-denominator"]["Denominator QR5"] is True
    assert by_id["ordinary-case-outside-denominator"] == {
        "Denominator QR5": False,
        "Numerator QR5": False,
    }

    cql = CQL.read_text(encoding="utf-8")
    assert "this expression is a candidate, not" in cql
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Execute bc-qr-05 candidate CQL branches" in workflow
    assert "bc-qr-05-cases.json" in workflow


def test_bc_qr_10_through_12_cover_all_admin_values_month_boundaries_and_rejections():
    cases = load(QR10_12_CASES)
    by_id = {case["id"]: case["expected"] for case in cases}
    categories = {
        expected["Case Entry Category"]
        for expected in by_id.values()
        if expected.get("Case Entry Category") is not None
    }
    assert categories == {
        "new-diagnosis", "existing-case", "delayed-entry-same-year",
        "delayed-entry-prior-year", "first-recurrence-curable",
        "first-recurrence-noncurable",
    }
    statuses = {
        expected["Case Status Reported"]
        for expected in by_id.values()
        if expected.get("Case Status Reported") is not None
    }
    assert statuses == {
        "diagnosis", "treatment", "clinical-trial", "follow-up", "palliative",
        "refused-interrupted", "closed",
    }
    assert by_id["new-diagnosis-diagnosis-january"]["Case Entry Month"] == 1
    assert by_id["existing-treatment-december"]["Case Entry Month"] == 12
    assert by_id["staging-overrides-treatment"]["Case Status"] == "treatment"
    assert by_id["staging-overrides-treatment"]["Case Status Reported"] == "diagnosis"
    assert by_id["missing-task-values"]["Case Entry Category"] is None
    assert by_id["invalid-system-and-code-rejected"] == {
        "Case Entry Category": None,
        "Case Status": None,
        "Case Status Reported": None,
    }

    cql = CQL.read_text(encoding="utf-8")
    assert "AllowedCodes List<String>" in cql
    assert "ValueCoding.system = ValueSystem" in cql
    measures = MEASURES.read_text(encoding="utf-8")
    assert 'criteria.expression = "Case Status Reported"' in measures
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Execute bc-qr-10 through 12 stratifier assertions" in workflow


def test_bc_qr_13_through_15_cover_closure_gender_all_age_bands_and_classes():
    cases = load(QR13_15_CASES)
    expected = [case["expected"] for case in cases]
    assert {item["Closure Reason"] for item in expected if item.get("Closure Reason")} == {
        "death", "transferred", "refused-return", "critical-aad",
    }
    assert {item["Administrative Sex"] for item in expected if item.get("Administrative Sex")} == {
        "male", "female", "other", "unknown",
    }
    assert {item["Age Band At Case Entry"] for item in expected} == {
        "<10", "10-19", "20-29", "30-39", "40-49", "50-59",
        "60-69", "70-79", "80-89", ">=90",
    }
    reported_classes = {
        item["Registry Case Class Reported"]
        for item in expected
        if item.get("Registry Case Class Reported")
    }
    assert reported_classes == {
        "class-0", "class-1", "class-2", "class-3", "staging-in-progress",
    }
    by_id = {case["id"]: case["expected"] for case in cases}
    assert by_id["age-40-missing-demographics-and-admin"]["Administrative Sex"] is None
    assert by_id["age-50-invalid-admin-values"]["Closure Reason"] is None
    assert by_id["age-50-invalid-admin-values"]["Registry Case Class Reported"] is None
    assert by_id["age-70-staging-overrides-class1"]["Registry Case Class"] == "class-1"
    assert by_id["age-70-staging-overrides-class1"]["Registry Case Class Reported"] == "staging-in-progress"

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Execute bc-qr-13 through 15 stratifier assertions" in workflow
