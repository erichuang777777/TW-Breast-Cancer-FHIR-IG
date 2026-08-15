# TWPAS 癌症用藥事前審查 Task

{% include disclaimer.md %}

## Task 定位

臺灣健保癌症用藥事前審查實作指引（TWPAS）由中央健康保險署正式維護。本社群草稿不建立替代 TWPAS，也不複製、修改或重新發布其 Profiles、ValueSets、Extensions 與 Constraints。本 Task 只定義乳癌 common FHIR facts 如何投影至指定版本的官方 TWPAS 申請 Bundle。

- 目標官方 package：`tw.gov.mohw.nhi.pas#1.2.5`
- 官方 canonical：`https://nhicore.nhi.gov.tw/pas`
- FHIR：R4 `4.0.1`
- 本模組狀態：mapping／adapter design draft；尚未宣告可正式送件

官方規格：[TWPAS 應用說明](https://nhicore.nhi.gov.tw/pas/)、[癌藥事前審查 Bundle 架構](https://nhicore.nhi.gov.tw/pas/vision-cancer.html)、[申請資料模型 Mapping](https://nhicore.nhi.gov.tw/pas/StructureDefinition-ApplyModel-mappings.html)。

## 平行 Task 關係

```text
原始病理／檢驗／影像／病史／治療資料
  → source-specific Mapping + Provenance
  → Breast Cancer common FHIR facts
  ├→ Cancer Care Plan Task
  ├→ QBC／P4P Task
  └→ TWPAS Task + PAS-only application data
         → official TWPAS Apply Bundle
```

癌症診療計畫書與 QBC artifact 都不是正式 TWPAS 輸入。過渡期可以從同一份 secondary source 獨立產生三個 Task view，僅用於 Mapping、reconciliation 與 regression test。

## 輸入邊界

| 類型 | 來源 | 範例 | 是否可進 common layer |
|---|---|---|---|
| 共用臨床事實 | 原始報告、來源系統或已審核 secondary source | 診斷、TNM／Stage、marker、ECOG、基因、影像、既有治療、疾病狀態 | 是 |
| TWPAS Task-only | 當次申請流程、申請人、機構與支付規則 | 申報類別、案件類別、申請藥品、數量、用藥線別、續用註記、給付適應症 | 否 |
| 官方衍生規則 | TWPAS Profile、ValueSet、Constraint、CQL | Bundle 組成、必要 reference、品項與適應症條件 | 否；只在 Task projection 執行 |

缺少必要 Task-only 資料時，adapter 必須停止並回報缺項，不得從 Care Plan、QBC 或其他臨床欄位推測。

## TWPAS 輸出資源

官方申請 Bundle 可能包含下列資源；實際基數與條件以 TWPAS 1.2.5 artifact 為準：

- `Claim TWPAS`
- `Patient TWPAS`
- `Organization TWPAS`、`Encounter TWPAS`、`Practitioner TWPAS`
- `DiagnosticReport Image TWPAS`、`ImagingStudy TWPAS`、`Media TWPAS`
- `Observation Cancer Stage TWPAS`
- `DiagnosticReport TWPAS`
- `Observation Diagnostic TWPAS`、`Observation Laboratory Result TWPAS`
- `Observation Patient Assessment TWPAS`
- `MedicationRequest Treat TWPAS`
- `Procedure TWPAS`
- `DocumentReference TWPAS`
- `Observation Treatment Assessment TWPAS`
- `MedicationRequest Apply TWPAS`
- `Coverage TWPAS`
- 自主審查情境的 `ClaimResponse Self Assessment TWPAS`

申請結果由官方 `Bundle Response TWPAS`／`ClaimResponse TWPAS` 表達，不回寫或覆蓋 common facts；若結果帶來新的臨床判斷，必須經來源與審核流程另行建立 clinical resource。

## Profile 與版本策略

本 IG 使用 TW Core 1.0.0；TWPAS 1.2.5 應用說明記載其基礎為 TW Core 0.3.2。因此：

1. common facts 與 TWPAS output 分開產生及驗證。
2. adapter 建立新的 TWPAS projection resource，不對 common resource 直接增加 TWPAS `meta.profile`。
3. 只有通過官方 `tw.gov.mohw.nhi.pas#1.2.5` 驗證的 output 才可聲明符合該版本。
4. TWPAS 升版時必須鎖定新 package，重跑 differential、ValueSet、Constraint、CQL、crosswalk 與合成案例。

## CI Build 的價值與預警邊界

[TWPAS 1.2.6 CI Build](https://build.fhir.org/ig/TWNHIFHIR/pas/) 可提早顯示下一版可能影響申請輸出的 Profile、terminology 與 Constraint 變更，因此適合作為乳癌 Task 的相容性預警來源。它不定義完整的乳癌臨床語意，也不是已授權發布版本，不得取代 [TWPAS 1.2.5 正式版](https://nhicore.nhi.gov.tw/pas/)或用來宣告正式送件相容性。

| 驗證目標 | 用途 | Release gate | 可否作主 IG dependency |
|---|---|---|---|
| TWPAS 1.2.5 published | 現行正式輸出、驗證與外部驗收 | blocking | 否；在隔離的 adapter 驗證環境使用 |
| TWPAS 1.2.6 CI | 未來差異偵測與合成案例回歸 | advisory | 否 |

截至 2026-08-15，本草稿追蹤的 CI 預警包括：申請藥物劑量單位／包裝綁定、既有治療 `MedicationRequest` 劑量系統限制、藥品品項與乳癌 `C50` programCode 的 Bundle 條件，以及適應症代碼說明。這些項目應產生警告與 review item，但在新版正式發布前不得改變 1.2.5 的正式輸出行為。

預警處理流程：

1. 定期比較 CI 與目前 published version，記錄觀察日期與官方來源。
2. 將可能影響乳癌 projection 的變更加入 watchlist，標示受影響欄位、風險與所需合成測試。
3. CI 測試失敗只產生 advisory，不阻擋依 1.2.5 建置的 Preview。
4. 新版正式發布後，由維護者與臨床／術語／申報 reviewer 確認差異，再更新 package pin、crosswalk 與 release gate；不得自動升版。

## 驗收條件

本 Task 從 design draft 升為 executable preview 前，至少需要：

- common-to-TWPAS crosswalk 每列均有 target canonical、FHIR path、轉換、缺值與 loss policy。
- TWPAS-only 欄位完整盤點並可由申請介面或來源系統取得。
- 完全合成的乳癌申請 Bundle，不含真實病人、醫師或機構識別資料。
- 使用官方 TWPAS 1.2.5 package 驗證成功。
- 正向、缺值、錯誤代碼、錯誤 reference、品項／適應症 Constraint 與版本升級回歸測試。
- 對輸入 facts、Task-only 欄位及輸出 resources 建立 field-level traceability。
- 實際官方測試環境／收件流程的外部驗收證據；Publisher 通過不等於健保署收件通過。

## 本版產物

- 人類可讀對照：[乳癌共同資料至 TWPAS 對照](twpas-crosswalk.html)
- 機器可讀 crosswalk：`mappings/twpas/breast-common-to-twpas-1.2.5.csv`
- Task-only 欄位邊界：`mappings/twpas/twpas-task-only-fields-1.2.5.csv`
- 雙版本驗證政策：`mappings/twpas/twpas-version-policy.csv`
- CI 1.2.6 預警清單：`mappings/twpas/twpas-ci-1.2.6-watchlist.csv`
