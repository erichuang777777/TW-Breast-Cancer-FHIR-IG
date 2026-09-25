# QBC／P4P 申報 Task

{% include disclaimer.md %}

## Task 定位

QBC／P4P 是乳癌社群草稿下第一個完成 115 欄欄位契約技術 Mapping 與合成驗證的業務 Task；115/115 欄的 clinical review 與外部 VPN 驗收仍未完成。它與癌症診療計畫書是平行 Task，應各自讀取乳癌 common FHIR facts。QBC 只投影申報所需子集合，再依官方規格產生 QBC XML。FHIR Bundle 是交換與稽核中介層，不是健保署 VPN 的直接上傳格式。

## 輸入與輸出

| 項目 | 定義 |
|---|---|
| Trigger | 建立、更新或重新送出 QBC 個案申報資料 |
| Current transition input | 過渡期可由診療計畫書 JSON secondary-source adapter 取得候選值；不是讀取 Care Plan Task Bundle |
| Production input | 經來源 Mapping 與人工審核的乳癌 common FHIR facts，加上 QBC 專屬欄位 |
| Target input | 由病理、檢驗、超音波、治療與追蹤來源建立的乳癌 canonical facts |
| FHIR representation | QBC Patient、Data Item Observations、workflow Extensions、Provenance、Submission Bundle |
| Output | 驗證後 QBC XML、稽核紀錄與錯誤報告 |
| Acceptance | 115 欄 conformance、Big5 round-trip、合成測試；正式使用另需 VPN 驗收 |

## 邊界

- QBC 欄位是申報語意，不自動等同完整臨床語意。
- 診療計畫書 JSON 目前只作為 secondary source；Cancer Care Plan Task artifact 不是 QBC 輸入。
- QBC 與 Care Plan 各自從 common facts 產生；兩個 Task view 的互相比對只用於 reconciliation 與 regression test。
- QBC 專用 Extensions 與 CodeSystems 留在 Task 層。
- ER／PR／HER2／PD-L1、TNM 等可對齊乳癌共同層或 mCODE，但必須保留 QBC 原始值。
- `QBCPatient` 衍生自共同層 `BreastCancerPatient`；其他 QBC raw observations 暫留 Task 層，待共同臨床 Profile 成熟後再逐步提升。

完整對應請見「[正式 Mapping 候選與簽核閘門](formal-mapping.html)」及「[115 欄逐欄規則稽核](field-audit.html)」。
