# Task 目錄

{% include disclaimer.md %}

Task 是業務 Use Case，不必然等於 FHIR `Task` Resource。只有需要交換工作指派、承辦者、狀態或輸入輸出時，才使用 FHIR `Task`。

| Task | 狀態 | 共同層使用 | 主要輸出 |
|---|---|---|---|
| QBC／P4P 申報 | Preview 1.0 | `BreastCancerPatient`，其餘概念採 Mapping 對齊 | QBC FHIR Bundle、115 欄 Mapping、QBC XML／稽核檔 |
| 癌症診療計畫書產生 | 尚未建立；目前只作 bridge input | 診斷、分期、marker、治療與 Provenance | Composition／document Bundle 候選 |
| 乳癌藥物事前審查 | 尚未建立 | 預計重用診斷、分期、marker、MedicationRequest | 應優先評估 TWPAS |
| [癌症登記](task-tcr.html) | Draft：長表 99 欄 Questionnaire、17 欄已驗證碼表 | 預計重用診斷、病理、分期、治療與 outcome | 癌登長表申報列、Task／QuestionnaireResponse |
| 乳癌病理交換 | 尚未建立 | 預計重用診斷與 marker | DiagnosticReport／Observation |
| 多專科討論 | 尚未建立 | 預計重用所有 canonical facts | 會議決議／CarePlan／Composition 候選 |
| 乳癌追蹤與 outcome | 尚未建立 | 預計重用 Episode、治療與 outcome | 待參考 ICHOM |

新增 Task 時，先建立 Use Case、actor、trigger、input、output 及驗收條件，再判斷是否需要新增 Profile；不得把單一 Task 的行政代碼提升成乳癌通用臨床術語。
