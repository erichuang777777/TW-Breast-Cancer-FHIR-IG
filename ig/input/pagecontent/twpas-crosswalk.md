# 乳癌共同資料至 TWPAS 1.2.5 對照

{% include disclaimer.md %}

本頁是 projection design，不是健保署官方規格副本。TWPAS 的 Profile、基數、值集與 Constraints 以官方 `tw.gov.mohw.nhi.pas#1.2.5` 為準；若本頁與官方 artifact 不一致，以官方 artifact 為準。

## Clinical facts crosswalk

| Common fact | 本 IG 候選來源 | 官方 TWPAS 目標 | 投影原則 | 狀態 |
|---|---|---|---|---|
| 病人識別與人口學 | `BreastCancerPatient` | `Patient TWPAS` | 依官方 identifier slices、姓名、性別與出生日期重新建立 projection；不得在公開範例使用真實識別碼 | design |
| 原發乳癌診斷 | `BreastCancerPrimaryCondition` | `Claim.diagnosis` | 保留診斷代碼、診斷日期與來源；Condition 的臨床語意不得被 Claim 行政欄位取代 | design |
| TNM／Stage | `BreastCancerStageGroupObservation` | `Observation Cancer Stage TWPAS`，由 `Claim.supportingInfo` 引用 | 保留 clinical／pathologic 類型、分期方法及版本；不得從 stage group 反推缺少的 T／N／M | design |
| ER／PR／HER2／Ki-67 | `BreastCancerTumorMarkerObservation` | `Observation Diagnostic TWPAS` 或 `Observation Laboratory Result TWPAS` | 依 assay、specimen、值型別與官方 ValueSet 決定目標；沒有足夠 metadata 時保存原始報告，不猜測代碼 | pending terminology review |
| 基因檢測 | source Observation + Specimen + DiagnosticReport | `Observation Diagnostic TWPAS` + genetic testing organization／specimen | 保存基因、變異、方法、檢體、檢測日期、機構及報告 lineage | design |
| ECOG／病人狀態 | assessment Observation | `Observation Patient Assessment TWPAS` | 保留量表種類、分數、評估時間及 performer | design |
| 檢驗結果 | laboratory Observation／DiagnosticReport | `Observation Laboratory Result TWPAS`／`DiagnosticReport TWPAS` | 結構化數值與報告附件並存；保留 UCUM、reference range、effective time 與 performer | design |
| 影像與影像報告 | ultrasound／image DiagnosticReport + ImagingStudy | `DiagnosticReport Image TWPAS` + `ImagingStudy TWPAS`／`Media TWPAS` | DICOM 與非 DICOM 依官方路徑分流，保留 accession／UID／body site／report date | design |
| 既有癌症用藥 | `BreastCancerMedicationRequest`／來源 medication record | `MedicationRequest Treat TWPAS` | 既有治療與本次申請品項分開；保留藥碼、劑量、頻率、期間、狀態與來源 | design |
| 本次申請品項 | 無；TWPAS-only | `MedicationRequest Apply TWPAS` | 由當次申請流程建立，不得由既有用藥自動複製 | task-only |
| 放射治療 | `BreastCancerTreatmentProcedure` | `Procedure TWPAS` | 保留日期、部位、療程及來源；官方需要的總劑量表示另依 TWPAS 規則 | design |
| 診療計畫文件 | Care Plan source document／`DocumentReference` | `DocumentReference TWPAS`，由 `Claim.supportingInfo[carePlanDocument]` 引用 | 文件是 supporting evidence，不是其他 facts 的唯一 source of truth | design |
| 治療後疾病狀態 | outcome Observation | `Observation Treatment Assessment TWPAS` | 保留評估時間、方法、evidence 與 performer；不得以審查結果代替臨床結果 | design |

## TWPAS-only boundary

下列資料屬申請案件，不應提升為乳癌 common clinical facts：

- `Claim.priority`：一般申請、自主審查、緊急報備等案件類別。
- `Claim.subType`：送核、補件、申復、爭議審議等申報類別。
- 申請機構、就醫科別、申請醫師與申請日期。
- 原受理編號／案件識別。
- 申請品項代碼、申請數量與單位。
- 用藥線別、續用註記、醫令類別。
- `Claim.item.programCode` 給付適應症條件。
- Coverage 與自主審查資訊。

## 資訊損失與追溯

每筆 projection 至少保留：source resource／element、source identifier、source version、target profile／path、轉換規則、原始碼和值、標準化碼和值、loss classification、review status 及產生版本。若 common fact 的精細度高於 TWPAS 欄位，TWPAS output 可以依官方格式縮減，但原始精細資料必須留在 common layer，不得被縮減結果覆寫。

## 尚未宣告完成

- 尚未取得完整 TWPAS-only 申請資料來源。
- 尚未建立 executable TWPAS adapter。
- 尚未產生及以官方 package 驗證完整乳癌申請 Bundle。
- 尚未完成 TWPAS 1.2.5 所有品項／給付適應症 Constraint 與 CQL 回歸測試。
- 尚未取得官方測試環境的收件證據。

