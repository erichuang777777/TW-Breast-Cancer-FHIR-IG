# Quality 匯入包整合稽核

本文件記錄本機 `FHIR_mapping_required from quality/` 匯入包與 tracked IG 的逐檔比較。匯入包是使用者保留的來源副本，不納入版本庫；下列 SHA-256 用來固定本次比對的來源批次。比較基準為 commit `05aeb98`，日期 2026-08-21。

## 結論

13 個來源檔案均已處理：11 個有直接 tracked 對應，另外 `HANDOFF.md` 是交接說明、`ig-navigation.patch` 是套用指令，兩者不應原樣複製成 IG artifact。未發現遺漏的 mapping ID、Measure、criterion、Task-only field、FSH artifact 或原有測試。

tracked 版本不是盲目覆蓋來源副本；後續已加入真實 Publisher／CQL execution 修正、規格矛盾標記、Python reference implementation 邊界、更多測試與更精確的發布限制。因此雜湊不同本身不代表漏整合，必須依下列結構／symbol 比較判定。

## 來源批次 SHA-256 與處理結果

| 來源相對路徑 | 來源 SHA-256 | 處理結果 |
|---|---|---|
| `HANDOFF.md` | `bb3d8a53d49a3a7c8564af8295f6c1a68476e590d2d58a65aade24b2d927d5a0` | instructions-consumed；不作為發布 artifact。 |
| `ig-navigation.patch` | `ff81ee8dc5e6f789b2fcf7e34faeccf641ca0d8ba91e4fbf830675488cbadc06` | applied；page、Task index row、menu 三項均存在。 |
| `mappings/case-management/case-management-measure-catalog.csv` | `b0c49f70bb5c30c38ca79aded19f468b8e3b4071e8f7f2cd8700aa71406380ff` | identical。 |
| `mappings/case-management/case-management-task-only-fields.csv` | `417a2eb132af4571a523a268c9e0ebc4a5cb6e2e0d1265abc17b3c7e0f67268f` | superseded-reviewed；18/18 IDs 保留，CM-TASK-020 修正為品管與季報共用的 governed reporting period。 |
| `ig/input/fsh/case-management-terminology.fsh` | `cc353d602a60ac955503c4f35446fe4da9a07d78796bbeb7fc9e0ff76ff49584` | identical。 |
| `mappings/case-management/breast-common-to-case-management.csv` | `33f799965ed7244bc833efa6a7330306455a911d950e6a70d39729f738811e80` | superseded-reviewed；34/34 IDs 保留，CM-BC-007/009/010/011/032 補上 QR-17/18 實際間接依賴，CM-BC-032 仍是 11/10 群矛盾的 blocking gap。 |
| `mappings/case-management/case-management-population-criteria.csv` | `56029884632b89628d41d17deb1c82f0a7ba2ede1f8563304efc9ebbf27d2848` | superseded-reviewed；68/68 criterion IDs 保留，新增 `python_divergence`、校正實作狀態，並將 CQL 間接呼叫、報告參數與人工 adjudication 依賴補齊為 45/52 facts。 |
| `mappings/case-management/README.md` | `3e395f363f93e316024769ef1f8988d9e39695ad7b94760e9d5d4cde9c12f564` | superseded-reviewed；原 84 行全部保留，增加 33 行 Python manifest 與 quarterly 未驗證邊界。 |
| `ig/input/cql/BreastCancerCaseManagement.cql` | `f7ff817b2b3a96035f712979ae133c46f093ab74bf3b4d013e2d612373e50f5c` | superseded-reviewed；見 CQL symbol 與 runtime 核對。 |
| `ig/input/fsh/case-management-measures.fsh` | `a07e3e694f05f1939b0dba5a23e1311b471790e098a528a90b594d0451019936` | superseded-reviewed；22/22 FSH symbols 保留，補 QI-03 上界警語與 QR-12 正規化 expression。 |
| `ig/input/pagecontent/task-case-management.md` | `cdf6e2c646cb3f12f74924902488feb46aca740a20d55da00365581bb84abda5` | superseded-reviewed；更新已過時的 CQL 未執行宣稱，加入資料來源盤點、已知分歧及 QR-17 阻擋。 |
| `tests/test_case_management_mapping.py` | `43e21c2a80cdfacebc49a4a1f9041d5468a346537270e432728f8fb36170fb0c` | superseded-reviewed；21/21 原 test functions 保留，tracked 現有 24，新增狀態 vocabulary、差異證據、indicator-family coverage 與間接依賴鎖定測試。 |
| `tests/test_case_management_measures.py` | `72be744f9544c96b694dc87660b9e83252e490f8f2efd8521531b2bfa3af3885` | superseded-reviewed；18/18 原 test functions 保留，新增 7 個 Publisher、FHIRHelpers、total boolean、Task query 與 Python manifest 測試。 |

## 結構與 symbol 完整性

| 類型 | 匯入包 | tracked | 判定 |
|---|---:|---:|---|
| common mapping IDs | 34 | 34 | exact same ID set。 |
| Measure catalog IDs | 20 | 20 | exact same ID set。 |
| population／stratifier criterion IDs | 68 | 68 | exact same ID set；tracked 增加一個審計欄位。 |
| Task-only field IDs | 18 | 18 | exact same ID set。 |
| Measure FSH symbols | 22 | 22 | exact same symbol set。 |
| mapping test functions | 21 | 24 | 匯入 21 項全部保留，新增 3 項。 |
| Measure test functions | 18 | 25 | 匯入 18 項全部保留，新增 7 項。 |
| CQL define/function symbols | 100 | 107 | 99 項同名保留；1 項等價重構；新增 8 項（新增的 pathology-report date path 使 CM-BC-019 與 N5-BIOPSY-BEFORE 實際對齊）。 |

CQL 唯一不再同名存在的是 `Case Management Task Inputs`。匯入版先建立一個 untyped flatten define，再由 `Case Input Code` 取值；tracked 版把 `[Task]` 查詢 inline 到 `Case Input Code`，並新增 `ValueSystem`、`AllowedCodes` 與 code system/code 驗證。`tests/test_case_management_measures.py` 明確要求舊 define 不存在且直接 Task query 存在；全部 20 Measure 已完成遠端 ELM translation、runtime smoke 與 asserted branch execution。因此這是經驗證的替代，不是漏件。

## 導覽 patch 核對

- `ig/input/pagecontent/task-case-management.md` 已存在。
- `ig/input/pagecontent/task-index.md` 已有 `task-case-management.html` 的 Task row。
- `ig/sushi-config.yaml` 的 `pages` 與 `menu` 均有個管指標項目。

## 證據邊界

這份稽核只證明「quality 匯入包的設計 artifact 已完整吸收或有具體替代」，不證明來源報表數值、原始資料 mapping、臨床 terminology 或 Measure 定義已正確。那些發布條件仍由 `PUBLICATION_ACCEPTANCE_MATRIX.md`、`source-traceability-register.csv`、`measure-validation-evidence-register.csv` 與八項 release controls 判定。
