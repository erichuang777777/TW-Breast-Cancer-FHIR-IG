# 癌症診療計畫書 Task／Cancer Care Plan Task

{% include disclaimer.md %}

## Task 定位

癌症診療計畫書有自己的欄位、條件與臨床流程，因此是乳癌 IG 內的獨立 Task。它與 QBC／P4P 是平行 Task；兩者都應從乳癌共用 FHIR facts 取得資料，不互為正式輸入或輸出。

The cancer care plan has its own fields, conditions, and workflow. It is parallel to QBC/P4P; both consume reusable breast-cancer FHIR facts and neither task is a production input to the other.

## 目前輸入契約

目前來源是院內系統擷取的私有 JSON，必要結構為：

```text
schema_version
sections
├─ basic.fields[]
├─ reference_reports.fields[] / text
├─ treatment_plan.fields[] / text
└─ disclosure.fields[] / text
```

機器可讀契約位於 `qbc_workbench/data/cancer_care_plan.schema.json`。`chart`、表單值、報告及計畫文字可能包含 PHI，只能留在受控環境，不得提交至公開 repo、IG examples 或 CI log。

去除所有個案值後的 223 欄單一樣本基線 catalog 位於 `qbc_workbench/data/cancer_care_plan_field_catalog.json`；可閱讀版本見「[診療計畫書欄位盤點](care-plan-field-inventory.html)」。2026-01 受控批次稽核觀察到 314 個唯一 controls 與 6 種結構變體，新增 91 controls 均先列為待審；詳見「[來源格式稽核](care-plan-source-audit.html)」。

## 欄位所有權

| 類型 | 定義 | 範例 | 處理方式 |
|---|---|---|---|
| `shared` | 多個 Task 共用，語意屬於乳癌 common FHIR layer，不屬於 Care Plan 或 QBC | laterality、TNM、ER／PR／HER2、Ki-67 | 逐步提升為共用 Condition／Observation 等 Profiles；各 Task 各自 Mapping |
| `care-plan-only` | 診療計畫需要、QBC 不收 | ECOG、家族史、個人病史、共病、診斷方式、切緣、完整計畫文字 | 保留在 CarePlan／QuestionnaireResponse，不得丟棄 |
| `derived` | 由表單或規則計算 | 自動分期顯示 | 保留算法、版本與 Provenance；不可假裝是原始事實 |
| `qbc-only` | 只屬於申報／VPN | 批次、申報與回覆狀態 | 不回寫成診療計畫臨床內容 |

## FHIR 輸出

`CancerCarePlanTaskBundle` 是 collection Bundle，至少包含：

- `BreastCancerPatient`
- `BreastCancerPrimaryCondition`
- `CancerCarePlanTaskQuestionnaireResponse`：完整保存所有有值的來源欄位，包括 QBC 沒有的額外欄位
- `CancerCarePlanTaskCarePlan`：診療計畫、活動及 supporting information
- `CancerCarePlanTaskProvenance`：來源雜湊、產生方式及稽核關係

完全合成範例：[Cancer Care Plan Task Bundle](Bundle-cancer-care-plan-task-bundle-example.html)。

## 正式資料鏈與目前核對工具

```text
原始資料 → Breast Cancer common FHIR facts + Provenance
  ├→ Cancer Care Plan Task Bundle
  └→ QBC Task Bundle → Big5 XML／VPN
```

目前私有診療計畫書 JSON 是過渡期 secondary source。`transform-care-plan` 只產生 Care Plan Task Bundle：

CLI：

```powershell
python -m qbc_workbench.cli transform-care-plan `.\private\cases\SYNTHETIC.case.json `
  --case SYNTHETIC-CASE `
  --output `.\runtime\care-plan-output
```

輸出目錄會產生 `<case>.care-plan.fhir.json`。

若要檢查兩個 adapter 對同一測試來源是否一致，可執行：

```powershell
python -m qbc_workbench.cli check-task-alignment `.\private\cases\SYNTHETIC.case.json `
  --case SYNTHETIC-CASE `
  --output `.\runtime\task-alignment
```

此命令會獨立產生 Care Plan check Bundle 與 QBC check Bundle；只供 reconciliation／regression test，不表示 Task-to-Task conversion。

## 發布前人工審查／簽核

Preview 可先發布；下列簽核是正式導入或把欄位提升成 canonical fact 前的治理閘門：

| 審查項目 | 建議角色 | 目前狀態 |
|---|---|---|
| 314-control 多檔 union、6 種表單變體與新增 91 controls 是否涵蓋目前表單版本 | 表單／癌症個管流程負責人 | 待簽核；223-control catalog 僅為單一來源 Preview 基線 |
| 欄位屬於 shared、care-plan-only 或 derived 的分類 | 乳癌臨床專家 + 資料治理負責人 | 待簽核 |
| 每欄臨床定義、單位、值域、必填與條件規則 | 乳癌臨床專家 | 待簽核 |
| 提升到 Condition／Observation／Procedure 等 FHIR path 的選擇 | FHIR 實作負責人 | 待簽核 |
| LOINC／SNOMED CT／院內碼等術語與授權 | 術語負責人 | 待簽核 |
| common facts → Care Plan 與 common facts → QBC 的獨立 Mapping、缺值與衝突處理 | Care Plan + QBC 負責人 | 25 個重疊控制項可做 alignment check；正式 common Mapping 仍待逐欄核對 |
| PHI、存取、保存、稽核與公開範例政策 | 資安／法遵 | 待機構導入時確認 |

## 尚未完成

- 既有 223-control catalog 是單一來源基線；受控批次 union 為 314 controls。新增 91 controls 尚未完成欄位定義、條件、術語與 FHIR path 審查。
- 原子病理、檢驗、超音波來源尚未接入；現階段診療計畫 JSON 只是 secondary source，不是其他 Task 的上游輸出。
- `QuestionnaireResponse` 先保存來源表單語意；欄位完成治理後，應逐步提升成共用 Condition、Observation、DiagnosticReport、Procedure 或 MedicationRequest。
- 正式臨床使用仍需在地規則、術語、資安與工作流程審查。
