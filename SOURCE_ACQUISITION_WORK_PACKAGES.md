# 原始資料取得工作包

## 用途

這份文件把 52 個 production 必要 fact 轉成可派工的院內工作包。機器可讀明細在 [`mappings/publication/source-acquisition-work-packages.csv`](mappings/publication/source-acquisition-work-packages.csv)。工作包中的 owner 是建議角色，不是假定已找到實際負責人；目前具名 owner 確認為 **0/52**。

各館既有報表只能作為欄位線索、人工 truth set 或輸出 reconciliation。取得來源時必須回到可重現的原始系統、資料表／欄位或 API path；不得把報表欄位填回 `source_system/source_element` 後視為完成。

## 取得順序

| 批次 | 數量 | 何時處理 | 完成意義 |
|---|---:|---|---|
| B0-result-blockers | 10 | 立即 | 目前已知會使分母、分子、分層或時間規則無法正確計算。 |
| B1-cohort-rate | 31 | B0 啟動後並行 | 其餘直接決定 cohort、分母、排除或分子的 P0 facts。 |
| B2-release-provenance | 1 | 建立第一份可重現 extract 時 | 固定原始檔 hash、執行時間與轉換鏈。 |
| B3-stratifiers | 4 | rate inputs 穩定後 | 確保分布／分層數字可核對。 |
| B4-support | 6 | 最後 | 報表支援及目前未進計算的候選欄位；production 前仍須完成。 |

優先級只代表先後，不代表可省略。正式 production publication 前仍要求 52/52 完成權威來源、FHIR mapping、來源簽核與真實資料驗證。

## 八個院內工作包

| 工作包 | Facts | 建議 primary owner | 必要共同 reviewer | 第一個交付物 |
|---|---:|---|---|---|
| WP-01-PATIENT-ADMIN | 3 | 病人行政／病歷資訊系統 owner | 個管、隱私與資料治理 | MPI/ADT schema、生日／性別／死亡欄位與病人 merge 規則。 |
| WP-02-REGISTRY-STAGING | 8 | 癌登／分期系統 owner | 腫瘤臨床、病理、術語 | 收案、診斷、AJCC edition/method、前年度 cohort query 與更新規則。 |
| WP-03-PATHOLOGY | 8 | 病理／LIS owner | 病理醫師、癌登、術語 | 檢體與報告連結、final/corrected 時間、ER/PR/HER2/Ki-67／組織型碼表。 |
| WP-04-SURGERY-PROCEDURE | 5 | 手術／處置系統 owner | 乳房外科、病理、編碼 | 手術／腋下處置／粗針切片碼、performed time、取消與 laterality 規則。 |
| WP-05-SYSTEMIC-THERAPY | 3 | 腫瘤用藥／藥局系統 owner | 腫瘤內科、藥師、術語 | order/admin schema、藥碼／regimen、狀態、時間與院外治療規則。 |
| WP-06-RADIOTHERAPY | 3 | 放療資訊系統 owner | 放腫醫師、醫學物理、FHIR／術語 | course/fraction/target、實際 delivered dose、cGy 換算、執行院所與完成狀態。 |
| WP-07-CASE-MANAGEMENT | 19 | 個管／品質方案 owner | 指標臨床 owner、品質委員會、資料治理 | 表單／DB schema、完整選項碼、原值與調整值、理由、核准人與 audit timestamps。 |
| WP-08-REPORTING-PROVENANCE | 3 | 報表平台／資料工程 owner | 品質方案、各來源系統、安全治理 | 報告期間、benchmark 定義、extract/job 設定、hash、timezone、軟體版本與 Provenance。 |

## 第一批必須先解決的十項

| Fact | 內容 | 直接阻擋 |
|---|---|---|
| CM-BC-005 | pathological stage group | 病理分期與侵襲癌條件無法可靠區分。 |
| CM-BC-010 | HER2 IHC | QI-04 與 subtype 不能由原始檢驗值計算。 |
| CM-BC-011 | HER2 ISH | HER2 equivocal／amplification 規則無權威來源。 |
| CM-BC-017 | breast surgery date | 手術先後、切片先於手術及放療時間窗無法驗證。 |
| CM-BC-018 | diagnostic core needle biopsy | QI-05 組織診斷日期無法可靠建立。 |
| CM-BC-021 | cytotoxic chemotherapy | first-treatment 與 systemic therapy 判斷不完整。 |
| CM-BC-024 | radiotherapy delivered dose | QI-03 ≥4000 cGy 門檻目前完全未執行。 |
| CM-BC-025 | treatment performing organisation | QI-06 院內／院外放療無法區分。 |
| CM-BC-032 | histology type | QR-17 十組／十一組矛盾與 free-text normalization 無法驗真。 |
| CM-BC-038 | prior-year new diagnosis cohort | QR-04 完整縱向分母無法形成。 |

## 每個 fact 的實際完成流程

1. 在 work-package CSV 填入具名 owner、組織／職稱、日期、assignment evidence URI 與簽署 artifact SHA-256；只有 `confirmed` 字樣不算完成。
2. 由 owner 回答該列 `acquisition_question`，交付指定 schema／API spec、版本與 extraction query。
3. 把權威 system、artifact、element、version 填回 `source-traceability-register.csv`，再逐欄完成下列 19 維資料契約並由 source owner/reviewer 簽核。不得使用空白、`TBD`、`N/A` 或沒有具體理由的 `not-applicable`。
4. 在受控環境選取可追溯案例，證明原始欄位可以重建預期 FHIR resource/path；敏感資料不得提交到 Git。
5. 全部來源到位後，依 [逐案資料正確性驗證協定](CASE_LEVEL_VALIDATION_PROTOCOL.md)，另以不共用 CQL 邏輯的實作做 20/20 Measure exact case-by-expression 重算，再用一個完整報告期間做 exact case-by-source-fact 與完整 MeasureReport reconciliation；最終 manifest 總差異必須為 0。

`scripts/audit_source_acquisition_work_packages.py` 會拒絕漏列、重複、改動批次、改動工作包、未簽證據卻宣稱 owner confirmed，以及 priority register 更新後未同步的舊內容。

### 每個 fact 必填的 19 維資料契約

| 面向 | 必須回答的內容 |
|---|---|
| 型別與粒度 | `data_type`、`record_grain`、`source_cardinality`：一筆資料代表什麼，以及每個 case 可有幾筆。 |
| 識別與串接 | `business_key`、`join_rule`：如何穩定識別並連回 patient／case／episode／event。 |
| 值域 | `allowed_value_domain`、`precision_tolerance`、`unit_policy`：合法代碼／範圍、精度與 UCUM／換算規則。 |
| 時間 | `time_semantics`、`event_timezone`、`late_arriving_update_rule`：使用哪個事件時間、時區、cutoff 後更正如何重算。 |
| 缺值與異常 | `null_policy`、`invalid_value_policy`、`fhir_absence_representation`：來源空值、非法值及 FHIR 缺值如何區分。 |
| 多筆與擷取 | `duplicate_resolution_rule`、`extraction_filter`：重複／corrected records 如何選，以及明確納入條件。 |
| 轉換與稽核 | `transformation_rule`、`provenance_rule`：可重現轉換、來源值、時間、adapter/version/hash 如何保存。 |
| 衍生欄位 | `derivation_input_fact_ids`：derived fact 必須列出已知、非自身且不形成循環的輸入；權威來源則填 `not-applicable:` 加具體理由。 |
