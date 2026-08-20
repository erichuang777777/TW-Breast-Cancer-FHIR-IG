# Taiwan Breast Cancer FHIR Implementation Guide

> 台灣乳癌 FHIR 實作指引社群草稿（Preview 1.0）
> Taiwan Breast Cancer FHIR Implementation Guide — Community Draft (Preview 1.0)

[中文](#中文說明) | [English](#english)

目前版本：`1.0.0-preview.1` · FHIR R4 · `draft` · `experimental`

## 中文說明

### 專案定位

本專案建立一套以台灣醫療情境為背景的乳癌 FHIR 實作指引草稿。乳癌是上層臨床範疇（domain scope）；QBC／P4P 癌症治療品質改善計畫資料申報是目前第一個被納入驗證的業務 Task，不等同於整套乳癌 IG。

本草稿希望讓後續 Task 共用乳癌核心模型，避免每個申報或作業流程各自建立不相容的 Patient、Condition、Observation、DiagnosticReport、Procedure、MedicationRequest 等定義。

```text
原子臨床資料
病理／檢驗／超音波／病史／家族史
        ↓
乳癌共用 FHIR Profiles、ValueSets、Extensions
        ↓
診療計畫／治療計畫／多專科討論／癌症登記／藥物申請
        ↓
├─ Task：癌症診療計畫書（獨立 Task 草稿）
├─ Task：QBC／P4P 癌症治療申報（第一個已驗證 Task）
└─ Task：TWPAS 癌症用藥事前審查（官方 TWPAS 1.2.5 投影設計）
```

目標資料流是先把病理、檢驗、影像、病史及治療等原始資料轉成乳癌共用 FHIR facts，再由癌症診療計畫書、QBC／P4P、TWPAS、癌症登記等平行 Task 各自取用。Task 之間沒有上下游依賴；互相產生的功能只可用於 migration、reconciliation 與一致性檢查。TWPAS Task 另加入當次申請的品項、數量、用藥線別與給付適應症等 Task-only 資料，再輸出符合健保署官方規格的 Bundle。

目前因無法取得完整原始臨床資料，整理過的癌症診療計畫書 JSON 暫時作為 secondary source，供兩個獨立 adapter 驗證 Mapping。這不代表 Cancer Care Plan Task 的輸出是 QBC Task 的輸入。

### 範圍

目前包含：

- 乳癌共用 Profiles、Terminology、Extensions、Examples 與 CapabilityStatement。
- QBC／P4P 115 年欄位至 FHIR 的正式化 Mapping、條件、基數、轉換、缺值、重複值、可逆性與審查狀態。
- 與 TW Core 1.0.0、mCODE 4.0.0 及 ICHOM Breast Cancer 1.0.0 的對齊與差異說明。
- 來源可追溯、Provenance、FHIR Bundle、Big5 XML round-trip、驗證規則與人工審查登錄。
- 可由 IG Publisher 驗證的完全合成端到端乳癌情境與 QBC Task Bundle。
- 癌症診療計畫書 capture v1 與未來 web template v2 JSON 契約、223-control Preview catalog／314-control 月批次 union 稽核、CarePlan／QuestionnaireResponse／Provenance／Task Bundle，以及平行 Task alignment check。
- TWPAS 1.2.5 平行 Task 的版本隔離策略、common facts crosswalk 與事前審查 Task-only 欄位目錄；不複製或取代健保署官方 Profiles。
- 後續擴充病理報告、檢驗報告、超音波報告、癌症登記、癌藥申請、治療計畫及多專科討論等 Task 的架構。

目前不包含：

- 衛生主管機關、健保署、HL7 Taiwan 或任何標準組織的正式核准或背書。
- 醫療決策建議、支付資格判定，或可直接投入正式申報的保證。
- 未經驗證的原始病歷資料與個人健康資訊。

### IG 識別

| 項目 | 值 |
|---|---|
| Repository | `erichuang777777/TW-Breast-Cancer-FHIR-IG` |
| Package ID | `io.github.erichuang777777.breast-cancer` |
| Canonical | `https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG` |
| Version | `1.0.0-preview.1` |
| FHIR | `4.0.1` |
| Status | `draft` / `experimental` |
| License | CC BY 4.0 |

### 重要目錄

| 路徑 | 內容 |
|---|---|
| `ig/` | FSH、IG 頁面、設定及 Publisher 產物 |
| `outputs/qbc_ig_mapping/` | QBC Mapping Table、正式化 CSV、簽核／審查登錄 |
| `qbc_workbench/data/cancer_care_plan*` | 診療計畫 JSON Schema 與不含個案值的欄位 catalog |
| `qbc_workbench/` | 匯入、驗證、FHIR 轉換、XML round-trip 與稽核工具 |
| `scripts/` | Mapping、IG、發布與 PHI 檢查腳本 |
| `tests/` | 自動化測試 |
| `private/` | 不納入 Git 的受保護來源與個案資料 |

核心 Mapping Table：

- `outputs/qbc_ig_mapping/QBC_FHIR_Mapping_TaskSpec_v1.0-preview.1.xlsx`
- `outputs/qbc_ig_mapping/qbc_fhir_formal_mapping.csv`
- `outputs/qbc_ig_mapping/qbc_mapping_approval_register.csv`

公開範例位於 `ig/input/fsh/breast-common-examples.fsh`、`ig/input/fsh/examples.fsh` 與 `ig/input/pagecontent/examples.md`。所有範例均為完全合成資料，不得以真實病歷或僅去識別化的病歷取代。

### 建置與驗證

需求：Python 3、Node.js／npm、SUSHI、Java，以及 HL7 FHIR IG Publisher。

```powershell
# 完整發布檢查：重建產物、PHI 掃描、測試、SUSHI 與 Publisher QA
.\scripts\check_release.ps1

# 單獨重建 Mapping Table
python scripts\build_qbc_ig_mapping.py

# 從受控來源重建不含 PHI 的診療計畫欄位 catalog
python scripts\build_care_plan_catalog.py .\private\cases\<case>.case.json

# 只產生 Cancer Care Plan Task Bundle
python -m qbc_workbench.cli transform-care-plan .\private\cases\<case>.case.json `
  --case <local-case-id> --output .\runtime\care-plan-output

# 由同一測試來源獨立產生兩個 Task view，僅供一致性檢查
python -m qbc_workbench.cli check-task-alignment .\private\cases\<case>.case.json `
  --case <local-case-id> --output .\runtime\task-alignment

# 產生不含個案識別與值的月批次稽核及 Care Plan JSON → QBC 缺口矩陣
python scripts\analyze_care_plan_batch.py .\private\monthly .\runtime\care-plan-output `
  .\runtime\care-plan-batch-audit.json
python scripts\analyze_care_plan_companions.py .\private\monthly `
  .\runtime\care-plan-companion-audit.json .\runtime\care-plan-companion-audit.xlsx
python scripts\analyze_care_plan_qbc_coverage.py .\private\monthly `
  .\runtime\care-plan-qbc-coverage.json

# 單獨執行測試與 PHI 掃描
python -m pytest -q
python scripts\check_no_phi.py
```

手動建置 IG：

```powershell
Set-Location ig
npm.cmd install --prefix tools
sushi.cmd .
java "-Dfile.encoding=UTF-8" -jar publisher.jar -ig ig.ini
```

發布前至少應確認：測試通過、SUSHI 無 error、Publisher QA 為 0 errors／0 warnings／0 broken links、Mapping 產物已重建，且 PHI 掃描無發現。

各發布層級、六種核對方法、逐項資料正確性門檻及目前 238 個 Publisher warnings 的精確分類，見 [FHIR IG 發布與資料正確性驗收矩陣](PUBLICATION_ACCEPTANCE_MATRIX.md)。

### 治理與簽核

只有 [發布驗收矩陣](PUBLICATION_ACCEPTANCE_MATRIX.md) 的 Community Preview gate 通過後，專案維護者才可發布版本化 Preview；目前只能分享明確標示限制的原始碼／研究草稿。Preview 也不代表官方認證。需要人工確認的項目記錄於 Mapping workbook 的 `Approval_Register` 及對應 CSV；簽核的是本專案對規則、術語與臨床語意所做的本地解讀，不是要求維護者代替主管機關核准官方規則。

正式導入前，採用機構仍應完成臨床、術語、FHIR、資訊安全、法遵與申報流程的在地審查。問題與建議請使用 [GitHub Issues](https://github.com/erichuang777777/TW-Breast-Cancer-FHIR-IG/issues)。

### 授權與聲明

本專案內容以 CC BY 4.0 授權；第三方標準、代碼系統與文件仍受各自授權條款約束。FHIR® 是 HL7® 的註冊商標。本專案為獨立社群草稿，未經 HL7 International、HL7 Taiwan、衛生福利部、中央健康保險署、ICHOM 或其他機構背書。

---

## English

### Project purpose

This repository develops a Taiwan-context community draft for a breast cancer FHIR Implementation Guide. Breast cancer is the domain scope. The QBC/P4P cancer care quality reporting workflow is the first validated business task; it is not the entire breast cancer IG.

The guide provides a reusable breast cancer model so future workflows can share compatible definitions for Patient, Condition, Observation, DiagnosticReport, Procedure, MedicationRequest, and related resources instead of creating a separate IG for every task.

```text
Atomic clinical data
pathology / laboratory / ultrasound / history / family history
        ↓
Shared breast cancer FHIR Profiles, ValueSets, and Extensions
        ↓
care plans / treatment plans / tumor board / cancer registry / drug review
        ↓
├─ Task: cancer care plan (independent task draft)
├─ Task: QBC/P4P reporting (the first validated task)
└─ Task: TWPAS cancer drug prior authorization (official TWPAS 1.2.5 projection design)
```

The target flow converts atomic pathology, laboratory, imaging, history, and treatment sources into reusable breast-cancer FHIR facts first. The cancer-care-plan, QBC/P4P, TWPAS, registry, and future modules are parallel tasks that independently consume those facts. Task-to-task conversion is permitted only for migration, reconciliation, and consistency checks. The TWPAS task adds application-only data such as the requested item, quantity, line of therapy, and coverage indication before producing an official TWPAS-conformant Bundle.

Because complete atomic sources are not yet available, the curated care-plan JSON is temporarily treated as a secondary source for two independent adapters. This does not make the Cancer Care Plan Task output an input to the QBC Task.

### Scope

Included now:

- Shared breast cancer Profiles, terminology, Extensions, examples, and a CapabilityStatement.
- A formal QBC/P4P 2026 field-to-FHIR mapping, including conditions, cardinalities, transformations, missing-value behavior, repetitions, reversibility, and review status.
- Alignment and gap documentation for TW Core 1.0.0, mCODE 4.0.0, and ICHOM Breast Cancer 1.0.0.
- Source traceability, Provenance, FHIR Bundles, Big5 XML round-trip behavior, validation rules, and a human-review register.
- Publisher-validated, fully synthetic end-to-end breast cancer and QBC task scenarios.
- Cancer-care-plan capture-v1 and future web-template-v2 JSON contracts, a 223-control Preview catalog and 314-control monthly-union audit, CarePlan/QuestionnaireResponse/Provenance/Task Bundle, and a parallel-task alignment check.
- A TWPAS 1.2.5 parallel-task design with version isolation, a common-facts crosswalk, and a prior-authorization task-only field inventory; the official NHIA profiles are neither copied nor replaced.
- A machine-readable TWPAS compatibility policy: published 1.2.5 remains the blocking conformance target, while the changing 1.2.6 CI build is used only for advisory early warnings and synthetic regression planning.
- An extensible architecture for pathology, laboratory, ultrasound, cancer registry, anticancer drug review, treatment planning, and multidisciplinary discussion tasks.

Not included:

- Official approval or endorsement by Taiwan health authorities, NHIA, HL7 Taiwan, or any standards organization.
- Clinical decision support, reimbursement eligibility decisions, or a guarantee that artifacts are production-ready for official submission.
- Unvalidated source medical records or personal health information.

### IG identity

| Item | Value |
|---|---|
| Repository | `erichuang777777/TW-Breast-Cancer-FHIR-IG` |
| Package ID | `io.github.erichuang777777.breast-cancer` |
| Canonical | `https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG` |
| Version | `1.0.0-preview.1` |
| FHIR | `4.0.1` |
| Status | `draft` / `experimental` |
| License | CC BY 4.0 |

### Repository layout

| Path | Purpose |
|---|---|
| `ig/` | FSH, narrative pages, configuration, and Publisher output |
| `outputs/qbc_ig_mapping/` | QBC Mapping Table, formal CSV, and approval/review register |
| `qbc_workbench/data/cancer_care_plan*` | Care-plan JSON Schema and field catalog with no case values |
| `qbc_workbench/` | Import, validation, FHIR transformation, XML round-trip, and audit tooling |
| `scripts/` | Mapping, IG, release, and PHI-check scripts |
| `tests/` | Automated tests |
| `private/` | Protected source and case data excluded from Git |

Primary mapping artifacts:

- `outputs/qbc_ig_mapping/QBC_FHIR_Mapping_TaskSpec_v1.0-preview.1.xlsx`
- `outputs/qbc_ig_mapping/qbc_fhir_formal_mapping.csv`
- `outputs/qbc_ig_mapping/qbc_mapping_approval_register.csv`

Public examples are maintained in `ig/input/fsh/breast-common-examples.fsh`, `ig/input/fsh/examples.fsh`, and `ig/input/pagecontent/examples.md`. Every example is completely synthetic; real or merely de-identified medical records must never be substituted.

### Build and validation

Prerequisites: Python 3, Node.js/npm, SUSHI, Java, and the HL7 FHIR IG Publisher.

```powershell
# Full release gate: rebuild artifacts, PHI scan, tests, SUSHI, and Publisher QA
.\scripts\check_release.ps1

# Rebuild the mapping artifacts only
python scripts\build_qbc_ig_mapping.py

# Rebuild the PHI-free care-plan field catalog from a controlled source
python scripts\build_care_plan_catalog.py .\private\cases\<case>.case.json

# Produce only the Cancer Care Plan Task Bundle
python -m qbc_workbench.cli transform-care-plan .\private\cases\<case>.case.json `
  --case <local-case-id> --output .\runtime\care-plan-output

# Independently build both task views from one test source for alignment checking only
python -m qbc_workbench.cli check-task-alignment .\private\cases\<case>.case.json `
  --case <local-case-id> --output .\runtime\task-alignment

# Produce aggregate-only monthly audits and the Care Plan JSON to QBC gap matrix
python scripts\analyze_care_plan_batch.py .\private\monthly .\runtime\care-plan-output `
  .\runtime\care-plan-batch-audit.json
python scripts\analyze_care_plan_companions.py .\private\monthly `
  .\runtime\care-plan-companion-audit.json .\runtime\care-plan-companion-audit.xlsx
python scripts\analyze_care_plan_qbc_coverage.py .\private\monthly `
  .\runtime\care-plan-qbc-coverage.json

# Run tests and the PHI scan separately
python -m pytest -q
python scripts\check_no_phi.py
```

Manual IG build:

```powershell
Set-Location ig
npm.cmd install --prefix tools
sushi.cmd .
java "-Dfile.encoding=UTF-8" -jar publisher.jar -ig ig.ini
```

Before publication, confirm that tests pass, SUSHI reports no errors, Publisher QA reports 0 errors, 0 warnings, and 0 broken links, mapping artifacts are rebuilt, and the PHI scan finds nothing.

### Governance and review

A project maintainer may publish this Preview release; publication does not constitute official certification. Human-review items are recorded in the workbook `Approval_Register` and its CSV counterpart. Reviewers sign the project’s local interpretation of clinical, terminology, and workflow rules—not the underlying official rules themselves.

Before production adoption, each implementing organization remains responsible for local clinical, terminology, FHIR, privacy, security, legal, and submission-workflow review. Use [GitHub Issues](https://github.com/erichuang777777/TW-Breast-Cancer-FHIR-IG/issues) for feedback.

### License and disclaimer

Project-authored content is licensed under CC BY 4.0. Third-party standards, code systems, and documents remain subject to their own terms. FHIR® is a registered trademark of HL7®. This independent community draft is not endorsed by HL7 International, HL7 Taiwan, Taiwan’s Ministry of Health and Welfare, the National Health Insurance Administration, ICHOM, or any other organization.
