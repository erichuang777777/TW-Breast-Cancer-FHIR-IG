# 外部規格對齊

{% include disclaimer.md %}

| 規格 | 本草稿的關係 | Conformance 聲明 |
|---|---|---|
| FHIR R4 4.0.1 | 基礎標準 | 是 |
| TW Core 1.0.0 | 直接 package dependency；Patient 等 Profile 由其衍生 | 依個別 Profile 驗證 |
| mCODE 4.0.0 | 泛癌症語意與 canonical 對齊參考 | 否；未宣告完整 mCODE conformance |
| ICHOM Breast Cancer 1.0.0 | 乳癌 outcome、治療與復發概念參考 | 否 |
| TWPAS | 台灣癌藥事前審查平行 Task 參考 | 否；不是本 IG 的父層 |

FHIR Profile 只有一個 `baseDefinition`。因此本草稿以 TW Core 作台灣結構父層，透過 Mapping Table、canonical reference 與文件說明對齊 mCODE／ICHOM，不建立虛假的多重繼承。

若未來要宣告 mCODE conformance，必須逐一驗證 mCODE 及其 US Core 父層限制是否與 TW Core 可同時滿足，並建立明確的 conformance 測試與 CapabilityStatement。
