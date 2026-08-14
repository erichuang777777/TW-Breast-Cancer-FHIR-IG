# 乳癌 FHIR 實作指引－社群草稿

{% include disclaimer.md %}

本實作指引是一套以台灣情境為背景的乳癌 FHIR 社群草稿。它先定義跨業務流程可重用的乳癌共同資料層，再將特定申報或交換流程放入 Task 模組。目前第一個可執行的 Task 是「QBC／P4P 申報」。

## 版本與基礎

- Package ID：`io.github.erichuang777777.breast-cancer`
- Canonical：`https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG`
- 版本：`1.0.0-preview.1`
- 狀態：`draft`／`experimental`
- FHIR：R4 `4.0.1`
- 結構基礎：`tw.gov.mohw.twcore#1.0.0`
- 語意參考：mCODE `4.0.0`、ICHOM Breast Cancer `1.0.0`

## 內容分層

1. **乳癌共同層**：提供 Patient、Primary Condition、Stage、Tumor Marker、Treatment、Medication 與 Episode of Care 的社群候選 Profiles。
2. **Task 層**：定義每個業務流程自己的必填規則、交換方式、Mapping、驗證與範例。
3. **QBC／P4P Task**：保存 115 欄來源規格、FHIR 對應、可逆轉換、業務規則及 XML／VPN 驗證邊界。

共同層不等於完整乳癌照護標準；QBC Task 也不代表整套乳癌 IG。實作者只能宣告其實際完成且通過驗證的 Profile 與 Task。

## 設計原則

1. TW Core 是台灣結構與識別碼的直接 dependency。
2. mCODE 與 ICHOM 是語意參考，除非逐項驗證，否則不宣告其完整 conformance。
3. 乳癌共用概念與 QBC 專用申報規則分開管理。
4. 所有來源值均可追溯；資訊不足時不得推論 assay、分期版本或臨床語意。
5. 正式 QBC XML 與健保 VPN 驗收仍以主管機關當期規範為準。

從「[分層架構](architecture.html)」開始閱讀，再依需要進入「[乳癌共同資料模型](common-model.html)」或「[QBC／P4P Task](task-qbc.html)」。
