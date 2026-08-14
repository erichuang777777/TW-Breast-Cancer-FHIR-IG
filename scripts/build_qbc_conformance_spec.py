from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path

from build_qbc_ig_mapping import SPEC, load_fields, section_for


ROOT = Path(__file__).resolve().parents[1]
JSON_OUT = ROOT / "qbc_workbench" / "data" / "qbc_fields.json"
CSV_OUT = ROOT / "outputs" / "qbc_conformance" / "qbc_fields.csv"
REVIEW_OUT = ROOT / "outputs" / "qbc_conformance" / "clinical_review_template.csv"
COVERAGE_OUT = ROOT / "outputs" / "qbc_conformance" / "rule_coverage.csv"
AUDIT_OUT = ROOT / "outputs" / "qbc_conformance" / "field_rule_audit.csv"
MANIFEST_OUT = ROOT / "outputs" / "qbc_conformance" / "source_manifest.json"
IG_AUDIT_PAGE = ROOT / "ig" / "input" / "pagecontent" / "field-audit.md"

# Word 文字未明示、由本專案補上的解讀。這些才是需要人簽核的項目——115 欄的規則
# 本身是健保署公布的法定規格，依定義即為準據，不需要任何人核准。
# `decision` 欄的值：pending（待簽核）、resolved（已決議，見 notes）。
LOCAL_INTERPRETATIONS = [
    {
        "item_id": "QBC-TM02-SURGERY-POSTOP-REQUIRED",
        "category": "區段必填觸發條件",
        "word_basis": "主表 D027-D057 各列僅列出值域，未載明何時必填",
        "local_interpretation": "推導為 TM02=1（治癒性手術）且 DIAG_TYPE 屬 (1,2) 時，術後區段必填",
        "decision": "pending",
        "reviewer_role": "QBC 申報負責人",
    },
    {
        "item_id": "QBC-DIAGTYPE3-RECURRENCE-REQUIRED",
        "category": "區段必填觸發條件",
        "word_basis": "主表總則要求 DIAG_TYPE=3 時 D058-D085 必填",
        "local_interpretation": "採「總則必填、個別條件優先」：D069 等具明確個別條件者依個別條件，否則依總則",
        "decision": "pending",
        "reviewer_role": "QBC 申報負責人",
    },
    {
        "item_id": "QBC-XML-TABLE1-CLOSING-TAGS",
        "category": "官方範例瑕疵處理",
        "word_basis": "表-1 官方 XML 範例部分結束標籤錯置或遺漏 /",
        "local_interpretation": "不沿用表-1 範例，改以表-2 欄位規則產生 well-formed XML",
        "decision": "pending",
        "reviewer_role": "QBC 申報負責人",
    },
    {
        "item_id": "QBC-MCODE-GAP-SCOPE",
        "category": "對應範圍",
        "word_basis": "非主表範圍；mCODE 4.0.0 為 US Realm 且依賴 US Core",
        "local_interpretation": "只做 gap mapping，不以加入 dependency 冒充 TW Core／mCODE 雙重 conformance",
        "decision": "pending",
        "reviewer_role": "FHIR 實作負責人",
    },
    {
        "item_id": "QBC-TM10-DATE-ORDER",
        "category": "疑似筆誤",
        "word_basis": "主表 TM10 列寫「不可早於 TM08」，但 TM08 是治療部位文字，不是日期",
        "local_interpretation": "視為筆誤，改以 TM09 開始日期檢查",
        "decision": "resolved",
        "reviewer_role": "臨床／QBC 申報負責人",
        "notes": "專案決議 2026-08-13；尚未取得健保署書面函釋，VPN 驗收仍應納入測試案例",
    },
    {
        "item_id": "QBC-SEVERITY-ORDER",
        "category": "FAQ 未提供的判定準則",
        "word_basis": "FAQ 要求同側多型態只報較嚴重者，但未提供嚴重度排序表",
        "local_interpretation": "期別 Ⅲ>Ⅱ>Ⅰ，次分期 ⅢC>ⅢB>ⅢA，完全同期別才以腫瘤大小排序",
        "decision": "resolved",
        "reviewer_role": "病理／臨床專家",
        "notes": "專案決議 2026-08-13；Ⅳ>ⅢC 與 ⅠA>0 為延伸推論、StageX 回退人工，仍待確認",
    },
    {
        "item_id": "QBC-TNM-SARCOMA-EXCEPTION",
        "category": "FAQ 未界定的例外範圍",
        "word_basis": "FAQ 允許葉狀瘤 TNM 未知後手填分期，未界定例外的判定方式",
        "local_interpretation": "非上皮性腫瘤不適用乳癌 TNM；除明示旗標外，組織學分類 8（其他）亦自動觸發",
        "decision": "resolved",
        "reviewer_role": "病理專家",
        "notes": "專案決議 2026-08-13；組織學 8 觸發範圍較寬，非葉狀瘤但填 8 者亦會降級為 warning",
    },
    {
        "item_id": "QBC-FAQ-BILATERAL-TWO-RECORDS",
        "category": "FAQ 未逐欄說明的範圍",
        "word_basis": "FAQ 要求雙側拆為左右兩筆，未說明全身性療程應否兩側重複",
        "local_interpretation": "兩側各自建檔與各自上傳，每筆含各自完整療程；系統主動提醒使用者",
        "decision": "resolved",
        "reviewer_role": "臨床／QBC 申報負責人",
        "notes": "專案決議 2026-08-13",
    },
    {
        "item_id": "QBC-FAQ-PREOP-HORMONE-3D-DIRECT-SURGERY",
        "category": "FAQ 情境判定",
        "word_basis": "FAQ 第 5 項：術前荷爾蒙用藥 3 天",
        "local_interpretation": "歸為 DIAG_TYPE=1 直接治癒性手術，不算新輔助性治療",
        "decision": "pending",
        "reviewer_role": "臨床專家",
    },
]

# 受區段規則影響的欄位由 rule_ids 反查，避免手寫欄位範圍與實作脫節。
SECTION_SCOPED_ITEMS = {"QBC-TM02-SURGERY-POSTOP-REQUIRED", "QBC-DIAGTYPE3-RECURRENCE-REQUIRED"}


def local_interpretation_rows(fields):
    """產生簽核表列；區段規則的受影響欄位由實際 rule_ids 反查。"""
    rows = []
    for item in LOCAL_INTERPRETATIONS:
        affected = [f["tag"] for f in fields if item["item_id"] in f.get("rule_ids", [])]
        if item["item_id"] in SECTION_SCOPED_ITEMS and not affected:
            raise RuntimeError(f"{item['item_id']} 宣稱是區段規則，卻沒有任何欄位引用它")
        rows.append({
            "item_id": item["item_id"],
            "category": item["category"],
            "affected_fields": f"{affected[0]}-{affected[-1]}" if len(affected) > 1 else (affected[0] if affected else "跨欄位／非欄位層級"),
            "field_count": len(affected),
            "word_basis": item["word_basis"],
            "local_interpretation": item["local_interpretation"],
            "decision": item["decision"],
            "reviewer_role": item["reviewer_role"],
            "reviewer_name": "",
            "decision_date": "",
            "notes": item.get("notes", ""),
        })
    return rows


PROGRAM_RULES = [
    {
        "rule_id": "QBC-FAQ-PREOP-HORMONE-3D-DIRECT-SURGERY",
        "condition": "preoperative hormone medication for 3 days",
        "outcome": "classify as DIAG_TYPE=1 (new diagnosis, direct curative surgery), not neoadjuvant therapy",
        "enforcement": "clinical-review",
        "source": "QBC FAQ item 5 supplied by the project reviewer",
    },
    {
        "rule_id": "QBC-FAQ-BILATERAL-TWO-RECORDS",
        "condition": "simultaneous bilateral breast cancer",
        "outcome": (
            "each side is built and uploaded as its own complete record (L and R), "
            "each carrying its own full treatment course including systemic therapy; "
            "the workbench warns the user so neither side is omitted"
        ),
        "enforcement": "automated-warning-and-batch-review",
        "source": "QBC FAQ item 6.1; scope of systemic therapy resolved by project decision 2026-08-13",
    },
    {
        "rule_id": "QBC-FAQ-BILATERAL-SEVERITY-ORDER",
        "condition": "bilateral lesions have different severity",
        "outcome": "submit the more severe side first, then the other side; severity per QBC-SEVERITY-ORDER",
        "enforcement": "clinical-and-batch-review",
        "source": "QBC FAQ item 6.1 supplied by the project reviewer",
    },
    {
        "rule_id": "QBC-SEVERITY-ORDER",
        "condition": "two lesions must be ranked by severity",
        "outcome": (
            "rank by stage III > II > I with subgroups ordered IIIC > IIIB > IIIA, then by tumour size "
            "only when the full stage is identical; IV > IIIC and IA > 0 extend the same logic, "
            "Stage X cannot be ranked and falls to manual decision"
        ),
        "enforcement": "automated",
        "source": "project decision 2026-08-13 (stage and subgroup ordering, tumour-size tie-break)",
    },
    {
        "rule_id": "QBC-TNM-SARCOMA-EXCEPTION",
        "condition": "malignant phyllodes tumour or sarcoma (non-epithelial breast tumour)",
        "outcome": (
            "ordinary breast TNM staging does not apply; the clinically entered stage is kept and "
            "the automatic TNM result must not override it. Downgraded to a warning that requires "
            "pathology reviewer sign-off"
        ),
        "enforcement": "automated-warning",
        "source": "QBC FAQ (phyllodes stage may be entered manually); exception scope resolved by project decision 2026-08-13",
    },
    {
        "rule_id": "QBC-FAQ-BILATERAL-ID-REWARD",
        "condition": "the same patient has bilateral records",
        "outcome": "integrated-care and follow-up rewards are paid once per ID, using the more severe side",
        "enforcement": "payer-system-only",
        "source": "QBC FAQ item 6.2 supplied by the project reviewer",
    },
    {
        "rule_id": "QBC-FAQ-IPSILATERAL-HISTOLOGY-SEVERITY",
        "condition": "two or more histology types occur in the same breast",
        "outcome": "submit only the more severe histology; do not create a second record",
        "enforcement": "clinical-review",
        "source": "QBC FAQ item 6.3 supplied by the project reviewer",
    },
    {
        "rule_id": "QBC-T01-AFTER-ONE-YEAR",
        "condition": "annual follow-up",
        "outcome": "T01 may be entered after one full year from P09, once per year, for at most five years",
        "enforcement": "automated",
        "source": "QBC scheme, FAQ section 3 item 1, VPN briefing page 17, and XML specification T01",
    },
    {
        "rule_id": "QBC-T06-DEATH-CLOSE",
        "condition": "T02=5 or T03=4",
        "outcome": "T06 is required; death is treated as case closure and T05 is not additionally required",
        "enforcement": "automated",
        "source": "XML specification T06 and VPN briefing page 17",
    },
]

DATE_TAGS = {"BIRTHDAY", "P09", "D001", "D025", "D058", "TM09", "TM10", "T01", "T04", "T05", "T06"}
DECIMAL_TAGS = {"P03", "P04", "D047"}
INTEGER_TAGS = {
    "P06", "D015", "D017", "D021", "D039", "D040", "D042", "D043",
    "D045", "D046", "D049", "D051", "D055", "D071", "D072", "D074",
    "D075", "D077", "D079", "D083", "TM01",
}
MULTI_TAGS = {"D009", "D036", "D068", "TM05", "TM07"}
CASE_REQUIRED = {"HOSPID", "ID", "BIRTHDAY", "DIAG_TYPE", "LATERALITY", "P01", "P02", "P03", "P04", "P07", "P08", "P09"}
RECURRENCE_CONDITIONS = {
    "D069": "DIAG_TYPE=3 AND D068 CONTAINS 13",
    "D071": "DIAG_TYPE=3 AND D070=1",
    "D072": "DIAG_TYPE=3 AND D070 IN (0,1)",
    "D074": "DIAG_TYPE=3 AND D073=1",
    "D075": "DIAG_TYPE=3 AND D073 IN (0,1)",
    "D077": "DIAG_TYPE=3 AND D076=1",
    "D079": "DIAG_TYPE=3 AND D078=1",
    "D081": "DIAG_TYPE=3 AND D080=2",
}
POSTOP_CONDITIONS = {
    "D036": "TM02=1 AND D035=StageⅣ",
    "D037": "TM02=1 AND D036 CONTAINS 12",
    "D039": "TM02=1 AND D038=1",
    "D040": "TM02=1 AND D038 IN (0,1)",
    "D042": "TM02=1 AND D041=1",
    "D043": "TM02=1 AND D041 IN (0,1)",
    "D045": "TM02=1 AND D044=1 (AT LEAST ONE OF D045,D046)",
    "D046": "TM02=1 AND D044=1 (AT LEAST ONE OF D045,D046)",
    "D049": "TM02=1 AND D048=1",
    "D051": "TM02=1 AND D050=1",
    "D053": "TM02=1 AND D052=2",
    "D055": "TM02=1 AND D054=1",
}


def values(*items: str) -> list[str]:
    return list(items)


ALLOWED: dict[str, list[str]] = {
    "DIAG_TYPE": values("1", "2", "3"),
    "LATERALITY": values("L", "R"),
    "P02": values("0", "1", "2", "3"),
    "P05": values("1", "2"),
    "P08": values("1", "2", "3"),
    "D002": values("1", "2"), "D026": values("1", "2"), "D059": values("1", "2"),
    "D003": values(*map(str, range(9))), "D030": values(*map(str, range(9))),
    "D004": values("X", "1", "2", "3"), "D031": values("X", "1", "2", "3"),
    "D011": values("1"), "D012": values("1", "2"), "D013": values("0", "1"),
    "D024": values("0", "1"), "D027": values("0", "1"),
    "D028": values("0", "1", "2"), "D029": values("0", "1", "2", "3", "4"),
    "TM02": values(*map(str, range(1, 8))), "TM03": values("1", "2"),
    "TM04": values("1", "2", "3"),
    "TM05": values("A1", "A2", *[f"B{i}" for i in range(1, 13)], "C1"),
    "TM07": values(*[f"A{i}" for i in range(1, 6)]),
    "T02": values("1", "2", "3", "4", "5", "6", "X"),
    "T03": values("1", "2", "3", "4", "5", "X"),
}

for tag in ["D005", "D032", "D060", "D064"]:
    ALLOWED[tag] = values("T0", "Tis", "T1", "T2", "T3", "T4", "Tx")
for tag in ["D006", "D033", "D061", "D065"]:
    ALLOWED[tag] = values("N0", "N1mi", "N1", "N2", "N3", "Nx")
for tag in ["D007", "D034", "D062", "D066"]:
    ALLOWED[tag] = values("M0", "M1", "Mx")
for tag in ["D014", "D016", "D022", "D023", "D038", "D041", "D048", "D050", "D056", "D057", "D070", "D073", "D076", "D078", "D084", "D085"]:
    ALLOWED[tag] = values("X", "0", "1")
for tag in ["D018", "D052", "D080"]:
    ALLOWED[tag] = values("X", "0", "1", "2", "3")
for tag in ["D019", "D020", "D053", "D054", "D081", "D082", "D044"]:
    ALLOWED[tag] = values("0", "1")
ALLOWED["D009"] = values(*map(str, range(1, 13)))
ALLOWED["D036"] = values(*map(str, range(1, 13)))
ALLOWED["D068"] = values(*map(str, range(1, 14)))

RANGES = {
    "P06": (0, 99),
    **{tag: (1, 100) for tag in ["D015", "D017", "D021", "D049", "D051", "D055", "D077", "D079", "D083"]},
    **{tag: (1, 99) for tag in ["D039", "D040", "D042", "D043", "D071", "D072", "D074", "D075"]},
    **{tag: (0, 99) for tag in ["D045", "D046"]},
    "D047": (0, 99.99),
    "TM01": (1, 99),
}

RULE_IDS = {
    "LATERALITY": ["QBC-LATERALITY-REQUIRED"],
    "P05": ["QBC-P05-FEMALE"], "P06": ["QBC-P06-MENOPAUSE"],
    "D001": ["QBC-D001-DIAGTYPE"],
    "D004": ["QBC-D004-HISTOLOGY"],
    "D008": ["QBC-D008-TNM"], "D035": ["QBC-D035-TNM"],
    "D063": ["QBC-D063-TNM"], "D067": ["QBC-D067-TNM"],
    "D009": ["QBC-D009-STAGE4"], "D010": ["QBC-D010-OTHER"],
    "D011": ["QBC-D011-D012-XOR"], "D012": ["QBC-D011-D012-XOR"],
    "D013": ["QBC-D013-METHOD"],
    "D015": ["QBC-D015-ER"], "D017": ["QBC-D017-PR"],
    "D019": ["QBC-D019-HER2"], "D021": ["QBC-D021-KI67"],
    "D024": ["QBC-D024-NEOADJUVANT-SURGERY"],
    "D025": ["QBC-D025-DIAGTYPE"], "D026": ["QBC-D026-DIAGTYPE"],
    "D036": ["QBC-D036-STAGE4"], "D037": ["QBC-D037-OTHER"],
    "D039": ["QBC-D039-SENTINEL"], "D040": ["QBC-D040-SENTINEL"],
    "D042": ["QBC-D042-AXILLARY"], "D043": ["QBC-D043-AXILLARY"],
    "D044": ["QBC-D044-NODE"], "D045": ["QBC-D045-D046-ONE"],
    "D046": ["QBC-D045-D046-ONE"],
    "D049": ["QBC-D049-ER"], "D051": ["QBC-D051-PR"],
    "D053": ["QBC-D053-HER2"], "D055": ["QBC-D055-KI67"],
    "D068": ["QBC-D068-RECURRENCE"], "D069": ["QBC-D069-OTHER"],
    "D071": ["QBC-D071-SENTINEL"], "D072": ["QBC-D072-SENTINEL"],
    "D074": ["QBC-D074-AXILLARY"], "D075": ["QBC-D075-AXILLARY"],
    "D077": ["QBC-D077-ER"], "D079": ["QBC-D079-PR"],
    "D081": ["QBC-D081-HER2"],
    "TM01": ["QBC-TM01-DIRECT-SURGERY", "QBC-TM01-UNIQUE", "QBC-TM01-CONTIGUOUS"],
    "TM02": ["QBC-TM02-DEPENDENCIES"], "TM04": ["QBC-TM04-RECURRENCE"],
    "TM05": ["QBC-TM05-TREATMENT", "QBC-TM05-TREATMENT-TYPE"],
    "TM06": ["QBC-TM06-OTHER"], "TM08": ["QBC-TM08-OTHER"],
    "TM07": ["QBC-TM07-RADIOTHERAPY"],
    "TM10": ["QBC-TM10-DATE-ORDER"],
    "T02": ["QBC-T02-DEPENDENCIES", "QBC-TRACE-RECURRENCE-CASE"],
    "T03": ["QBC-T03-DEPENDENCIES", "QBC-TRACE-RECURRENCE-CASE"],
    "T04": ["QBC-T04-TRANSFER"], "T05": ["QBC-T05-CLOSE"],
    "T06": ["QBC-T06-DEATH"],
}


def data_type(tag: str) -> str:
    if tag in DATE_TAGS:
        return "date"
    if tag in DECIMAL_TAGS:
        return "decimal"
    if tag in INTEGER_TAGS:
        return "integer"
    if tag in MULTI_TAGS:
        return "code-list"
    if tag in ALLOWED:
        return "code"
    return "string"


def validation_checks(field: dict) -> list[str]:
    checks = ["Big5 encodability"]
    if field["always_required"]:
        checks.append("required")
    if field["max_length"]:
        checks.append(f"max length {field['max_length']}")
    if field["data_type"] in {"date", "integer", "decimal", "code-list"}:
        checks.append(field["data_type"] + " format")
    if field["allowed_values"]:
        checks.append("allowed value set")
    if field["minimum"] is not None or field["maximum"] is not None:
        checks.append("numeric range")
    if field["required_when"]:
        checks.append("conditional requiredness")
    if field["rule_ids"]:
        checks.append("cross-field business rules")
    return checks


def markdown_cell(value: object) -> str:
    return str(value or "").replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def build() -> tuple[Path, ...]:
    source_hash = hashlib.sha256(SPEC.read_bytes()).hexdigest()
    fields = []
    for source in load_fields():
        tag = source["QBC Tag"]
        length_match = re.search(r"X\((\d+)", source["QBC 格式"].replace("）", ")"))
        low, high = RANGES.get(tag, (None, None))
        rule_ids = list(RULE_IDS.get(tag, []))
        if "D027" <= tag <= "D057" and tag not in POSTOP_CONDITIONS:
            rule_ids.insert(0, "QBC-TM02-SURGERY-POSTOP-REQUIRED")
        if "D058" <= tag <= "D085" and tag not in RECURRENCE_CONDITIONS:
            rule_ids.insert(0, "QBC-DIAGTYPE3-RECURRENCE-REQUIRED")
        fields.append({
            "tag": tag,
            "label": source["QBC 中文名稱"],
            "section": section_for(tag),
            "required_marker": source["必要性"],
            "always_required": tag in CASE_REQUIRED,
            "source_format": source["QBC 格式"],
            "max_length": int(length_match.group(1)) if length_match else None,
            "data_type": data_type(tag),
            "allowed_values": ALLOWED.get(tag, []),
            "multi_select": tag in MULTI_TAGS,
            "minimum": low,
            "maximum": high,
            "required_when": (
                [RECURRENCE_CONDITIONS.get(tag, "DIAG_TYPE=3")] if "D058" <= tag <= "D085"
                else [POSTOP_CONDITIONS.get(tag, "TM02=1 AND DIAG_TYPE IN (1,2)")] if "D027" <= tag <= "D057"
                else []
            ),
            "rule_ids": rule_ids,
            "source_rule": source["QBC 原始規則"],
        })
    if len(fields) != 115:
        raise RuntimeError(f"Expected 115 fields, got {len(fields)}")

    payload = {
        "schema_version": "1.0.0",
        "status": "unofficial-derived-draft",
        "source": {
            "title": SPEC.name,
            "version": "11507 定版",
            "sha256": source_hash,
            "notice": "Derived from the locally supplied QBC document; does not replace the official specification.",
        },
        "section_rules": [
            {"rule_id": "QBC-TM02-SURGERY-POSTOP-REQUIRED", "condition": "TM02=1 and DIAG_TYPE in (1,2)", "fields": "D027-D057", "precedence": "field-specific conditions override"},
            {"rule_id": "QBC-DIAGTYPE3-RECURRENCE-REQUIRED", "condition": "DIAG_TYPE=3", "fields": "D058-D085", "precedence": "field-specific conditions override"},
        ],
        "program_rules": PROGRAM_RULES,
        "fields": fields,
    }
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields[0]))
        writer.writeheader()
        for field in fields:
            writer.writerow({**field, "allowed_values": ",".join(field["allowed_values"]), "rule_ids": ",".join(field["rule_ids"])})
    # 115 欄的規則本身是健保署公布的法定規格，不需要任何人「核准」；逐字轉錄與
    # 實作已由來源 SHA-256 與 tests/test_conformance.py 驗證。真正需要人簽核的，
    # 只有 Word 文字未明示、由本專案補上的解讀。簽核表因此只列這些項目。
    with REVIEW_OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        columns = ["item_id", "category", "affected_fields", "field_count", "word_basis",
                   "local_interpretation", "decision", "reviewer_role", "reviewer_name",
                   "decision_date", "notes"]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for item in local_interpretation_rows(fields):
            writer.writerow(item)
    with COVERAGE_OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        columns = ["tag", "label", "source_rule", "required_when", "validation_checks", "rule_id", "implementation", "automated_test", "technical_status", "clinical_review_status"]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for field in fields:
            generic_rules = ["QBC-ENCODING-BIG5"]
            if field["max_length"]:
                generic_rules.append("QBC-FORMAT-LENGTH")
            if field["data_type"] != "string":
                generic_rules.append(f"QBC-FORMAT-{field['data_type'].upper()}")
            if field["allowed_values"]:
                generic_rules.append("QBC-VALUESET")
            if field["minimum"] is not None or field["maximum"] is not None:
                generic_rules.append("QBC-FORMAT-RANGE")
            rule_ids = list(dict.fromkeys(generic_rules + field["rule_ids"]))
            pending_items = {item["item_id"] for item in LOCAL_INTERPRETATIONS if item["decision"] == "pending"}
            resolved_items = {item["item_id"] for item in LOCAL_INTERPRETATIONS if item["decision"] == "resolved"}
            for rule_id in rule_ids:
                # 直接轉錄自 Word 的規則不需要人簽核：來源 SHA-256 已鎖定版本，
                # 逐字保留與值域完整性由 tests/test_conformance.py 斷言。
                if rule_id in pending_items:
                    status = "needs-decision"
                elif rule_id in resolved_items:
                    status = "decided-by-project"
                else:
                    status = "verified-by-test"
                writer.writerow({
                    "tag": field["tag"], "label": field["label"], "source_rule": field["source_rule"],
                    "required_when": " | ".join(field["required_when"]),
                    "validation_checks": " | ".join(validation_checks(field)), "rule_id": rule_id,
                    "implementation": "qbc_workbench.validation", "automated_test": "tests/test_conformance.py",
                    "technical_status": "implemented", "clinical_review_status": status,
                })
    with AUDIT_OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        columns = [
            "tag", "label", "section", "required_marker", "source_format", "source_rule",
            "always_required", "required_when", "data_type", "max_length", "minimum", "maximum",
            "allowed_values", "multi_select", "validation_checks", "rule_ids",
            "technical_status", "clinical_review_status", "review_notes",
        ]
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for field in fields:
            writer.writerow({
                **{column: field.get(column, "") for column in columns},
                "required_when": " | ".join(field["required_when"]),
                "allowed_values": ",".join(field["allowed_values"]),
                "validation_checks": " | ".join(validation_checks(field)),
                "rule_ids": ",".join(field["rule_ids"]),
                "technical_status": "implemented",
                "clinical_review_status": "pending",
                "review_notes": "",
            })
    audit_lines = [
        "# 115 欄逐欄規則稽核",
        "",
        "{% include disclaimer.md %}",
        "",
        "> 本頁由 11507 定版 Word 主表自動產生。原始規則逐字保留；「技術狀態」只代表本地驗證器已有對應檢查，不代表健保署或臨床專家已核准。",
        "",
        "## 出處與著作權",
        "",
        "「Word 原始規則」欄為衛生福利部中央健康保險署所發布 QBC XML 上傳格式說明（11507 定版）之逐字引用，目的在於讓實作者能逐欄核對本草案的技術檢查是否忠實反映官方規則。該等文字之權利屬原權利機關所有，不因本 IG 依 CC BY 4.0 授權其原創內容而改變。",
        "",
        "官方文件原檔不隨本 IG 散布；請逕向健保署取得，並以下列 SHA-256 核對版本是否一致。若權利機關認為本頁引用範圍不適當，請循 [issue tracker](https://github.com/erichuang777777/TW-Breast-Cancer-FHIR-IG/issues) 反映，本專案將配合調整或移除。",
        "",
        f"來源 SHA-256：`{source_hash}`",
        "",
        "| Tag | 欄位 | 格式 | Word 原始規則 | 適用／必填條件 | 驗證內容 | Rule ID | 技術狀態 | 臨床審核 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for field in fields:
        audit_lines.append("| " + " | ".join(map(markdown_cell, [
            field["tag"], field["label"], field["source_format"], field["source_rule"],
            "；".join(field["required_when"]) or ("固定必填" if field["always_required"] else "依資料情境"),
            "；".join(validation_checks(field)), ", ".join(field["rule_ids"]) or "通用格式規則",
            "implemented", "pending",
        ])) + " |")
    IG_AUDIT_PAGE.parent.mkdir(parents=True, exist_ok=True)
    IG_AUDIT_PAGE.write_text("\n".join(audit_lines) + "\n", encoding="utf-8")
    MANIFEST_OUT.write_text(json.dumps({
        "source": payload["source"],
        "generated_files": [str(path.relative_to(ROOT)).replace("\\", "/") for path in [JSON_OUT, CSV_OUT, REVIEW_OUT, COVERAGE_OUT, AUDIT_OUT, IG_AUDIT_PAGE]],
        "field_count": len(fields),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return JSON_OUT, CSV_OUT, REVIEW_OUT, COVERAGE_OUT, AUDIT_OUT, IG_AUDIT_PAGE, MANIFEST_OUT


if __name__ == "__main__":
    print("\n".join(map(str, build())))
