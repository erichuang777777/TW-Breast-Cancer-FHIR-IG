# Task 目錄

{% include disclaimer.md %}

Task 是業務 Use Case，不必然等於 FHIR `Task` Resource。只有需要交換工作指派、承辦者、狀態或輸入輸出時，才使用 FHIR `Task`。

| Task | 狀態 | 共同層使用 | 主要輸出 |
|---|---|---|---|
| 癌症診療計畫書 | Preview 1.0 可執行草稿 | 與 QBC 平行重用 Patient、Condition、診斷、分期、marker、治療與 Provenance | CarePlan、QuestionnaireResponse、Provenance、Task Bundle |
| QBC／P4P 申報 | Preview 1.0 | `BreastCancerPatient`，其餘概念採 Mapping 對齊 | QBC FHIR Bundle、115 欄 Mapping、QBC XML／稽核檔 |
| TWPAS 癌症用藥事前審查 | 架構與 Mapping 草稿 | 重用診斷、分期、marker、ECOG、報告、既有治療及 outcome | 由 adapter 產生符合官方 `tw.gov.mohw.nhi.pas#1.2.5` 的 Apply Bundle；本 IG 不重製官方 Profiles |
| 癌症登記 | 尚未建立 | 預計重用診斷、病理、分期、治療與 outcome | Registry submission |
| 癌症診療計畫書產生 | 尚未建立；目前只作 bridge input | 診斷、分期、marker、治療與 Provenance | Composition／document Bundle 候選 |
| 乳癌藥物事前審查 | 尚未建立 | 預計重用診斷、分期、marker、MedicationRequest | 應優先評估 TWPAS |
| [癌症登記](task-tcr.html) | Draft：長表 99 欄 Questionnaire、18 欄已驗證碼表 | 預計重用診斷、病理、分期、治療與 outcome | 癌登長表申報列、Task／QuestionnaireResponse |
| 乳癌病理交換 | 尚未建立 | 預計重用診斷與 marker | DiagnosticReport／Observation |
| 多專科討論 | 尚未建立 | 預計重用所有 canonical facts | 會議決議／CarePlan／Composition 候選 |
| 乳癌追蹤與 outcome | 尚未建立 | 預計重用 Episode、治療與 outcome | 待參考 ICHOM |

新增 Task 時，先建立 Use Case、actor、trigger、input、output 及驗收條件，再判斷是否需要新增 Profile；不得把單一 Task 的行政代碼提升成乳癌通用臨床術語。

TWPAS 是中央健康保險署維護的正式 IG。本草稿只定義乳癌共同資料如何投影至 TWPAS，以及哪些申請資料必須在 Task 執行時另行取得；官方 TWPAS Profile、ValueSet、Constraint 與版本異動始終優先。
