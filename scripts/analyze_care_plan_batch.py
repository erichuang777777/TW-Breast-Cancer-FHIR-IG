from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qbc_workbench.care_plan_batch import analyze_care_plan_batch  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a PHI-free aggregate audit of private cancer care-plan FHIR transforms."
    )
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=Path("qbc_workbench/data/cancer_care_plan_field_catalog.json"),
    )
    args = parser.parse_args()
    report = analyze_care_plan_batch(args.source_dir, args.bundle_dir, args.catalog)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "source_files": report["source_files"],
                "parsed_records": report["parsed_records"],
                "bundle_invalid": report["bundle_invalid"],
                "mapping_item_count_mismatches": report["mapping_item_count_mismatches"],
                "contains_case_identifiers": report["contains_case_identifiers"],
                "contains_source_values": report["contains_source_values"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
