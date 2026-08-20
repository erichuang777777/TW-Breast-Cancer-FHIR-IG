from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publication-readiness.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_publisher_workflow_is_reproducible_and_preserves_evidence():
    text = workflow_text()
    assert "workflow_dispatch:" in text
    assert '"feat/cancer-registry-task-v2"' in text
    assert "releases/download/2.3.2/publisher.jar" in text
    assert "gem install jekyll" in text
    assert "actions/upload-artifact@v7" in text
    assert "ig/output/" in text
    assert "scripts/audit_publisher_qa.py" in text
    assert "mappings/publication/publisher-warning-policy.csv" in text
    assert "publisher-warning-audit.json" in text
    assert "scripts/audit_release_controls.py" in text
    assert "mappings/publication/release-control-register.csv" in text
    assert "release-control-audit.json" in text


def test_publisher_workflow_enforces_technical_and_strict_qa_levels():
    text = workflow_text()
    assert "publisher-exit-code.txt" in text
    assert "errors = 0, warn = [0-9]+, info = [0-9]+, broken links = 0" in text
    assert "publisher_formal_qa_gate" in text
    assert "test -f output/package.tgz" in text
    assert "Complete formal release gate" in text
    assert "maximum_supported_claim" in text
