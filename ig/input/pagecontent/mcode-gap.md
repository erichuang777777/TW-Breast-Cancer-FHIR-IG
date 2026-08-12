# mCODE 對應與缺口

{% include disclaimer.md %}

本草案以 mCODE 4.0.0 作為對照基準。mCODE 是 US Realm IG，依賴 US Core；本臺灣草案以 TW Core 為基礎，因此不以多重繼承或僅加入 dependency 的方式宣稱 mCODE conformance。

| QBC 領域 | 建議 FHIR／mCODE 表示 | 狀態 |
|---|---|---|
| Patient、生日、性別 | TW Core Patient；內容與 CancerPatient 對齊 | partial |
| 原發癌症 | Condition／PrimaryCancerCondition | partial；需 ICD-O/SNOMED 治理 |
| T、N、M、Stage | mCODE TNM category／stage profiles | partial；需 AJCC 版本與授權決議 |
| ER、PR、HER2、Ki-67 | TumorMarkerTest＋LOINC／UCUM | partial；部分 assay code 待專家確認 |
| BRCA | GenomicsReport／GenomicVariant | partial；目前 QBC 值不足以完整表達 variant |
| PD-L1 | TumorMarkerTest | partial；缺 assay 與 CPS/TPS 等語意 |
| 手術 | CancerRelatedSurgicalProcedure | partial；需院內碼 ConceptMap |
| 藥物治療 | CancerRelatedMedicationAdministration | partial；需臺灣藥碼映射 |
| 放射治療 | RadiotherapyCourseSummary／Volume | partial；需治療系統資料 |
| QBC 收案、分類、追蹤狀態 | EpisodeOfCare／QBC Extension | no exact map |

完整 115 欄逐欄 mapping、信心等級、術語候選與待確認事項收錄於 `QBC_FHIR_TWCore_mCODE_Mapping_v0.1.xlsx`。在所有 `pending`／`Review` 項目完成治理前，不宣稱整體 mCODE conformant。
