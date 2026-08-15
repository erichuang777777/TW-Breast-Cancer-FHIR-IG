# 外部規格對齊

{% include disclaimer.md %}

| 規格 | 本草稿的關係 | Conformance 聲明 |
|---|---|---|
| FHIR R4 4.0.1 | 基礎標準 | 是 |
| TW Core 1.0.0 | 直接 package dependency；Patient 等 Profile 由其衍生 | 依個別 Profile 驗證 |
| mCODE 4.0.0 | 泛癌症語意與 canonical 對齊參考 | 否；未宣告完整 mCODE conformance |
| ICHOM Breast Cancer 1.0.0 | 乳癌 outcome、治療與復發概念參考 | 否 |
| TWPAS 1.2.5 | 健保署官方癌症用藥事前審查 Task contract；本草稿定義 common facts 到 TWPAS 的投影 | common layer 不宣告 TWPAS conformance；只有經官方套件驗證的 Task output 才可宣告 |

FHIR Profile 只有一個 `baseDefinition`。因此本草稿以 TW Core 作台灣結構父層，透過 Mapping Table、canonical reference 與文件說明對齊 mCODE／ICHOM，不建立虛假的多重繼承。

目前 `BreastCancerPatient` 已直接衍生自 TW Core Patient；其他乳癌 Condition、Observation、DiagnosticReport、Specimen、Procedure 與 MedicationRequest 草稿仍有部分直接衍生自 FHIR base resource。這些 Profile 只能稱為「以 TW Core 為台灣結構對齊基準」，不得宣稱已全部衍生自 TW Core。改父層前須逐一比較 TW Core 1.0.0 differential、現有範例與各 Task projection，確認不會造成不相容限制。

若未來要宣告 mCODE conformance，必須逐一驗證 mCODE 及其 US Core 父層限制是否與 TW Core 可同時滿足，並建立明確的 conformance 測試與 CapabilityStatement。

## TWPAS 版本隔離

本 IG 直接依賴 TW Core 1.0.0；TWPAS 1.2.5 官方應用說明記載其結構基礎為 TW Core 0.3.2。兩者不可只因 canonical 名稱相似就假設限制完全相容。本 Preview 採以下策略：

1. 乳癌 common facts 依本 IG 與 TW Core 1.0.0 驗證。
2. TWPAS adapter 產生新的 Task projection resources，不在同一 resource 的 `meta.profile` 宣稱未經證明的雙重 conformance。
3. TWPAS output 以 `tw.gov.mohw.nhi.pas#1.2.5` 獨立驗證。
4. 每次升級 TWPAS 版本時重跑 crosswalk、官方 Constraint、ValueSet 與合成案例回歸測試。

官方來源：[TWPAS 1.2.5 應用說明](https://nhicore.nhi.gov.tw/pas/)、[癌藥申請 Bundle 架構](https://nhicore.nhi.gov.tw/pas/vision-cancer.html)。
