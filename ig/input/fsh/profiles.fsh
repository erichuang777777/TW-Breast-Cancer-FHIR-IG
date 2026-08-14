Profile: QBCPatient
Parent: BreastCancerPatient
Id: qbc-patient
Title: "QBC Patient"
Description: "QBC／P4P Task 使用的病人 Profile，衍生自乳癌社群草稿的 BreastCancerPatient。"
* ^status = #draft
* ^experimental = true
* identifier 1..*
* identifier.system 1..1
* identifier.value 1..1
* birthDate 1..1

Profile: QBCDataItemObservation
Parent: Observation
Id: qbc-data-item-observation
Title: "QBC Data Item Observation Base"
Description: "QBC 欄位 Observation 的共同基礎限制。實作者應優先使用強型別衍生 Profile；無法安全轉型時使用 Raw Profile。"
* ^status = #draft
* ^experimental = true
* status = #final (exactly)
* status MS
* code 1..1
* code from QBCFieldValueSet (required)
* code MS
* subject 1..1
* subject only Reference(QBCPatient)
* subject MS
* value[x] 1..1
* value[x] MS

Profile: QBCRawDataItemObservation
Parent: QBCDataItemObservation
Id: qbc-raw-data-item-observation
Title: "QBC Raw Data Item Observation"
Description: "以 valueString 保存原始 QBC 值的可逆中介層；不表示已完成臨床術語標準化。"
* ^status = #draft
* ^experimental = true
* value[x] only string

Profile: QBCDateDataItemObservation
Parent: QBCDataItemObservation
Id: qbc-date-data-item-observation
Title: "QBC Date Data Item Observation"
Description: "以 FHIR dateTime 表示已通過 YYYYMMDD 驗證的 QBC 日期欄位。原始值仍應保存在來源或 Provenance。"
* ^status = #draft
* ^experimental = true
* code from QBCDateFieldValueSet (required)
* value[x] only dateTime

Profile: QBCIntegerDataItemObservation
Parent: QBCDataItemObservation
Id: qbc-integer-data-item-observation
Title: "QBC Integer Data Item Observation"
Description: "以 FHIR integer 表示已通過整數與範圍驗證的 QBC 計數或百分比欄位。"
* ^status = #draft
* ^experimental = true
* code from QBCIntegerFieldValueSet (required)
* value[x] only integer

Profile: QBCQuantityDataItemObservation
Parent: QBCDataItemObservation
Id: qbc-quantity-data-item-observation
Title: "QBC Quantity Data Item Observation"
Description: "以 UCUM 單位表示已通過小數格式與範圍驗證的 QBC 量測欄位（身高、體重、腫瘤大小）。單位碼由各衍生 Profile 或實作依欄位決定。"
* ^status = #draft
* ^experimental = true
* code from QBCQuantityFieldValueSet (required)
* value[x] only Quantity
* valueQuantity.system = "http://unitsofmeasure.org" (exactly)
* valueQuantity.code 1..1
* valueQuantity.value 1..1

Profile: QBCTumorSizeObservation
Parent: QBCQuantityDataItemObservation
Id: qbc-tumor-size-observation
Title: "QBC Tumor Size Observation"
Description: "以 UCUM cm 表示 QBC D047 術後顯微鏡下腫瘤大小。"
* ^status = #draft
* ^experimental = true
* code = $QBCFieldCS#D047
* valueQuantity.code = #cm (exactly)

Profile: QBCProvenance
Parent: Provenance
Id: qbc-provenance
Title: "QBC Provenance"
Description: "記錄 QBC 欄位值的來源、產生方式與人工審核資訊。"
* ^status = #draft
* ^experimental = true
* target 1..*
* target only Reference(QBCPatient or QBCDataItemObservation)
* recorded 1..1
* agent 1..*

Profile: QBCSubmissionBundle
Parent: $TWCoreBundle
Id: qbc-submission-bundle
Title: "QBC Submission Bundle"
Description: "封裝 QBC 個案、欄位值及來源資訊的非官方 FHIR collection Bundle。"
* ^status = #draft
* ^experimental = true
* identifier 1..1
* identifier.system 1..1
* identifier.value 1..1
* type = #collection (exactly)
* timestamp 1..1
* entry 1..*
* entry.fullUrl 1..1
* entry.resource 1..1
* entry ^slicing.discriminator.type = #profile
* entry ^slicing.discriminator.path = "resource"
* entry ^slicing.rules = #open
* entry contains
    patient 1..1 and
    observation 0..* and
    provenance 0..*
* entry[patient].resource only QBCPatient
* entry[observation].resource only QBCDataItemObservation
* entry[provenance].resource only QBCProvenance
