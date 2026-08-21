# 正式 Mapping 候選與簽核閘門

{% include disclaimer.md %}

## 技術狀態

`QBC_FHIR_Mapping_TaskSpec_v1.0-preview.1.xlsx` 的 `Architecture` 工作表說明乳癌共同層與 QBC Task 的關係；`Formal_Mapping_115` 是 QBC Task 的 preview mapping 規格。每一個 QBC Tag 均有唯一的主要 Target Resource 與 Target Element，並包含：

- source condition、source/target cardinality 與 datatype；
- target profile canonical URL 與明確版本；
- mCODE semantic alignment canonical（只表示語意對齊，不表示 conformance）；
- ConceptMap／術語關係、轉換、null、repeat、資訊損失及 round-trip policy；
- technical status、approval gate 與 release status。

115 個 QBC Tag 皆有且只能有一個 `QBC-MAP-{Tag}` 主要規則。候選 Resource 不再使用 `/` 並列；需要額外臨床資源時，應由轉換器產生 supporting resource，主要 QBC round-trip 值仍由 mapping rule 與 Provenance 管控。

個管品管／季報的共同資料 mapping 另以 34 個 canonical facts 為單位，目前拆成 55 個 FHIR target alternatives。Publisher snapshot 稽核確認 49 個 alternatives 可解析到本 IG 的確切 Profile／ElementDefinition，1 個是由 ER、PR、HER2 IHC、HER2 ISH 與 Ki-67 五項輸入組成的 derived rule；其餘 5 個 alternatives 仍無完整 Profile／element。受影響 facts 是放療總劑量、組織型態、轉院組織關係、放療療程狀態覆蓋與最後接觸時間。

路徑可解析的 49 列中另發現 12 個 semantic Profile gaps，影響 8 個 facts：pN／pT 誤用 stage-group shell；診斷性 core biopsy 誤用 treatment Procedure shell；賀爾蒙、化療及 anti-HER2 治療以 `MedicationRequest` 醫囑冒充實際給藥，並把 `authoredOn` 開立時間當治療開始時間；`MedicationRequest.performer` 只能表示預期執行者；`MedicationRequest.status` 只能表示醫囑狀態。另有 prior-year new-diagnosis cohort 只映射 episode start，缺少 episode-scoped new-diagnosis discriminator。合併結構、語意與 coverage 缺口後共有 13 個 blocked projection facts。另有 3 個百分比 Quantity 已解析到 `Observation.value[x]`，但 `%` 單位仍待來源契約與臨床核准。

因此本階段的 mapping 完成標準不是「有填 target path」，而是每個 alternative 都具備可解析且語意適配的 Profile canonical、ElementDefinition id/path、choice datatype／slice／unit 規則與阻擋狀態。正式門檻為 55/55 exact projection、unresolved path 0、semantic Profile gap 0、unit-policy-pending 0、blocked fact 0；即使達成，仍須另外完成原始 table/column 或 API path、19 維來源契約、Provenance 與逐案驗證。

## 新增的 computable artifacts

- 9 個 QBC Extensions：收案類別、個案分類、診斷院所分類、治療順序、治療類型、治療院所分類、治療狀態、追蹤狀態及轉出日期。
- `QBCWorkflowCodeSystem` 與六個 workflow ValueSets。
- `QBCGenderToFHIRAdministrativeGender` ConceptMap。
- `QBCLateralityToSNOMEDCT` ConceptMap。

## 術語處理

| 項目 | 正式候選決策 | 簽核原因 |
|---|---|---|
| PR | 定性採 LOINC `85339-0`；百分比採 `85325-9`，限 immune stain 已確認 | 需比對院內 LIS assay |
| HER2 FISH | 乳癌檢體 FISH 採 `85318-4`；一般 tissue FISH 才可退回 `31150-6` | 需確認 specimen 與 method |
| PD-L1 | QBC 未提供 clone、assay、CPS/TPS 或 threshold，禁止硬指定 assay-specific LOINC；保留 raw QBC 結果 | 需院內 LIS 補足 metadata |
| TNM／Stage | 保存 QBC 原始值及 AJCC edition；mCODE 只做 semantic alignment | AJCC 版本及授權需治理 |

## Preview 與正式使用的治理原則

只有 repository `PUBLICATION_ACCEPTANCE_MATRIX.md` 定義的 Community Preview gate 通過後，專案維護者才可發布版本化 Preview；清楚標示非官方、`draft`／`experimental=true` 是必要條件，但單靠標示並不足夠。技術測試通過也不等於主管機關、院內或臨床權責核准；Excel 的 `Approval_Register` 保留正式或官方使用時的治理閘門，簽核人應填寫決策、姓名、日期、證據位置及簽核版本雜湊。

若要宣告正式生產使用或官方適用，仍需完成：QBC 申報規則、臨床分類、FHIR 架構、病理／術語、AJCC／SNOMED／藥品碼授權、個資資安、跨系統 UAT、VPN receipt，以及 publisher／canonical 核准。完成後才能另行發布不可變的 `1.0.0`、`status=active`、`experimental=false`。
