import configparser
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IG_INI = ROOT / "ig" / "ig.ini"
REGISTER = ROOT / "mappings" / "publication" / "template-supply-chain.csv"
WORKFLOW = ROOT / ".github" / "workflows" / "publication-readiness.yml"
GENERATOR = ROOT / "tcr_workbench" / "ig_export.py"
PAGE_BEGIN_OVERLAY = ROOT / "ig" / "input" / "includes" / "fragment-pagebegin.html"


def test_ig_uses_the_pinned_security_advisory_replacement_template():
    parser = configparser.ConfigParser()
    parser.read(IG_INI, encoding="utf-8")
    assert parser["IG"]["template"] == "fhir2.base.template#0.1.0"
    assert "fhir.base.template" not in IG_INI.read_text(encoding="utf-8")


def test_template_supply_chain_register_is_exact_and_machine_readable():
    with REGISTER.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [{
        "component": "fhir2.base.template",
        "version": "0.1.0",
        "registry_url": "https://packages2.fhir.org/packages/fhir2.base.template",
        "package_url": (
            "https://packages2.fhir.org/web/fhir2.base.template-0.1.0.tgz"
        ),
        "sha1": "7ddff7819ddcb15677d63949f54f13825fa3d4d1",
        "security_advisory": (
            "https://www.fhir.org/guides/security-notices/"
            "2026-03-npm-dependencies.html"
        ),
        "required_status": "pinned-approved-replacement",
        "validation_evidence": (
            "Publisher log must load the exact package; no insecure-template "
            "notice; 0 errors and 0 broken links"
        ),
    }]
    assert re.fullmatch(r"[0-9a-f]{40}", rows[0]["sha1"])


def test_generators_cannot_reintroduce_the_retired_template():
    source = GENERATOR.read_text(encoding="utf-8")
    assert "template = fhir2.base.template#0.1.0" in source
    assert "template = fhir.base.template" not in source


def test_publisher_ci_enforces_exact_template_and_no_security_notice():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "Load Template from fhir2.base.template#0.1.0" in workflow
    assert "! grep -Fq 'no longer considered secure' publisher.log" in workflow


def test_multilanguage_jurisdiction_flag_overlay_uses_root_assets():
    source = PAGE_BEGIN_OVERLAY.read_text(encoding="utf-8")
    assert (
        'src="../assets/images/{{jurisdiction.flag}}.svg"'
        in source
    )
    assert 'src="assets/images/{{jurisdiction.flag}}.svg"' not in source
