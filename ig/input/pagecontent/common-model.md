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
| `BreastCancerEpisodeOfCare` | 串接診斷、治療與追蹤期間 | FHIR EpisodeOfCare |

`BreastCancerStageGroupObservation` 與 `BreastCancerTumorMarkerObservation` 已由抽象的 `BreastCancerSourceObservation` 衍生；`QBCPatient` 則由 `BreastCancerPatient` 衍生，形成可由機器驗證的「來源證據 → canonical facts → Task」關係。

## 尚待社群治理

- 乳癌診斷 code、laterality 與 morphology 的必要綁定。
- AJCC edition 的統一表示及授權邊界。
- ER／PR／HER2／PD-L1 的 assay、specimen、score 與 threshold 模型。
- 病理、影像、基因體及治療療程的跨 Task 共用 cardinality。
- 台灣藥碼、SNOMED CT、LOINC 與院內碼的 ConceptMap。

在上述治理完成前，Task 必須保存原始值與 Provenance，不得因缺少 metadata 而自動指定過度精確的標準碼。
