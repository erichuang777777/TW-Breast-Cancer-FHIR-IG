# 乳癌共同資料模型

{% include disclaimer.md %}

## 共同 Profiles

| Profile | 用途 | 直接父層 |
|---|---|---|
| `BreastCancerPatient` | 乳癌 Task 共用病人識別與人口學資料 | TW Core Patient |
| `BreastCancerSourceDiagnosticReport` | 病理、檢驗、超音波等來源報告的抽象外殼 | FHIR DiagnosticReport |
| `BreastCancerPathologyReport` | 具體病理來源報告 | Source DiagnosticReport |
| `BreastCancerLaboratoryReport` | 具體檢驗來源報告 | Source DiagnosticReport |
| `BreastCancerUltrasoundReport` | 具體乳房超音波來源報告；影像引用標準 ImagingStudy | Source DiagnosticReport |
| `BreastCancerSourceObservation` | 從來源報告取得的原子 finding／result | FHIR Observation |
| `BreastCancerSourceSpecimen` | 病理與檢驗檢體 lineage | FHIR Specimen |
| `BreastCancerPathologySpecimen` | 具體病理檢體 lineage | Source Specimen |
| `BreastCancerPrimaryCondition` | 原發乳癌診斷與部位 | FHIR Condition |
| `BreastCancerStageGroupObservation` | 分期群組及分期方法／版本 | FHIR Observation |
| `BreastCancerTumorMarkerObservation` | ER、PR、HER2、Ki-67、PD-L1 等結果外殼 | FHIR Observation |
| `BreastCancerTreatmentProcedure` | 手術、放療與其他非藥物治療 | FHIR Procedure |
| `BreastCancerMedicationRequest` | 全身性治療用藥要求 | FHIR MedicationRequest |
| `BreastCancerMedicationAdministration` | 全身性治療實際給藥事件；醫囑本身不得視為已給藥 | FHIR MedicationAdministration |
| `BreastCancerEpisodeOfCare` | 串接診斷、治療與追蹤期間 | FHIR EpisodeOfCare |
| `BreastCancerCommonFactsBundle` | Task-neutral 的來源證據與共用 facts 交換邊界；供平行 Task 獨立取用 | FHIR collection Bundle |

`BreastCancerStageGroupObservation` 與 `BreastCancerTumorMarkerObservation` 已由抽象的 `BreastCancerSourceObservation` 衍生；`QBCPatient` 則由 `BreastCancerPatient` 衍生，形成可由機器驗證的「來源證據 → canonical facts → Task」關係。

癌症診療計畫書 Task 另外定義 `CancerCarePlanTaskCarePlan`、`CancerCarePlanTaskQuestionnaireResponse`、`CancerCarePlanTaskProvenance` 與 `CancerCarePlanTaskBundle`。這些是 Task 投影，不等同於共同臨床 facts。QBC 與 Care Plan 是平行消費者；重疊欄位經臨床與術語審查後，應提升到上表的共用 Profiles，再由兩個 Task 各自 Mapping。

TWPAS 也是平行消費者。乳癌診斷、分期、marker、ECOG、報告、既有治療與 outcome 可由共同層投影；申報類別、申請品項、數量、用藥線別、給付適應症與申請者等資料仍屬 TWPAS Task。官方 TWPAS resources 是輸出 contract，不是本共同層的父層，也不在此重新定義。

## 尚待社群治理

- 乳癌診斷 code、laterality 與 morphology 的必要綁定。
- AJCC edition 的統一表示及授權邊界。
- ER／PR／HER2／PD-L1 的 assay、specimen、score 與 threshold 模型。
- 病理、影像、基因體及治療療程的跨 Task 共用 cardinality。
- 台灣藥碼、SNOMED CT、LOINC 與院內碼的 ConceptMap。

在上述治理完成前，Task 必須保存原始值與 Provenance，不得因缺少 metadata 而自動指定過度精確的標準碼。
