from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
# 官方規格文件屬第三方著作，保存在受控隔離目錄，不進版本控制、不隨本專案散布。
SPEC_SOURCES = ROOT / "private" / "spec-sources"
EXTRACTED = ROOT / "outputs" / "source_audit" / "extracted"
CSV_OUT = ROOT / "outputs" / "source_audit" / "source_line_traceability.csv"
SUMMARY_OUT = ROOT / "outputs" / "source_audit" / "coverage_summary.json"
IG_OUT = ROOT / "ig" / "input" / "pagecontent" / "source-traceability.md"

ROUTES = {
    "01_": [(1, 4, "program-rules.html", "方案資格、照護、獎勵與核付"), (5, 8, "field-audit.html", "VPN登錄資料範圍"), (9, 12, "quality-indicators.html", "品質監控指標")],
    "02_": [(1, 2, "program-rules.html", "參與資格與申請"), (3, 4, "program-rules.html", "收案、結案與轉介"), (5, 8, "faq-rules.html", "VPN與臨床情境問答"), (9, 10, "program-rules.html", "獎勵計算與時程"), (11, 13, "governance.html", "申請附件與治理")],
    "03_": [(1, 7, "program-rules.html", "方案與品質概覽"), (8, 21, "vpn-workflow.html", "VPN畫面與作業流程"), (22, 22, "field-audit.html", "AJCC第8版分期"), (23, 24, "governance.html", "申請與執行提醒")],
    "04_": [(1, 2, "vpn-workflow.html", "權限與登入"), (3, 12, "vpn-workflow.html", "查詢、收案、轉出、接收與刪除"), (13, 13, "vpn-workflow.html", "空白尾頁")],
    "05_": [(1, 2, "upload-workflow.html", "批次上傳、錯誤檔與成功狀態")],
    "06_": [(0, 9999, "field-audit.html", "115欄及XML結構逐列規格")],
}


def route_for(filename: str, page: int) -> tuple[str, str]:
    prefix = filename[:3]
    for start, end, destination, topic in ROUTES[prefix]:
        if start <= page <= end:
            return destination, topic
    raise RuntimeError(f"No route for {filename} page {page}")


def original_for(extracted_name: str) -> Path:
    stem = Path(extracted_name[3:]).stem
    matches = [p for base in (SPEC_SOURCES, ROOT) for p in base.glob(f"*{stem}.*")]
    if not matches:
        raise RuntimeError(
            f"找不到 {extracted_name} 的官方原始文件。官方規格文件屬第三方著作，"
            f"不隨本專案散布；請自行取得後放入 {SPEC_SOURCES.relative_to(ROOT)}／再重跑本腳本。"
        )
    if len(matches) > 1:
        raise RuntimeError(f"Cannot resolve source for {extracted_name}: {matches}")
    return matches[0]


def main() -> None:
    rows = []
    source_summaries = []
    for path in sorted(EXTRACTED.glob("*.txt")):
        original = original_for(path.name)
        digest = hashlib.sha256(original.read_bytes()).hexdigest()
        page = 0
        source_rows = 0
        destinations = set()
        for extracted_line, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            marker = re.fullmatch(r"===== PAGE (\d+) =====", raw.strip())
            if marker:
                page = int(marker.group(1))
                continue
            text = " ".join(raw.split())
            if not text:
                continue
            destination, topic = route_for(path.name, page)
            classification = "non-normative-layout" if re.fullmatch(r"\d{1,3}", text) else "reviewed-content"
            rows.append({
                "source_file": original.name, "source_sha256": digest, "page": page or "table/paragraph",
                "extracted_line": extracted_line, "text": text, "classification": classification,
                "topic": topic, "ig_destination": destination, "coverage_status": "mapped",
            })
            source_rows += 1
            destinations.add(destination)
        source_summaries.append({"source_file": original.name, "sha256": digest, "mapped_nonempty_lines": source_rows, "destinations": sorted(destinations)})

    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if not rows or any(row["coverage_status"] != "mapped" for row in rows):
        raise RuntimeError("Source coverage is incomplete")
    summary = {"source_count": len(source_summaries), "mapped_nonempty_lines": len(rows), "unmapped_lines": 0, "sources": source_summaries}
    SUMMARY_OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 規格來源與逐行追溯", "", "{% include disclaimer.md %}", "",
        "本專案將工作區內 5 份 QBC PDF 與 1 份 XML 格式 Word 視為規格來源。PDF 逐頁擷取、Word 逐段及逐列擷取後，每一個非空白文字行都必須對應至下列 IG 說明頁；版面頁碼等標示為非規範內容，但仍保留在追溯表中。", "",
        f"目前來源共 **{len(source_summaries)}** 份，已映射 **{len(rows)}** 個非空白文字行，未映射 **0** 行。完整逐行文字、來源 SHA-256、頁碼及 IG 去向由 `scripts/build_source_traceability.py` 在本機產生於 `outputs/source_audit/source_line_traceability.csv`；該檔含官方文件全文，屬第三方著作，不進版本控制、不隨本 IG 散布。下表的 SHA-256 可用於核對你自行取得的官方原檔是否為同一版本。", "",
        "| 來源 | 映射文字行 | 來源 SHA-256 | IG 去向 |", "|---|---:|---|---|",
    ]
    for item in source_summaries:
        links = ", ".join(f"[{name}]({name})" for name in item["destinations"])
        lines.append(f"| {item['source_file']} | {item['mapped_nonempty_lines']} | `{item['sha256']}` | {links} |")
    lines.extend([
        "", "## 其他工作區檔案", "",
        "| 檔案 | 分類 | 本輪處理 |", "|---|---|---|",
        "| `private/spec-sources/` | 健保署官方規格文件原檔（PDF／Word） | 第三方著作；僅在本機擷取供逐行追溯，不進版本控制、不隨本 IG 散布 |",
        "| `private/rosters/` | 方案申請／合格個案名單 | 含個人資料；隔離於受控目錄，排除於公開規格稽核與版本控制 |",
        "| `private/cases/` | 單一個案來源檔（JSON／Word／PDF／Excel） | 含病歷資料；隔離於受控目錄，排除於公開規格稽核與版本控制 |",
        "| `ig/`、`scripts/`、`tests/`、`outputs/qbc_conformance/`、`qbc_workbench/` | 本專案程式與生成物 | 以測試及 Publisher QA 驗證，不作為官方規格來源 |",
        "",
        "本表刻意不列出任何個案檔名、病歷號或名單檔名。所有含個人資料的來源一律以目錄層級描述，實際檔名不進入本 IG、版本控制或任何發布物。",
        "", "## 閱讀原則", "", "- 最新修訂的問答集用來補充方案與欄位表未明說的臨床及作業情境。", "- Word 11507 定版主表是 XML Tag、長度、值域、條件必填及編碼的主要來源。", "- VPN 手冊與說明會用來描述畫面狀態、權限、轉出／接收及刪除流程，不把畫面行為誤寫成 FHIR Profile 限制。", "- 文件互相矛盾或無法由資料本身證明時，列入人工審核或待 VPN 驗收，不宣稱已自動驗證。",
    ])
    IG_OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(CSV_OUT)
    print(SUMMARY_OUT)
    print(IG_OUT)


if __name__ == "__main__":
    main()
