from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from qbc_workbench.care_plan_catalog import catalog_from_private_json  # noqa: E402


def render_markdown(catalog: dict) -> str:
    ownership_counts: dict[str, int] = {}
    for field in catalog["fields"]:
        ownership = field["ownership"]
        ownership_counts[ownership] = ownership_counts.get(ownership, 0) + 1

    rows = [
        "# 癌症診療計畫書欄位盤點／Cancer Care Plan Field Inventory",
        "",
        "> 本表只含表單控制項 metadata，不含個案值、病歷號、報告文字、來源雜湊或其他 PHI。",
        "",
        f"- Catalog version: `{catalog['catalog_version']}`",
        f"- Unique controls: **{catalog['field_count']}**",
        f"- Shared with QBC: **{ownership_counts.get('shared', 0)}**",
        f"- Care-plan-only: **{ownership_counts.get('care-plan-only', 0)}**",
        f"- Derived: **{ownership_counts.get('derived', 0)}**",
        "",
        "目前所有有值欄位都可無損保存在 QuestionnaireResponse；只有完成語意審查的欄位，才會逐步提升為共用 Condition、Observation、DiagnosticReport、Procedure 或 MedicationRequest。",
        "",
        "| ID | Section | Control key | Type | Ownership | QBC target | Candidate FHIR path | Review |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for field in catalog["fields"]:
        rows.append(
            "| {field_id} | {section} | `{control_key}` | {types} | {ownership} | {qbc} | `{path}` | {status} |".format(
                field_id=field["field_id"],
                section=field["section"],
                control_key=field["control_key"].replace("|", "\\|"),
                types=", ".join(field["input_types"]).replace("|", "\\|") or "—",
                ownership=field["ownership"],
                qbc=", ".join(field["qbc_targets"]) or "—",
                path=field["fhir_path"].replace("|", "\\|"),
                status=field["review_status"],
            )
        )
    rows.extend(
        [
            "",
            "## 審查原則",
            "",
            "- `implemented-partial`：已有 Care Plan／QBC 重疊欄位的 alignment check，但 common FHIR Profile 與術語仍須逐欄簽核。",
            "- `pending-field-review`：目前只承諾完整保存來源答案，尚未宣告為標準化臨床事實。",
            "- `pending-algorithm-review`：衍生欄位必須補上算法、版本、輸入與人工覆核規則。",
            "",
        ]
    )
    return "\n".join(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a PHI-free cancer care-plan field catalog")
    parser.add_argument("source", type=Path, help="Private *.case.json source")
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("qbc_workbench/data/cancer_care_plan_field_catalog.json"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("ig/input/pagecontent/care-plan-field-inventory.md"),
    )
    args = parser.parse_args()

    catalog = catalog_from_private_json(args.source)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.markdown_output.write_text(render_markdown(catalog), encoding="utf-8")
    print(json.dumps({"fields": catalog["field_count"], "contains_phi": False}))


if __name__ == "__main__":
    main()
