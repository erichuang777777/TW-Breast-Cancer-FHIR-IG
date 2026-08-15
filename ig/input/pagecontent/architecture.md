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
   └─ 平行 Task／文件投影層
      ├─ 癌症診療計畫書
      ├─ QBC／癌症治療申報
      ├─ 治療計畫／多專科討論
      ├─ TWPAS 癌症用藥事前審查投影
      └─ 癌症登記
```

## Current state

目前無法取得病理、檢驗與超音波等原始來源，因此已整理過的癌症診療計畫書 JSON 暫時作為 secondary source。兩個 adapter 各自執行，不形成 Task 依賴：

```text
同一份過渡期測試來源
  ├→ Care Plan adapter → Cancer Care Plan Task Bundle
  └→ QBC adapter       → QBC FHIR Bundle → QBC XML
                 \──── alignment／reconciliation check ────/
```

這只用來驗證欄位 Mapping 與發現不一致。不得把 Care Plan Bundle 當作 QBC 輸入，也不得把 QBC Bundle 回寫成 Care Plan 的臨床事實。secondary source 必須標記為「衍生文件」，不能冒充原始檢驗事實。

## Target state

```text
病理／檢驗／超音波／治療系統
  → source-specific Mapping
  → 乳癌 Canonical Facts + Provenance
  ├→ 產生癌症診療計畫書
  ├→ 直接產生 QBC 申報
  ├→ TWPAS adapter → 官方 TWPAS Apply Bundle
  ├→ 癌症登記
  ├→ 治療計畫
  └→ 多專科討論
```

所有 Task 都應讀取同一組 canonical facts，避免各自解析來源並得到不同結果。癌症診療計畫書與 QBC 是平行消費者；任何 Task-to-Task 轉換只可作為 migration、reconciliation 或 regression check，不是正式資料流。

TWPAS Task 另需申報類別、案件類別、申請品項、數量、用藥線別、續用註記、給付適應症、申請醫師與機構等 Task-only 資料。這些行政／支付流程資料不得提升為乳癌 canonical facts。adapter 將已審核的 common facts 與 Task-only 資料組合成官方 TWPAS Bundle，並以官方套件獨立驗證。

## Artifact 所有權

| Artifact | 所屬層 | 重用規則 |
|---|---|---|
| `BreastCancerSource*` 與標準 `ImagingStudy` | 來源證據層 | 保存 report／observation／specimen／imaging lineage |
| `BreastCancer*` clinical Profiles | Canonical facts 層 | 可被所有乳癌文件與 Task 重用 |
| 癌症診療計畫書、治療計畫、MDT | 平行 Task／文件投影層 | 各自從 canonical facts 產生；不得作為其他 Task 的事實來源 |
| `CancerCarePlanTask*` Profiles 與欄位 catalog | 癌症診療計畫書 Task | 表達診療計畫書需求與輸出，不擁有 QBC Task |
| `QBC*` Profiles、Extensions、CodeSystems | QBC Task | 不提升成通用乳癌臨床語意 |
| `Formal_Mapping_115` | QBC Task | 定義 common FHIR facts 到 QBC 的投影；secondary-source adapter 僅供過渡驗證 |
| TWPAS 1.2.5 Profiles、ValueSets 與 Constraints | 健保署官方 TWPAS Task | 本 IG 不複製或重新定義；TWPAS adapter 的輸出必須直接符合官方 canonical |
| `breast-common-to-twpas-1.2.5.csv` | TWPAS projection | 記錄 common facts 到官方 TWPAS resource/path 的對照、資訊損失與審查狀態 |

目前各層放在同一 package 方便 Preview 驗證。當第二個 Task 開始重用 canonical facts，或取得第一批原始報告後，可再拆成獨立 source adapter 與 task packages。
