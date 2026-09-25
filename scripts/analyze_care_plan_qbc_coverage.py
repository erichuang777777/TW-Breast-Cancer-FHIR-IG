from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qbc_workbench.care_plan_qbc_coverage import (  # noqa: E402
    analyze_care_plan_qbc_coverage,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a PHI-free aggregate Care Plan JSON to QBC coverage matrix."
    )
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--qbc-fields", type=Path, default=Path("qbc_workbench/data/qbc_fields.json")
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("qbc_workbench/data/cancer_care_plan_field_catalog.json"),
    )
    args = parser.parse_args()
    report = analyze_care_plan_qbc_coverage(
        args.source_dir, args.qbc_fields, args.catalog
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "source_files": report["source_files"],
                "parsed_records": report["parsed_records"],
                "qbc_field_count": report["qbc_field_count"],
                "produced_in_january_field_count": report[
                    "produced_in_january_field_count"
                ],
                "not_produced_in_january_field_count": report[
                    "not_produced_in_january_field_count"
                ],
                "coverage_status_counts": report["coverage_status_counts"],
                "diagnosis_type_counts": report["diagnosis_type_counts"],
                "contains_case_identifiers": report["contains_case_identifiers"],
                "contains_source_values": report["contains_source_values"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
