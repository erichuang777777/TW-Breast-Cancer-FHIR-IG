# Changelog

## Unreleased

- Added a machine-readable TWPAS version policy that keeps published 1.2.5 as the blocking target and CI 1.2.6 as advisory only.
- Added a breast-cancer-focused TWPAS CI watchlist covering medication units, treatment dosage-system behavior, drug/programCode constraints, and indication terminology.
- Added regression tests preventing the CI package from becoming a main IG dependency or conformance claim.

本專案有兩條獨立的版本線，發布節奏不同，請勿混用：

| 版本線 | 識別 | 目前版本 | 定義於 |
|---|---|---|---|
| Workbench 應用程式 | `qbc-review-workbench` | `0.1.0-alpha.1`（PEP 440：`0.1.0a1`） | `qbc_workbench/__init__.py`、`pyproject.toml` |
| FHIR 實作指引 | `io.github.erichuang777777.breast-cancer` | `1.0.0-preview.1`（`draft`／`experimental`） | `ig/sushi-config.yaml`、`ig/publication/package-list.json` |

格式依循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，版本號依循 [語意化版本](https://semver.org/lang/zh-TW/)。

---

## [未發布]

### TWPAS 癌症用藥事前審查 Task

- 將官方 TWPAS 1.2.5 納入乳癌 common facts 的平行 Task 架構，新增 Task 定位、TW Core 版本隔離策略、common-to-TWPAS crosswalk 與 Task-only 欄位目錄。
- 明確規定本 IG 不複製或重新定義健保署官方 Profiles；只有經官方 package 獨立驗證的 Task output 才可宣告 TWPAS conformance。

### 癌症診療計畫書 Task

- 將癌症診療計畫書與 QBC 定義為平行 Task；兩者各自讀取乳癌 common FHIR facts，不互為 production input/output。
- 新增目前院內 JSON 的機器可讀 Schema，以及 223 個唯一控制項的 PHI-free catalog：25 個 `shared`、195 個 `care-plan-only`、3 個 `derived`。
- 新增 `CancerCarePlanTaskQuestionnaireResponse`、`CancerCarePlanTaskCarePlan`、`CancerCarePlanTaskProvenance`、`CancerCarePlanTaskBundle` Profiles 與完全合成 examples。
- `transform-care-plan` CLI 只產生診療計畫 FHIR Bundle；另以 `check-task-alignment` 從同一測試來源獨立產生兩個 Task view，僅供 reconciliation／regression check。
- 新增欄位 catalog 產生器、診療計畫 Task／欄位盤點頁面，以及空表單拒絕、FHIR id 長度、Provenance profile 與禁止 catalog 洩漏來源值的測試。

### 乳癌社群草稿上層與 QBC Task 分層

- 新增完整乳癌合成情境 Bundle、中英雙語合成範例頁，以及強制每個公開 FSH example 標示為合成資料的回歸測試。
- IG identity 改為 `io.github.erichuang777777.breast-cancer#1.0.0-preview.1`，canonical 改為 `https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG`。
- 新增 7 個可跨 Task 重用的 `BreastCancer*` Profiles、共同資訊分類 CodeSystem／ValueSet、CapabilityStatement 與完整合成範例。
- `QBCPatient` 改由 `BreastCancerPatient` 衍生；QBC 115 欄 Mapping、Extensions、CodeSystems 與 XML／VPN 規則明確歸入 QBC／P4P Task 層。
- 新增分層架構、Scope、共同模型、外部規格對齊、Task 目錄與 QBC Task 頁面；TW Core 為結構 dependency，mCODE／ICHOM 僅作語意參考。
- Mapping workbook 更新為 `QBC_FHIR_Mapping_TaskSpec_v1.0-preview.1.xlsx`，新增 `Architecture` 工作表並保留原有 115 欄及治理表。
- 依資料來源成熟度再分成來源證據、乳癌 canonical facts、衍生文件／協作、Task 投影四層；新增抽象 source profiles，以及具體 `BreastCancerPathologyReport`、`BreastCancerLaboratoryReport`、`BreastCancerUltrasoundReport`、`BreastCancerPathologySpecimen`。影像 lineage 直接使用標準 FHIR `ImagingStudy`。
- 明確記錄唯一目標 flow（原始病理／檢驗／超音波／治療來源 → common FHIR facts → 平行的 Care Plan／QBC／癌藥申請／癌登／MDT）；診療計畫書 JSON 僅是過渡期 secondary source。
- Mapping workbook 新增 `Data_Flow`，逐欄增加 current secondary source、target source evidence、canonical fact 及 projection role，禁止把衍生文件或其他 Task artifact 當成原始 source of truth。

### 人工審查範圍修正

先前 `clinical_review_template.csv` 逐欄列出 115 個官方規則、全部標為
`pending`，等於要求人「核准」健保署公布的法定規格。這個框架是錯的：官方規則
依定義即為準據，需要人判斷的只有 Word 文字未明示、由本專案補上的解讀。

- 簽核表由 **115 列縮為 9 列**，只列本地解讀，欄位改為
  `item_id`／`category`／`affected_fields`／`word_basis`／`local_interpretation`／
  `decision`／`reviewer_role`／`reviewer_name`／`decision_date`／`notes`
- 受影響欄位由實作的 `rule_ids` 反查，不手寫；區段規則若無欄位引用，產生腳本直接失敗
- `rule_coverage.csv` 的 `clinical_review_status` 由全部 `pending` 改為
  `verified-by-test`（481）／`needs-decision`（39）／`decided-by-project`（1）
- 查證後確認 `QBC-TM02-SURGERY-POSTOP-REQUIRED` 的觸發條件並非 Word 明文
  （D027／D030／D032 原文只列值域），係本專案推導，影響 19 欄，已列入待簽核
- 新增 `test_review_template_only_lists_local_interpretations_not_official_rules`
  與 `test_word_derived_rules_are_verified_by_test_not_pending_human_review`

### 官方 XML 範例回歸測試

依 XML 規格 `TRACES` 區段的官方範例新增回歸測試，原封不動通過驗證。官方註記
「追蹤（每年至多填寫一次，最多 5 年）」與「追蹤年度（根據收案日滿一年後始可填寫）」
證實追蹤頻率**本非歧義**，該項依據由「專案決議」升級為「官方明文」。範例第二筆
`T03=4` 填 `T06` 而 `T05` 留空，亦印證主表 T06 的「※死亡視同結案」。

### 已知歧義決議（專案決議 2026-08-13）

8 項已知歧義中的 7 項由專案臨床與實作人員決議。決議來源記為「專案決議」，
**不等同健保署正式函釋**；取得書面回覆後應升級為「官方確認」並註記文號。

| 項目 | 決議 | 實作變更 |
|---|---|---|
| `TM10` 日期順序 | 確認為筆誤，以 `TM09` 為準 | 行為已相符，僅升級文件狀態 |
| 持續中的藥物療程 | 送件一律從嚴，仍要求 `TM10` | 行為已相符，僅升級文件狀態 |
| 追蹤頻率 | 「一年一次」與「至少一次」語意相同，無衝突 | 行為已相符，僅升級文件狀態 |
| de novo Stage IV | 初診斷即轉移視同復發，定義相同，不另做特殊標記 | 移除 de novo 特殊標記的保留條款 |
| 雙側共用療程 | 各自建檔、各自上傳，每筆含各自完整療程；須提醒使用者 | 新增 `QBC-FAQ-BILATERAL-TWO-RECORDS` warning 與 `bilateral_counterpart_case_id` |
| 惡性葉狀瘤／肉瘤 | 一般乳癌 TNM 不適用，臨床手填分期優先 | 新增 `QBC-TNM-SARCOMA-EXCEPTION`（TNM 不一致降為 warning）與 `non_epithelial_tumor` |
| 同側多型態「較嚴重」 | 期別 Ⅲ > Ⅱ > Ⅰ，次分期 ⅢC > ⅢB > ⅢA，完全同期別才以腫瘤大小排序 | 新增 `QBC-SEVERITY-ORDER`：`stage_rank()`、`severity_rank()`、`more_severe()` |

「同側多型態」自此由人工逐案判定升級為可自動判定。完整排序為
`Stage 0` < `ⅠA` < `ⅠB` < `ⅡA` < `ⅡB` < `ⅢA` < `ⅢB` < `ⅢC` < `Ⅳ`。
其中 `Ⅳ > ⅢC` 與 `ⅠA > 0` 依同一邏輯延伸、`StageX` 一律回退人工判定，
這三者列為待確認，未當作已決議。

肉瘤例外的觸發範圍維持原設計：除 `non_epithelial_tumor` 明示旗標外，組織學分類
為 `8`（其他）亦自動觸發，因 `D003`／`D030` 無葉狀瘤專屬代碼。

第 8 項「獎勵核付」不是歧義而是刻意不做，已移至「不由本 IG 認定」。

### 新增

- **發布身分**：IG canonical 由佔位的 `https://example.org/fhir/qbc` 改為
  `https://ericeric777777.github.io/qbc-ig`，package ID 由 `tw.example.qbc` 改為
  `io.github.ericeric777777.qbc`。採 reverse-DNS 對應，刻意不使用 `tw.`／`tw.gov.`
  開頭以免佔用主管機關命名空間。ImplementationGuide 補上 `experimental`、`contact`
  與 `copyright`。
- **版本控制**：專案首次納入 git 管理。
- **版本目錄**：`ig/publication/package-list.json` 由範本轉為實際版本目錄，
  取代 `package-list.template.json`。
- **個資閘門**：新增 `scripts/check_no_phi.py`，以 git 可提交檔案為範圍掃描
  病歷號、身分證號與個案檔名；合成識別碼須在 `SYNTHETIC_ALLOWLIST` 明確宣告。
  已接入 `scripts/check_release.ps1` 與 `scripts/build_release.py`。
- **打包腳本**：新增 `scripts/build_release.py`，發布包檔案清單由 git 追蹤檔推導，
  取代先前手動複製、已與原始碼脫節的快照。
- **FHIR Profile**：新增 `QBCQuantityDataItemObservation`，涵蓋身高、體重與腫瘤大小；
  `QBCTumorSizeObservation` 改為其衍生。新增 `QBCQuantityFieldValueSet`。
- **範例**：新增身高（`P03`）、追蹤年度（`T01`）、原始值（`D003`）三個合成範例。

### 變更

- **病歷資料完整隔離**：真實個案、名單與官方規格原檔移入 `private/`
  （`cases/`、`rosters/`、`spec-sources/`），由 `.gitignore` 整批排除。
  `.gitignore` 先前只排除不存在的 `patients/`／`incoming/`，實際個案檔完全未受保護。
- **強型別覆蓋補齊**：`QBCDateFieldValueSet` 由 3 欄補至 10 欄
  （新增 `P09`、`TM09`、`TM10`、`T01`、`T04`、`T05`、`T06`；`BIRTHDAY` 以
  `QBCPatient.birthDate` 表示，刻意不納入）。`QBCIntegerFieldValueSet` 補入
  `P06`、`TM01`，共 21 欄。
- **Patient 範例**：改用 TW Core Patient 的 `idCardNumber` slice
  （`v2-0203#NNxxx` + 內政部 system），先前的 identifier 不符合任何 slice。
- **來源追溯頁**：不再列出任何個案檔名、病歷號或名單檔名，改以目錄層級描述；
  新增各來源的 SHA-256 供讀者核對自行取得的官方原檔。
- **著作權界線**：`field-audit.md` 新增「出處與著作權」區塊，載明逐字引用之
  權利歸屬與異議管道；官方文件全文擷取與逐行 CSV 不再進入版本控制或發布物。
- **免責聲明**：`downloads`、`mappings`、`security`、`usecases`、`field-audit`
  五頁補上先前缺漏的 `disclaimer.md`。

### 修正

- `qbc_workbench/fhir.py` 的 `QBC_CANONICAL` 預設值同步更新（先前寫死 example.org）。
- 發布包先前缺少 `spec.py`、`validation.py`、`xml_validation.py`、
  `data/qbc_fields.json`、`test_conformance.py`、`test_fhir.py`，導致 README
  記載的 `validate-xml`／`mock-receive` 指令在包內無法執行。

---

## [0.1.0-alpha.1] — 2026-08-12

首個可執行的開發預覽版：批次匯入、FHIR canonical Bundle、QBC 規則、Ollama 結構化擷取、
人工審核 Web UI、核准閘門、Big5 XML 與稽核輸出。後續 conformance 更新加入 115 欄
機器可讀規格、結構化錯誤碼、Big5 XML round-trip、模擬收件端、三種 `DIAG_TYPE` 合成
測試包、FHIR 強型別 Observation Profiles 及 mCODE 4.0.0 gap matrix。
# Mapping v0.2.0-review

- 新增 `Formal_Mapping_115`：115 個唯一 mapping rule，固定 Target Resource/Element、profile 版本、型別、基數、轉換及資訊損失政策。
- 新增 `Approval_Register`，將 QBC 規則、臨床、FHIR、術語／授權、個資資安、VPN UAT 與 publisher 核准分開治理。
- 新增 9 個 QBC Extensions、2 個 ConceptMaps、13 個 ValueSets／2 個 CodeSystems；IG Publisher QA 為 0 errors、0 warnings、0 broken links。
