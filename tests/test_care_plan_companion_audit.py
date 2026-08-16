import json
from pathlib import Path

from openpyxl import Workbook
from pypdf import PdfWriter

from qbc_workbench.care_plan_companion_audit import (
    _unmatched_cell_class,
    analyze_companions,
)


def test_companion_audit_is_aggregate_and_detects_structural_sources(tmp_path: Path):
    source = {
        "schema_version": "synthetic",
        "sections": {
            "basic": {
                "fields": [
                    {"name": "Synthetic$control", "type": "text", "value": "KNOWN"}
                ]
            }
        },
    }
    (tmp_path / "PRIVATE.case.json").write_text(json.dumps(source), encoding="utf-8")
    workbook = Workbook()
    workbook.active["A1"] = "KNOWN"
    workbook.active["A2"] = "DOCUMENT-ONLY"
    workbook.save(tmp_path / "PRIVATE.xlsx")
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    with (tmp_path / "PRIVATE.pdf").open("wb") as handle:
        writer.write(handle)

    report = analyze_companions(tmp_path)
    serialized = json.dumps(report)

    assert report["matched_json_xlsx_pdf"] == 1
    assert report["json"]["union_controls"] == 1
    assert report["xlsx"]["sheets_per_workbook"] == {"min": 1, "median": 1, "max": 1}
    assert report["contains_case_identifiers"] is False
    assert report["contains_source_values"] is False
    assert "DOCUMENT-ONLY" not in serialized
    assert "PRIVATE" not in serialized


def test_unmatched_cell_classification_does_not_return_source_text():
    assert _unmatched_cell_class("2026/01/15", "CASE") == "date-like"
    assert _unmatched_cell_class("A12345", "CASE") == "code-or-numeric-like"
    assert _unmatched_cell_class("合成敘述內容", "CASE") == "narrative-or-heading-like"
