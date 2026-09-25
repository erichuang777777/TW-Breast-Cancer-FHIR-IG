import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAPPINGS = ROOT / "mappings" / "case-management"
CROSSWALK = MAPPINGS / "breast-common-to-case-management.csv"
CATALOG = MAPPINGS / "case-management-measure-catalog.csv"
CRITERIA = MAPPINGS / "case-management-population-criteria.csv"
TASK_ONLY = MAPPINGS / "case-management-task-only-fields.csv"

QUALITY_MEASURES = {"bc-qi-01", "bc-qi-02", "bc-qi-03", "bc-qi-04", "bc-qi-05",
                    "bc-qi-06"}
QUARTERLY_RATES = {"bc-qr-01", "bc-qr-02", "bc-qr-03", "bc-qr-04", "bc-qr-05"}
QUARTERLY_COHORTS = {"bc-qr-10", "bc-qr-11", "bc-qr-12", "bc-qr-13", "bc-qr-14",
                     "bc-qr-15", "bc-qr-16", "bc-qr-17", "bc-qr-18"}
FAMILIES = {"quality", "quarterly", "both"}
PYTHON_STATUS_VALUES = {
    "implemented", "not-implemented", "divergent", "not-evaluable", "manual-override",
    "task-layer",
}
POPULATION_TYPES = {
    "initial-population",
    "denominator",
    "denominator-exclusion",
    "numerator",
    "numerator-exclusion",
    "stratifier",
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_crosswalk_ids_are_unique_and_every_row_states_a_target_and_a_gap():
    mapping = rows(CROSSWALK)
    assert mapping
    assert len({row["mapping_id"] for row in mapping}) == len(mapping)
    assert all(row["mapping_id"].startswith("CM-BC-") for row in mapping)
    assert all(row["target_path"] and row["projection_rule"] for row in mapping)
    assert all(row["gap_if_absent"] for row in mapping)


def test_unverified_terminology_is_declared_rather_than_assumed():
    """A candidate code may sit in the mapping, but it must be labelled as one."""
    for row in rows(CROSSWALK):
        if row["candidate_terminology"]:
            assert row["terminology_status"] == "candidate-unverified", row["mapping_id"]
        else:
            assert row["terminology_status"] in {"n/a", "candidate-unverified"}


def test_every_row_declares_which_report_family_needs_it():
    for row in rows(CROSSWALK):
        assert row["used_by_indicator_family"] in FAMILIES, row["mapping_id"]
    for row in rows(TASK_ONLY):
        assert row["used_by_indicator_family"] in FAMILIES, row["field_id"]


def test_a_shared_fact_is_one_row_serving_both_families():
    """The whole point of merging the two tasks: a fact both reports need is
    described once, so the two descriptions cannot drift apart. A blank legacy
    worksheet column is allowed: several newly exposed dependencies are absent
    from that report, which is precisely the source gap the mapping records."""
    shared = [row for row in rows(CROSSWALK)
              if row["used_by_indicator_family"] == "both"]
    assert len(shared) >= 6
    assert len({row["common_concept"] for row in shared}) == len(shared)


def test_legacy_ids_are_recorded_and_unique_so_the_merge_stays_traceable():
    seen: dict[str, str] = {}
    for row in rows(CROSSWALK):
        assert row["legacy_ids"], row["mapping_id"]
        for old in row["legacy_ids"].split():
            assert old.startswith(("QI-BC-", "QR-BC-")), old
            assert old not in seen, (old, seen.get(old), row["mapping_id"])
            seen[old] = row["mapping_id"]
    for row in rows(TASK_ONLY):
        assert row["legacy_ids"], row["field_id"]
        for old in row["legacy_ids"].split():
            assert old.startswith(("QI-TASK-", "QR-TASK-")), old


def test_every_rate_measure_has_a_denominator_and_a_numerator():
    criteria = rows(CRITERIA)
    assert criteria
    assert all(row["population_type"] in POPULATION_TYPES for row in criteria)
    for measure_id in QUALITY_MEASURES | QUARTERLY_RATES:
        populations = {row["population_type"] for row in criteria
                       if row["measure_id"] == measure_id}
        assert "denominator" in populations, measure_id
        assert "numerator" in populations, measure_id


def test_every_cohort_measure_has_at_least_one_stratifier():
    criteria = rows(CRITERIA)
    for measure_id in QUARTERLY_COHORTS:
        strata = [row for row in criteria
                  if row["measure_id"] == measure_id
                  and row["population_type"] == "stratifier"]
        assert strata, measure_id


def test_criterion_ids_are_unique_and_reference_a_real_mapping_row():
    criteria = rows(CRITERIA)
    assert len({row["criterion_id"] for row in criteria}) == len(criteria)
    known = {row["mapping_id"] for row in rows(CROSSWALK)}
    known |= {row["field_id"] for row in rows(TASK_ONLY)}
    for row in criteria:
        for reference in row["depends_on_mapping"].split():
            assert reference in known, (row["criterion_id"], reference)


def test_declared_fact_family_covers_every_criterion_that_uses_it():
    facts = {row["mapping_id"]: row for row in rows(CROSSWALK)}
    facts.update({row["field_id"]: row for row in rows(TASK_ONLY)})
    family_members = {
        "quality": {"quality"},
        "quarterly": {"quarterly"},
        "both": {"quality", "quarterly"},
    }
    for criterion in rows(CRITERIA):
        for fact_id in criterion["depends_on_mapping"].split():
            assert criterion["indicator_family"] in family_members[
                facts[fact_id]["used_by_indicator_family"]
            ], (criterion["criterion_id"], fact_id)


def test_indirect_and_human_adjudication_dependencies_cannot_disappear():
    """Lock dependencies found by tracing the CQL call graph and task layer.

    These are easy to omit because the criterion expression reaches them through
    a shared helper, an evaluation parameter, or a governed manual decision.
    """
    criteria = {row["criterion_id"]: set(row["depends_on_mapping"].split())
                for row in rows(CRITERIA)}
    expected = {
        "IP-CLASS": {"CM-BC-003", "CM-TASK-001"},
        "IP-QUARTER": {"CM-BC-002", "CM-TASK-020"},
        "N5-ADH-RULE": {"CM-BC-016", "CM-BC-019", "CM-TASK-010"},
        "N6-RT": {"CM-BC-017", "CM-BC-023", "CM-BC-025"},
        "IP-CASELOAD": {"CM-BC-002", "CM-TASK-020", "CM-TASK-023"},
        "N4-LOST": {"CM-BC-037", "CM-TASK-015"},
        "D5-QUIT": {"CM-TASK-003", "CM-TASK-007", "CM-TASK-014"},
        "N5-RETURN": {"CM-BC-035", "CM-TASK-014"},
        "S13-CLOSURE": {"CM-BC-031", "CM-BC-036", "CM-TASK-003"},
        "S16-STAGE": {
            "CM-BC-004", "CM-BC-005", "CM-BC-033", "CM-BC-034",
            "CM-TASK-004", "CM-TASK-013",
        },
        "S17-HISTOLOGY": {"CM-BC-007", "CM-BC-032"},
        "S18-SUBTYPE": {
            "CM-BC-007", "CM-BC-008", "CM-BC-009", "CM-BC-010",
            "CM-BC-011", "CM-BC-032",
        },
    }
    for criterion_id, dependencies in expected.items():
        assert criteria[criterion_id] == dependencies, criterion_id


def test_no_criterion_still_points_at_a_pre_merge_id():
    for row in rows(CRITERIA):
        for reference in row["depends_on_mapping"].split():
            assert not reference.startswith(("QI-", "QR-")), (
                row["criterion_id"], reference)


def test_a_criterion_running_on_a_proxy_says_what_the_proxy_is():
    for row in rows(CRITERIA):
        if row["proxy_removed_by_fhir"] in {"yes", "partial"}:
            assert row["current_proxy"], row["criterion_id"]
        if row["review_status"] in {"proxy-in-use", "blocking-data-gap"}:
            assert row["current_proxy"], row["criterion_id"]


def test_indicator_six_keeps_both_readings_visible():
    variants = {row["variant"] for row in rows(CRITERIA)
                if row["measure_id"] == "bc-qi-06"}
    assert {"practice", "definition"} <= variants


def test_cql_and_python_status_are_tracked_for_every_criterion():
    """CQL is the normative expression, Python the reference implementation;
    neither may quietly go missing, and python_status may only be one of the
    values the reference-implementation manifest actually distinguishes."""
    for row in rows(CRITERIA):
        assert row["cql_status"], row["criterion_id"]
        assert row["python_status"], row["criterion_id"]
        assert row["python_status"] in PYTHON_STATUS_VALUES, row["criterion_id"]


def test_a_divergent_or_unimplemented_criterion_states_its_impact():
    """A row that says Python does not (or does not honestly) implement a
    criterion is only useful if it also says what changes when the gap is
    closed - otherwise 'not-implemented' is just a different unverified claim.

    Scoped to the quality family: that is what python-implementation-manifest.json
    covers today, so it is the only family whose python_status this repo has
    actually cross-checked against the pipeline that computes it. quarterly's
    not-implemented rows (bc-qr-04, bc-qr-05) are real gaps too, but stating a
    numeric impact for them would be inventing a number nobody has computed."""
    for row in rows(CRITERIA):
        if row["indicator_family"] != "quality":
            continue
        if row["python_status"] in ("not-implemented", "divergent"):
            assert row["python_divergence"], row["criterion_id"]


def test_a_blocked_criterion_is_not_claimed_as_implemented():
    """The loss-to-follow-up rate needs a prior-year cohort this export has
    never contained. Reporting it as calculated would be a lie on the form."""
    for row in rows(CRITERIA):
        if row["measure_id"] == "bc-qr-04":
            assert row["python_status"] == "not-implemented", row["criterion_id"]


def test_measure_catalog_covers_exactly_the_declared_measures():
    catalog = rows(CATALOG)
    expected = QUALITY_MEASURES | QUARTERLY_RATES | QUARTERLY_COHORTS
    assert {row["measure_id"] for row in catalog} == expected
    for row in catalog:
        assert row["indicator_family"] in {"quality", "quarterly"}, row["measure_id"]
        if row["measure_id"] in QUARTERLY_COHORTS:
            assert row["scoring"] == "cohort", row["measure_id"]
        else:
            assert row["scoring"] == "proportion", row["measure_id"]
        assert (row["status"].startswith("draft")
                or row["status"] == "blocked-data-gap"), row["measure_id"]


def test_the_two_families_report_at_their_own_level():
    catalog = {row["measure_id"]: row for row in rows(CATALOG)}
    for measure_id in QUALITY_MEASURES:
        assert catalog[measure_id]["threshold_owner"] == "multidisciplinary team"
        assert catalog[measure_id]["threshold_2026"]
    for measure_id in QUARTERLY_RATES | QUARTERLY_COHORTS:
        assert catalog[measure_id]["reporting_unit"] == "case manager", measure_id


def test_the_three_core_indicators_are_flagged():
    catalog = rows(CATALOG)
    core = {row["measure_id"] for row in catalog
            if row["core_indicator"].startswith("yes")}
    assert core == {"bc-qi-02", "bc-qi-03", "bc-qi-04"}


def test_the_blocked_rate_is_marked_in_the_catalog_too():
    catalog = {row["measure_id"]: row for row in rows(CATALOG)}
    assert catalog["bc-qr-04"]["status"] == "blocked-data-gap"
    assert "not calculated" in catalog["bc-qr-04"]["reference_result"]


def test_task_only_fields_never_claim_to_be_common_facts():
    fields = rows(TASK_ONLY)
    assert fields
    assert all(row["common_fact"] == "no" for row in fields)
    assert all(row["fhir_representation"] and row["required_behavior"] for row in fields)


def test_partial_derivability_points_at_real_common_facts():
    """Saying 'part of this is derivable' is only useful if it names which
    fact would derive it."""
    known = {row["mapping_id"] for row in rows(CROSSWALK)}
    for row in rows(TASK_ONLY):
        for reference in row["partially_derivable_from"].split():
            assert reference in known, (row["field_id"], reference)


def test_class_label_stays_task_only_for_both_families():
    fields = {row["field_id"]: row for row in rows(TASK_ONLY)}
    assert fields["CM-TASK-001"]["used_by_indicator_family"] == "both"
    assert fields["CM-TASK-001"]["common_fact"] == "no"


def test_task_003_carries_both_case_status_and_closure_reason():
    """S12 and S13 share CM-TASK-003, so neither Task input may disappear."""
    field = {row["field_id"]: row for row in rows(TASK_ONLY)}["CM-TASK-003"]
    assert field["fhir_representation"] == (
        "Task.input[case-status]|Task.input[closure-reason]"
    )
    behavior = field["required_behavior"]
    assert "case status:" in behavior
    assert "closure reason when closed:" in behavior


def test_case_management_task_profile_and_cql_are_patient_scoped():
    profile = (ROOT / "ig" / "input" / "fsh" / "case-management-task.fsh").read_text(
        encoding="utf-8"
    )
    assert "Profile: BreastCancerCaseManagementTask" in profile
    assert "Parent: Task" in profile
    assert "* for 1..1" in profile
    expected_slices = {
        "caseEntryCategory",
        "caseStatus",
        "closureReason",
        "registryCaseClass",
        "retentionDisposition",
        "curativeTreatmentDisposition",
        "treatmentCompletion",
    }
    assert all(f"* input[{name}].value[x] only CodeableConcept" in profile
               for name in expected_slices)

    cql = (ROOT / "ig" / "input" / "cql" / "BreastCancerCaseManagement.cql").read_text(
        encoding="utf-8"
    )
    assert 'CaseTask."for".reference.value' in cql
    assert "= Patient.id.value" in cql

    capability = (ROOT / "ig" / "input" / "fsh" / "capability.fsh").read_text(
        encoding="utf-8"
    )
    assert "/StructureDefinition/breast-cancer-case-management-task" in capability
    assert "/StructureDefinition/tcr-registry-abstraction-task" in capability


def test_case_management_page_is_in_the_ig_navigation_and_states_its_boundaries():
    config = (ROOT / "ig" / "sushi-config.yaml").read_text(encoding="utf-8")
    assert "task-case-management.md:" in config
    assert "task-case-management.html" in config
    assert "task-quality-index" not in config
    assert "task-quarterly-report" not in config

    index_page = (ROOT / "ig" / "input" / "pagecontent" / "task-index.md").read_text(
        encoding="utf-8")
    assert "task-case-management.html" in index_page

    task_page = (ROOT / "ig" / "input" / "pagecontent" /
                 "task-case-management.md").read_text(encoding="utf-8")
    assert "沒有關係" in task_page          # not the NHI P4P programme indicators
    assert "稽核者" in task_page            # why two report families
    assert "Task-only" in task_page
    assert "不重現也不取代" in task_page
