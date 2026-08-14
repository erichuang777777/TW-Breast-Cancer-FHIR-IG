# QBC／P4P 申報 Task

{% include disclaimer.md %}

## Task 定位

QBC／P4P 是乳癌社群草稿下的第一個可執行業務 Task，目標是把乳癌 canonical facts 或目前可取得的衍生文件轉成可追溯的 FHIR 表示，再依官方規格產生 QBC XML。FHIR Bundle 是交換與稽核中介層，不是健保署 VPN 的直接上傳格式。

## 輸入與輸出

| 項目 | 定義 |
|---|---|
| Trigger | 建立、更新或重新送出 QBC 個案申報資料 |
| Current input | 已整理的癌症診療計畫書、QBC 115 欄候選值及人工審核結果 |
| Target input | 由病理、檢驗、超音波、治療與追蹤來源建立的乳癌 canonical facts |
| FHIR representation | QBC Patient、Data Item Observations、workflow Extensions、Provenance、Submission Bundle |
| Output | 驗證後 QBC XML、稽核紀錄與錯誤報告 |
| Acceptance | 115 欄 conformance、Big5 round-trip、合成測試；正式使用另需 VPN 驗收 |

## 邊界

- QBC 欄位是申報語意，不自動等同完整臨床語意。
- 癌症診療計畫書是目前的 bridge input，不是永久 source of truth。
- 未來可由 canonical facts 先產診療計畫書再申報，也可直接投影成 QBC；兩者必須使用相同 Provenance 與 reconciliation 規則。
- QBC 專用 Extensions 與 CodeSystems 留在 Task 層。
- ER／PR／HER2／PD-L1、TNM 等可對齊乳癌共同層或 mCODE，但必須保留 QBC 原始值。
- `QBCPatient` 衍生自共同層 `BreastCancerPatient`；其他 QBC raw observations 暫留 Task 層，待共同臨床 Profile 成熟後再逐步提升。

完整對應請見「[正式 Mapping 候選與簽核閘門](formal-mapping.html)」及「[115 欄逐欄規則稽核](field-audit.html)」。
