from pathlib import Path

from scripts.audit_profile_constraints import audit


ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "ig" / "input" / "pagecontent" / "must-support.md"
CONFIG = ROOT / "ig" / "sushi-config.yaml"
BASELINE = ROOT / "mappings" / "publication" / "profile-constraint-baseline.csv"


def test_must_support_policy_is_published_and_does_not_mean_required():
    page = PAGE.read_text(encoding="utf-8")
    config = CONFIG.read_text(encoding="utf-8")
    assert "{% include disclaimer.md %}" in page
    assert "Must Support 不等於必填" in page
    assert "資料產生者義務" in page
    assert "資料接收者義務" in page
    assert "min = 0" in page and "min = 1" in page
    assert "不得由報表反推為原始事實" in page
    assert "不表示必須提供通用 CRUD" in page
    assert "must-support.md:" in config
    assert "must-support.html" in config


def test_policy_count_is_bound_to_the_live_profile_constraint_inventory():
    report = audit(
        BASELINE,
        [
            ROOT / "ig" / "fsh-generated" / "resources",
            ROOT / "ig" / "input" / "resources",
        ],
    )
    page = PAGE.read_text(encoding="utf-8")
    count = report["facet_counts"]["must-support"]
    assert count == 106
    assert f"共有 {count} 個 `mustSupport = true`" in page
