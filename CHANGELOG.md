# Changelog

本專案有兩條獨立的版本線，發布節奏不同，請勿混用：

| 版本線 | 識別 | 目前版本 | 定義於 |
|---|---|---|---|
| Workbench 應用程式 | `qbc-review-workbench` | `0.1.0-alpha.1`（PEP 440：`0.1.0a1`） | `qbc_workbench/__init__.py`、`pyproject.toml` |
| FHIR 實作指引 | `io.github.ericeric777777.qbc` | `0.1.0`（`draft`／`experimental`） | `ig/sushi-config.yaml`、`ig/publication/package-list.json` |

格式依循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.1.0/)，版本號依循 [語意化版本](https://semver.org/lang/zh-TW/)。

---

## [未發布]

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
