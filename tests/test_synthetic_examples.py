from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_FILES = (
    ROOT / "ig" / "input" / "fsh" / "breast-common-examples.fsh",
    ROOT / "ig" / "input" / "fsh" / "examples.fsh",
)


def _example_blocks(text: str) -> list[str]:
    return [f"Instance:{block}" for block in text.split("Instance:")[1:] if "Usage: #example" in block]


def test_every_public_fsh_example_is_marked_synthetic():
    blocks = [block for path in EXAMPLE_FILES for block in _example_blocks(path.read_text(encoding="utf-8"))]
    assert blocks
    unlabeled = [block.splitlines()[0].strip() for block in blocks if "synthetic" not in block.lower() and "合成" not in block]
    assert unlabeled == []


def test_complete_synthetic_scenario_covers_source_fact_and_treatment_layers():
    text = EXAMPLE_FILES[0].read_text(encoding="utf-8")
    scenario = next(block for block in _example_blocks(text) if "BreastCancerSyntheticScenarioBundleExample" in block)
    for resource_type in ("Patient", "Condition", "Specimen", "Observation", "DiagnosticReport", "Procedure", "MedicationRequest", "MedicationAdministration", "EpisodeOfCare"):
        assert f"/{resource_type}/" in scenario


def test_examples_page_carries_bilingual_synthetic_warning():
    page = (ROOT / "ig" / "input" / "pagecontent" / "examples.md").read_text(encoding="utf-8")
    assert "完全合成資料" in page
    assert "completely synthetic" in page.lower()
    assert "不可用於臨床決策或正式申報" in page
    assert "must not be used for clinical decisions or official submission" in page
