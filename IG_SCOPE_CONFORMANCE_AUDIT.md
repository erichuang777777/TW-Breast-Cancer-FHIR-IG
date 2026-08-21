# 全 IG 範圍與 Conformance 宣稱稽核

本文件防止把某一個 Task 的技術成果擴張成整份 IG、外部標準或正式申報的正確性宣稱。機器可讀版本位於 [`mappings/publication/ig-scope-claim-register.csv`](mappings/publication/ig-scope-claim-register.csv)。

每個 claim 的發布角色決策另記於 [`mappings/publication/publication-scope-decision-register.csv`](mappings/publication/publication-scope-decision-register.csv)。固定的 10 個角色為：`IG-CORE`、`TASK-QBC`、`TASK-CASE-MGMT` 是 normative；TW Core、mCODE、ICHOM、Care Plan、TWPAS、TCR 是 informative；未來模組是 excluded。現況 **0/10 完成人工簽核**。角色、允許宣稱、禁止宣稱與 blocking evidence 都必須逐列簽核；不能刪除待辦列或把 normative 降為 informative 來通過 RC-08。除 `IG-CORE` 可保留 `technical-build-pass` 外，所有 normative Task 在正式發布前都必須達到 `formal-release-ready`。

逐一 artifact 的結構證據位於 [`mappings/publication/artifact-conformance-register.csv`](mappings/publication/artifact-conformance-register.csv)。完整集合是 **46 個 StructureDefinition（33 Profile＋13 Extension）**，不是只有 FSH 中的 42 個；另有 4 個手寫 TCR extension 也必須納管。機器稽核會逐列比對 generated `id`、`name`、FHIR `type`、`kind`、`baseDefinition`、`draft/experimental`、衍生關係及直接／衍生 Profile 或 extension-use 合成範例。現況 46/46 技術證據一致，但臨床／FHIR 規格核准為 **0/46**。

## 整體結論

整份 IG 目前只能宣稱：**以 FHIR R4 4.0.1 與固定 dependency 建置成功的非官方 technical community draft**。不能宣稱整份 IG 已完成 TW Core、mCODE、ICHOM、TWPAS、TCR、QBC 或院內品管的正式 conformance／驗收。

不同 scope 的證據不能互相替代。例如：QBC 115 欄技術驗證不證明 Care Plan 的 314 controls 已完成；TCR 的 48 個已驗證碼表不證明 99 欄全部完成；個管 20 個 CQL Measure 通過也不證明真實報表數字正確。

## 逐 Scope 判定

| Scope | 現有證據 | 允許宣稱 | 不允許宣稱 |
|---|---|---|---|
| IG 核心 | FHIR R4 4.0.1、SUSHI／Publisher、固定 package | 可重現建置的 FHIR R4 技術草稿 | 臨床正確、官方背書、正式導入／申報 |
| TW Core | dependency 固定 1.0.0；`BreastCancerPatient` 與 `QBCSubmissionBundle` 直接使用 TW Core parent | TW Core 是台灣結構基準；具名衍生 Profile 可依其 parent 宣稱 | 全部乳癌 Profiles 都衍生或完整符合 TW Core |
| mCODE | 4.0.0 語意比較；不是 dependency | semantic alignment reference | mCODE conformance 或 TW Core+mCODE 雙重 conformance |
| ICHOM | Breast Cancer 1.0.0 outcome gap 參考；不是 dependency | outcome coverage reference | ICHOM conformance、背書或完整 outcome implementation |
| Care Plan | 223-control catalog；25 `implemented-partial`、195 field review pending、3 algorithm review pending；受控 union 314 controls | 可執行、保留來源語意的 Task 草稿 | 完整 canonical mapping 或 production-ready workflow |
| QBC／P4P | 115/115 technical validation；合成 Big5 XML round-trip | 技術欄位契約已實作的衍生草稿 | 115 欄臨床簽核完成、官方解釋或 VPN 接受；目前 115/115 clinical review pending，14 個 approval gate 未核准 |
| TWPAS | 1.2.5 版本隔離；12 個 common mapping、15 個 Task-only requirement | official package 的 projection design | 已有可驗證的 TWPAS Apply Bundle、正式送件相容；目前沒有 adapter／官方 package output validation／NHIA acceptance |
| 個管品管／季報 | 20/20 draft Measure 合成 CQL 測試 | computable technical draft | 真實院內數字正確；目前 raw mapping、independent recalculation、golden cohort 均為 0/20 |
| TCR | 99 欄 Questionnaire；48 欄有已驗證碼表、32 欄待碼表核對、19 欄本來就是非 coded 欄位 | 部分碼表已驗證的 TCR Task 草稿 | 99 欄完整 TCR conformance 或正式申報接受 |
| 未來模組 | Task 目錄中的 pathology、tumor board、follow-up/outcome 等規劃 | future scope | 已實作或已符合任何外部規格 |

## 外部規格的判定規則

對任何外部 IG／標準，只能使用下列其中一種關係，且必須逐 Profile／artifact 留證據：

1. `direct-conformance`：固定 package/version、套用其 Profile、完整 validator 通過。
2. `partial-direct-conformance`：只有列明的 Profile／artifact 符合；不得擴張到整個 scope。
3. `projection-design`：只完成 mapping，尚未產生或驗證正式 output。
4. `semantic-reference-only`：只比較概念，完全不構成 conformance。
5. `not-implemented`：僅列入 roadmap。

canonical URL 相似、概念名稱相同或文件中引用某個標準，都不能從第 3／4 類自動升成第 1 類。

## 本次發現並修正的 TCR 計數差異

舊文案把「沒有已驗證碼表的其餘 51 欄」全部描述為 pending。實際 Questionnaire 的互斥分類為：

- 48 欄：有已驗證 `answerValueSet`。
- 32 欄：明確帶 `tcr-codetable-pending`。
- 19 欄：日期、數值或識別碼等非 coded 欄位，本來就不應要求 ValueSet。

三類合計 99，現在由自動測試鎖定；不得再以 51 個 pending 或「48/99 全部完成」描述。
