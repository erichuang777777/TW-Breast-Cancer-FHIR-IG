import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "mappings" / "twpas" / "breast-common-to-twpas-1.2.5.csv"
TASK_ONLY = ROOT / "mappings" / "twpas" / "twpas-task-only-fields-1.2.5.csv"
VERSION_POLICY = ROOT / "mappings" / "twpas" / "twpas-version-policy.csv"
CI_WATCHLIST = ROOT / "mappings" / "twpas" / "twpas-ci-1.2.6-watchlist.csv"
OFFICIAL_CANONICAL = "https://nhicore.nhi.gov.tw/pas/StructureDefinition/"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_twpas_crosswalk_is_versioned_unique_and_points_to_official_profiles():
    mapping = rows(CROSSWALK)
    assert mapping
    assert len({row["mapping_id"] for row in mapping}) == len(mapping)
    assert all(row["mapping_id"].startswith("TWPAS-BC-") for row in mapping)
    assert all(row["target_profile"].startswith(OFFICIAL_CANONICAL) for row in mapping)
    assert all(row["target_path"] and row["projection_rule"] and row["loss_policy"] for row in mapping)
    assert all(row["review_status"] != "officially-accepted" for row in mapping)


def test_twpas_task_only_fields_never_claim_to_be_common_facts():
    fields = rows(TASK_ONLY)
    assert fields
    assert all(row["common_fact"] == "no" for row in fields)
    assert all(row["source_owner"] == "TWPAS application workflow" for row in fields)
    assert all(row["target_path"] and row["required_behavior"] for row in fields)


def test_repository_does_not_redefine_official_twpas_profiles():
    fsh = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "ig" / "input" / "fsh").glob("*.fsh"))
    assert "Profile: PatientTWPAS" not in fsh
    assert "Profile: MedicationRequestApplyTWPAS" not in fsh
    assert "Profile: BundleTWPAS" not in fsh


def test_twpas_pages_are_in_the_ig_navigation():
    config = (ROOT / "ig" / "sushi-config.yaml").read_text(encoding="utf-8")
    assert "task-twpas.md:" in config
    assert "twpas-crosswalk.md:" in config
    task_page = (ROOT / "ig" / "input" / "pagecontent" / "task-twpas.md").read_text(encoding="utf-8")
    assert "tw.gov.mohw.nhi.pas#1.2.5" in task_page
    assert "不複製" in task_page
    assert "Task-only" in task_page


def test_twpas_version_policy_keeps_published_and_ci_targets_separate():
    policy = {row["target_version"]: row for row in rows(VERSION_POLICY)}
    assert policy["1.2.5"]["publication_status"] == "published"
    assert policy["1.2.5"]["release_gate"] == "blocking"
    assert policy["1.2.6"]["publication_status"] == "ci-build"
    assert policy["1.2.6"]["release_gate"] == "advisory"
    assert all(row["main_ig_dependency_allowed"] == "no" for row in policy.values())


def test_twpas_ci_watchlist_is_advisory_traceable_and_breast_relevant():
    warnings = rows(CI_WATCHLIST)
    assert warnings
    assert len({row["watch_id"] for row in warnings}) == len(warnings)
    assert all(row["ci_version"] == "1.2.6" for row in warnings)
    assert all(row["release_gate"] == "advisory" for row in warnings)
    assert all(row["required_check"] and row["breast_cancer_value"] for row in warnings)
    assert all(row["source_url"] == "https://build.fhir.org/ig/TWNHIFHIR/pas/" for row in warnings)


def test_ci_package_is_not_a_main_ig_dependency():
    config = (ROOT / "ig" / "sushi-config.yaml").read_text(encoding="utf-8")
    assert "tw.gov.mohw.nhi.pas:" not in config
    assert "tw.gov.mohw.nhi.pas#1.2.6" not in config
