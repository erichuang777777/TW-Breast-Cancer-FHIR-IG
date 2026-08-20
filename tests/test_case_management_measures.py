"""The generated artifacts must say the same thing as the mapping tables.

The mapping is merged; the artifacts are what the merge is for. These tests bind
the three descriptions of one indicator together — the population criteria table,
the FSH Measure, the CQL define — so that changing one and forgetting the others
fails here instead of in a committee meeting.
"""

import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAPPINGS = ROOT / "mappings" / "case-management"
CATALOG = MAPPINGS / "case-management-measure-catalog.csv"
CRITERIA = MAPPINGS / "case-management-population-criteria.csv"
FSH = ROOT / "ig" / "input" / "fsh" / "case-management-measures.fsh"
TERMINOLOGY = ROOT / "ig" / "input" / "fsh" / "case-management-terminology.fsh"
CQL = ROOT / "ig" / "input" / "cql" / "BreastCancerCaseManagement.cql"

LIBRARY_URL = ("https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG"
               "/Library/BreastCancerCaseManagement")
SHARED_POPULATION_MEASURES = {"bc-qi-00", "bc-qr-00"}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fsh_text() -> str:
    return FSH.read_text(encoding="utf-8")


def cql_text() -> str:
    return CQL.read_text(encoding="utf-8")


def measure_blocks() -> dict[str, str]:
    """Every FSH Measure instance body, keyed by its measure id."""
    blocks: dict[str, str] = {}
    for block in fsh_text().split("\nInstance: ")[1:]:
        block = block.split("\nProfile: ")[0]
        if "InstanceOf: Measure" not in block:
            continue
        measure_id = re.search(r'\* id = "(bc-q[ir]-\d+)"', block)
        assert measure_id, block.splitlines()[0]
        blocks[measure_id.group(1)] = block
    return blocks


def populations(body: str) -> set[str]:
    return set(re.findall(
        r"population\[\d+\]\.code = \$MeasurePopulation#([a-z-]+)", body))


def expressions(body: str) -> list[str]:
    return re.findall(r'criteria\.expression = "([^"]+)"', body)


def stratifier_expressions(body: str) -> list[str]:
    return re.findall(
        r'stratifier\[\d+\]\.criteria\.expression = "([^"]+)"', body)


def cql_defines() -> set[str]:
    return set(re.findall(r'^define (?:function )?"([^"]+)"', cql_text(), re.M))


def test_every_catalogued_measure_exists_as_a_measure_instance():
    catalogued = {row["measure_id"] for row in rows(CATALOG)}
    assert catalogued == set(measure_blocks()), (
        "the catalog and the FSH have drifted apart")


def test_both_families_share_one_library():
    """The merge is only real if one library serves both report families."""
    blocks = measure_blocks()
    for measure_id, body in blocks.items():
        assert f'* library = "{LIBRARY_URL}"' in body, measure_id
    assert "BreastCancerQualityIndex" not in fsh_text()
    assert "BreastCancerQualityIndex" not in cql_text()
    assert f"library BreastCancerCaseManagement" in cql_text()


def test_no_artifact_is_still_filed_under_the_pre_merge_name():
    fsh_dir = ROOT / "ig" / "input" / "fsh"
    cql_dir = ROOT / "ig" / "input" / "cql"
    assert not list(fsh_dir.glob("quality-index*"))
    assert not list(cql_dir.glob("*QualityIndex*"))


def test_measure_scoring_matches_the_catalog():
    catalog = {row["measure_id"]: row for row in rows(CATALOG)}
    for measure_id, body in measure_blocks().items():
        expected = catalog[measure_id]["scoring"]
        assert f"* scoring = $MeasureScoring#{expected}" in body, measure_id
        if expected == "cohort":
            assert "improvementNotation" not in body, measure_id
        else:
            notation = catalog[measure_id]["improvement_notation"]
            assert f"$MeasureImprovement#{notation}" in body, measure_id


def test_every_measure_declares_the_populations_its_criteria_table_declares():
    """Shared initial populations live on the bc-qi-00 / bc-qr-00 rows; every
    other population type must appear on both sides or on neither."""
    table: dict[str, set[str]] = {}
    for row in rows(CRITERIA):
        table.setdefault(row["measure_id"], set()).add(row["population_type"])
    for measure_id, body in measure_blocks().items():
        declared = populations(body) - {"initial-population"}
        expected = table.get(measure_id, set()) - {"stratifier"}
        assert declared == expected, (measure_id, declared, expected)


def test_every_measure_starts_from_a_shared_initial_population():
    shared = {row["criterion_id"] for row in rows(CRITERIA)
              if row["measure_id"] in SHARED_POPULATION_MEASURES}
    assert shared
    for measure_id, body in measure_blocks().items():
        assert "initial-population" in populations(body), measure_id


def test_cohort_measures_carry_the_stratifiers_the_table_lists():
    counts: dict[str, int] = {}
    for row in rows(CRITERIA):
        if row["population_type"] == "stratifier":
            counts[row["measure_id"]] = counts.get(row["measure_id"], 0) + 1
    for measure_id, expected in counts.items():
        body = measure_blocks()[measure_id]
        assert len(stratifier_expressions(body)) == expected, measure_id


def test_every_measure_expression_resolves_to_a_cql_define():
    """A criteria.expression naming a define that does not exist is a measure
    that cannot be evaluated, and nothing else in the build would catch it."""
    defines = cql_defines()
    for measure_id, body in measure_blocks().items():
        for expression in expressions(body) + stratifier_expressions(body):
            assert expression in defines, (measure_id, expression)


def test_every_criterion_is_traceable_into_the_cql():
    """Each define carries the criterion_id it implements, so a reviewer can go
    from a number on the form to the rule that produced it."""
    text = cql_text()
    for row in rows(CRITERIA):
        assert row["criterion_id"] in text, row["criterion_id"]


def test_the_cql_covers_both_families_not_just_the_quality_indicators():
    text = cql_text()
    assert 'define "Quarterly Caseload"' in text
    assert 'define "New Diagnosis Case"' in text
    for index in range(1, 6):
        assert f'define "Denominator QR{index}"' in text
        assert f'define "Numerator QR{index}"' in text


def test_the_quarterly_rates_are_attributable_to_one_case_manager():
    """A quarterly figure belongs to a case manager. Reporting the whole
    caseload under one person's name would overstate that person's work."""
    text = cql_text()
    assert 'parameter "Reporting Case Manager" String default null' in text
    assert "careManager" in text
    for measure_id in {"bc-qr-01", "bc-qr-02", "bc-qr-03", "bc-qr-04",
                       "bc-qr-05"}:
        assert measure_id in measure_blocks()


def test_the_blocked_rate_cannot_silently_report_a_number():
    """bc-qr-04 needs a prior-year cohort the export has never carried. The
    population must stay empty until the caller says the cohort is loaded."""
    text = cql_text()
    assert 'parameter "Prior Year Cohort Available" Boolean default false' in text
    cohort = text.split('define "Prior Year And Current New Diagnosis Cohort":')[1]
    assert '"Prior Year Cohort Available"' in cohort.split("define ")[0]
    assert "無法計算" in measure_blocks()["bc-qr-04"]


def test_administrative_categories_are_enumerated_and_clinical_ones_are_not():
    """Enumerating a code the case management team owns is honest; enumerating
    an unverified LOINC or SNOMED CT code is not."""
    terminology = TERMINOLOGY.read_text(encoding="utf-8")
    admin_systems = re.findall(r"^CodeSystem: (\w+)", terminology, re.M)
    assert len(admin_systems) >= 7
    for block in terminology.split("CodeSystem: ")[1:]:
        assert re.search(r'^\* #[\w-]+ "', block, re.M), block.splitlines()[0]
    for block in terminology.split("ValueSet: ")[1:]:
        header = block.splitlines()[0]
        if "include codes from system" in block:
            continue
        assert "待驗證後補齊" in block, header


def test_task_only_workflow_data_is_read_not_inferred():
    """Case entry category, case status and the dispositions are administrative
    facts. Deriving them from clinical resources would be a guess presented as
    a recorded value."""
    text = cql_text()
    assert 'define function "Case Input Code"' in text
    assert "cm-task-input-type" in text
    for define in ('"Case Entry Category"', '"Case Status"',
                   '"Retention Disposition"',
                   '"Curative Treatment Disposition"',
                   '"Treatment Completion"'):
        assert f"define {define}:\n  \"Case Input Code\"(" in text, define


def test_the_three_ways_a_stage_can_be_missing_stay_separate():
    """The worksheet writes '?' for staging-in-progress, transfer-during-staging
    and unobtainable outside records. Collapsing them re-creates the manual
    sorting the model exists to remove."""
    text = cql_text()
    stage = text.split('define "Reported Stage Group":')[1].split("define ")[0]
    assert "staging-in-progress" in stage
    assert "other-transferred-during-staging" in stage
    assert "other-outside-records-insufficient" in stage


def test_the_invasive_denominator_excludes_in_situ_and_phyllodes():
    text = cql_text()
    invasive = text.split('define "Is Invasive Histology":')[1].split("define ")[0]
    assert "'dcis'" in invasive and "'phyllodes'" in invasive
    group = text.split('define "Histology Group":')[1].split('define "Has Micro')[0]
    assert "Has Microinvasion" in group, (
        "DCIS with microinvasion is reported with the invasive carcinomas")


def test_the_subtype_is_derived_from_markers_not_from_the_typed_letter():
    text = cql_text()
    subtype = text.split('define "HR HER2 Subtype":')[1]
    assert "Hormone Receptor Positive" in subtype
    assert "HER2 Positive" in subtype
    assert "'indeterminate'" in subtype
    assert "Is Invasive Histology" in subtype


def test_committee_and_case_manager_decisions_stay_out_of_the_measures():
    """Thresholds, add-backs and per-case adjudications are human decisions
    recorded with a reason. A measure that encoded them would hide them."""
    text = fsh_text()
    assert "threshold" not in text.lower()
    for row in rows(CATALOG):
        if row["threshold_2026"] not in {"n/a", ""}:
            assert row["threshold_2026"] not in text, row["measure_id"]


# --------------------------------------------------------------------------
# python_status vs. the reference-implementation manifest
#
# The eighteen tests above bind Measure <-> CQL <-> criteria table together,
# but say nothing about whether the criteria table's python_status column is
# true. python-implementation-manifest.json is generated from the pipeline
# that actually produces the quarterly report (pipeline/rules.py's
# CRITERION_IDS / UNIMPLEMENTED_CRITERIA, exported by
# pipeline/export_criteria_manifest.py); comparing against it is what turns
# "CQL and Python agree" from a claim in a comment into a check that fails.
# --------------------------------------------------------------------------

MANIFEST = MAPPINGS / "python-implementation-manifest.json"


def manifest() -> dict:
    with MANIFEST.open(encoding="utf-8") as handle:
        return json.load(handle)


def test_the_reference_implementation_manifest_exists_and_declares_its_scope():
    data = manifest()
    assert data["families_covered"] == ["quality"], (
        "the manifest's scope changed; the exemption test below and the "
        "quarterly-family callout in the mappings README must be revisited")
    assert data["note"], "an unscoped manifest must say so, not go silent about it"


def test_quality_criteria_covered_by_the_manifest_match_its_python_status():
    """Every criterion_id the manifest actually knows about (it was generated
    from rules.py, not from this CSV, so it does not necessarily know about
    every row here) must have the same python_status the manifest computed.
    Flip a covered row's status without re-running the pipeline export and
    this fails - that is the point."""
    data = manifest()
    implemented = set(data["implemented"])
    unimplemented = set(data["unimplemented"])
    covered = implemented | unimplemented
    checked = 0
    for row in rows(CRITERIA):
        if row["indicator_family"] != "quality" or row["criterion_id"] not in covered:
            continue
        checked += 1
        if row["criterion_id"] in implemented:
            assert row["python_status"] == "implemented", row["criterion_id"]
        else:
            assert row["python_status"] in ("not-implemented", "divergent",
                                            "not-evaluable"), row["criterion_id"]
    # the three known divergences plus N3-DOSE must all have been exercised
    assert checked >= 4


def test_the_quarterly_family_exemption_from_manifest_checking_is_explicit():
    """quarterly's Python reference implementation lives in a different
    project (個管品管_2_季報統計/scripts/quarterly_report.py) and has not been
    audited against this CSV. Skipping the consistency check for it is a
    documented boundary, not a gap nobody noticed."""
    data = manifest()
    assert "quarterly" not in data["families_covered"]
    readme = (MAPPINGS / "README.md").read_text(encoding="utf-8")
    assert "quarterly" in readme and "python_status" in readme, (
        "the quarterly exemption must be written down in the mappings README")
