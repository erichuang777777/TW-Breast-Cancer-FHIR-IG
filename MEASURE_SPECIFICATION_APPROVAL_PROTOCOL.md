# Measure 規格核准證據規範

本規範定義 RC-07 對 20 個 Measure 的人工核准證據。核准的是「當次實際可執行規格」，不是相同檔名、舊版會議紀錄或只有摘要的文件。

## 每個 Measure 的七個鎖定元件

`scripts/audit_measure_specification_approvals.py` 會對每個 Measure 重算：

1. `case-management-measures.fsh` 完整檔案 SHA-256；
2. `BreastCancerCaseManagement.cql` 完整檔案 SHA-256；
3. 該 Measure 生成後 FHIR JSON 的 canonical JSON SHA-256；
4. `case-management-measure-catalog.csv` 該列的 canonical SHA-256；
5. 該 Measure 自有 criteria 加上同 family 共用 criteria 的 canonical SHA-256；
6. `case-management-measure-audit.csv` 該列的 canonical SHA-256；
7. approval id、scope、known issues、required signer 與 acceptance evidence 的 canonical SHA-256。

七個 hash 再組成 `specification_fingerprint`。任何 CQL、FSH、criteria、已知差異或核准範圍變更，都會使舊 bundle 失效；共用 FSH/CQL 變更會保守地使全部 20 筆重新核准。

## 核准 bundle

核准列的 `evidence_uri_path` 必須指向 `mappings/publication/evidence/` 下的 JSON bundle，清冊 SHA-256 必須等於 bundle 原始 bytes。bundle 必須包含：

- `schema_version = 1.0`、正確 `measure_id`；
- 七個 `component_hashes` 與由它們重算的 `specification_fingerprint`；
- 與 FSH 完全相等的 `reviewed_expression_ids`；
- 與該 Measure 適用 criteria 完全相等的 `reviewed_criterion_ids`；
- 與清冊 known issues 完全同集合的 resolution，每項均有 resolution 與 evidence；
- `unresolved_issue_count = 0`；
- 與清冊 signer、organization/title、decision date 相符的 reviewer identity 與含 timezone 的 `reviewed_at`；
- 獨立 truth-table JSON 的 repository-relative path 與實檔 SHA-256。

## Truth table 門檻

每個 truth case 必須有：抽象 `case_id`、`criterion_id`、布林 `expected_result`、`boundary_class` 與非空 rationale。禁止未知 criterion 或重複 `(case_id, criterion_id)`。

每個 Measure 適用的每個 criterion，至少必須各有：

- 一筆 `expected_result = true`；
- 一筆 `expected_result = false`。

目前 68 個唯一 criteria 中有 4 個 family 共用 criteria；展開到各 Measure 後為 104 個 Measure×criterion 使用點，因此最低門檻是 **208 個正／負 truth assertions**。這是規格核准的最低真值表，不取代 RC-04 的可執行邊界測試、RC-05 的獨立逐案重算或 RC-06 的原始資料 golden cohort。

## 通過條件

- inventory：20 Measure、68 unique criteria、62 Measure-expression uses；
- approved live bundles：20/20；
- unresolved known issues：0；
- truth assertions：至少 208，且每個 Measure×criterion 的 true/false 集合完整；
- 所有 bundle、truth table 與 component hash 均與當次 repository／生成結果一致。

目前為 0/20，故 RC-07 仍為 blocked。
