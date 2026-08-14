# 分層架構

{% include disclaimer.md %}

本草稿把來源證據、可重用臨床事實、衍生文件與業務 Task 分開。癌症診療計畫書不是最上游原子來源，而是由病理、檢驗、影像及治療紀錄整理出的衍生資料產品。

```text
FHIR R4／TW Core
└─ 乳癌 FHIR 社群草稿
   ├─ 來源證據層
   │  ├─ 病理報告 → DiagnosticReport + Observation + Specimen
   │  ├─ 檢驗報告 → DiagnosticReport + Observation + Specimen
   │  └─ 超音波／影像 → DiagnosticReport + ImagingStudy + Observation
   ├─ 乳癌 Canonical Facts 層
   │  ├─ 原發診斷、組織學與部位
   │  ├─ TNM／Stage
   │  ├─ ER／PR／HER2／Ki-67／PD-L1
   │  └─ 手術、藥物、放療、追蹤與結果
   ├─ 衍生文件／臨床協作層
   │  ├─ 癌症診療計畫書
   │  ├─ 治療計畫
   │  └─ 多專科討論紀錄
   └─ 對外 Task／投影層
      ├─ QBC／癌症治療申報
      ├─ 癌藥申請／事前審查
      └─ 癌症登記
```

## Current state

目前無法取得病理、檢驗與超音波等原始來源，因此使用已整理過的癌症診療計畫書作為 bridge input：

```text
癌症診療計畫書
  → QBC adapter／人工核對
  → QBC FHIR Task Bundle
  → QBC XML／癌症治療申報
```

這條路徑可用，但必須把來源標記為「衍生文件」，不能把計畫書欄位宣告成原始檢驗事實。

## Target state

```text
病理／檢驗／超音波／治療系統
  → source-specific Mapping
  → 乳癌 Canonical Facts + Provenance
  ├→ 產生癌症診療計畫書
  ├→ 直接產生 QBC 申報
  ├→ 癌藥申請
  ├→ 癌症登記
  ├→ 治療計畫
  └→ 多專科討論
```

所有輸出都應讀取同一組 canonical facts，避免每個 Task 重複解析文件並得到不同結果。是否先產生癌症診療計畫書是流程選擇，不應成為 QBC 的必要技術依賴。

## Artifact 所有權

| Artifact | 所屬層 | 重用規則 |
|---|---|---|
| `BreastCancerSource*` 與標準 `ImagingStudy` | 來源證據層 | 保存 report／observation／specimen／imaging lineage |
| `BreastCancer*` clinical Profiles | Canonical facts 層 | 可被所有乳癌文件與 Task 重用 |
| 癌症診療計畫書、治療計畫、MDT | 衍生文件／協作層 | 從 canonical facts 產生，也可暫作 bridge input |
| `QBC*` Profiles、Extensions、CodeSystems | QBC Task | 不提升成通用乳癌臨床語意 |
| `Formal_Mapping_115` | QBC Task | 定義 canonical／bridge input 到 QBC 的投影 |

目前各層放在同一 package 方便 Preview 驗證。當第二個 Task 開始重用 canonical facts，或取得第一批原始報告後，可再拆成獨立 source adapter 與 task packages。
