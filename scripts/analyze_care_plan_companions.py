from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from openpyxl import Workbook
from openpyxl.styles import Font

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qbc_workbench.care_plan_companion_audit import analyze_companions  # noqa: E402


def _flatten(prefix: str, value: object, rows: list[tuple[str, object]]) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            _flatten(f"{prefix}.{key}" if prefix else key, nested, rows)
    else:
        rows.append((prefix, json.dumps(value, ensure_ascii=False) if isinstance(value, list) else value))


def _write_workbook(report: dict, path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Aggregate Audit"
    sheet.append(["Metric", "Value"])
    for cell in sheet[1]:
        cell.font = Font(name="Arial", bold=True)
    rows: list[tuple[str, object]] = []
    _flatten("", report, rows)
    for metric, value in rows:
        sheet.append([metric, value])
    for column in sheet.columns:
        for cell in column:
            cell.font = Font(name="Arial", bold=cell.row == 1)
    sheet.column_dimensions["A"].width = 58
    sheet.column_dimensions["B"].width = 22
    workbook.save(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare private care-plan JSON, XLSX and PDF companions.")
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output_json", type=Path)
    parser.add_argument("output_xlsx", type=Path)
    args = parser.parse_args()
    report = analyze_companions(args.source_dir)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_workbook(report, args.output_xlsx)
    print(
        json.dumps(
            {
                "matched": report["matched_json_xlsx_pdf"],
                "unreadable": report["unreadable"],
                "contains_case_identifiers": report["contains_case_identifiers"],
                "contains_source_values": report["contains_source_values"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
