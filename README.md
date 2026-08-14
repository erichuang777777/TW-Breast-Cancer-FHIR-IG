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
Task：QBC／P4P 癌症治療申報（目前第一個 Task）
```

目前因無法取得完整原始臨床資料，QBC Task 先以整理過的癌症診療計畫書作為 bridge input。未來可改由病理、檢驗、影像與其他原子資料產生診療計畫，或直接投影為申報資料；診療計畫與申報資料都不應被視為原始臨床事實的唯一來源。

### 範圍

目前包含：

- 乳癌共用 Profiles、Terminology、Extensions、Examples 與 CapabilityStatement。
- QBC／P4P 115 年欄位至 FHIR 的正式化 Mapping、條件、基數、轉換、缺值、重複值、可逆性與審查狀態。
- 與 TW Core 1.0.0、mCODE 4.0.0 及 ICHOM Breast Cancer 1.0.0 的對齊與差異說明。
- 來源可追溯、Provenance、FHIR Bundle、Big5 XML round-trip、驗證規則與人工審查登錄。
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
| `qbc_workbench/` | 匯入、驗證、FHIR 轉換、XML round-trip 與稽核工具 |
| `scripts/` | Mapping、IG、發布與 PHI 檢查腳本 |
| `tests/` | 自動化測試 |
| `private/` | 不納入 Git 的受保護來源與個案資料 |

核心 Mapping Table：

- `outputs/qbc_ig_mapping/QBC_FHIR_Mapping_TaskSpec_v1.0-preview.1.xlsx`
- `outputs/qbc_ig_mapping/qbc_fhir_formal_mapping.csv`
- `outputs/qbc_ig_mapping/qbc_mapping_approval_register.csv`

### 建置與驗證

需求：Python 3、Node.js／npm、SUSHI、Java，以及 HL7 FHIR IG Publisher。

```powershell
# 完整發布檢查：重建產物、PHI 掃描、測試、SUSHI 與 Publisher QA
.\scripts\check_release.ps1

# 單獨重建 Mapping Table
python scripts\build_qbc_ig_mapping.py

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

### 治理與簽核

Preview 版本可以由專案維護者發布，不代表官方認證。需要人工確認的項目記錄於 Mapping workbook 的 `Approval_Register` 及對應 CSV；簽核的是本專案對規則、術語與臨床語意所做的本地解讀，不是要求維護者代替主管機關核准官方規則。

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
Task: QBC/P4P cancer care reporting (the first task currently implemented)
```

Because complete source clinical data is not currently available, the QBC task uses a curated cancer care plan as a bridge input. A future implementation may derive the care plan from atomic pathology, laboratory, imaging, and history data, or project those facts directly into reporting data. Neither the care plan nor the claim/report payload should replace the original clinical facts as the source of truth.

### Scope

Included now:

- Shared breast cancer Profiles, terminology, Extensions, examples, and a CapabilityStatement.
- A formal QBC/P4P 2026 field-to-FHIR mapping, including conditions, cardinalities, transformations, missing-value behavior, repetitions, reversibility, and review status.
- Alignment and gap documentation for TW Core 1.0.0, mCODE 4.0.0, and ICHOM Breast Cancer 1.0.0.
- Source traceability, Provenance, FHIR Bundles, Big5 XML round-trip behavior, validation rules, and a human-review register.
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
| `qbc_workbench/` | Import, validation, FHIR transformation, XML round-trip, and audit tooling |
| `scripts/` | Mapping, IG, release, and PHI-check scripts |
| `tests/` | Automated tests |
| `private/` | Protected source and case data excluded from Git |

Primary mapping artifacts:

- `outputs/qbc_ig_mapping/QBC_FHIR_Mapping_TaskSpec_v1.0-preview.1.xlsx`
- `outputs/qbc_ig_mapping/qbc_fhir_formal_mapping.csv`
- `outputs/qbc_ig_mapping/qbc_mapping_approval_register.csv`

### Build and validation

Prerequisites: Python 3, Node.js/npm, SUSHI, Java, and the HL7 FHIR IG Publisher.

```powershell
# Full release gate: rebuild artifacts, PHI scan, tests, SUSHI, and Publisher QA
.\scripts\check_release.ps1

# Rebuild the mapping artifacts only
python scripts\build_qbc_ig_mapping.py

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
