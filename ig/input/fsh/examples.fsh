Instance: QBCPatientExample
InstanceOf: QBCPatient
Usage: #example
Title: "完全合成的 QBC 個案"
Description: "只供規格驗證使用，不代表真實人物。QBC 主表的 `ID` 欄位可能是國民身分證統一編號、居留證號或護照號；本範例示範以 TW Core Patient 的 `idCardNumber` slice 表示身分證的情形，居留證與護照請改用 `residentNumber` 或 `passportNumber` slice。"
* id = "qbc-patient-example"
* identifier[idCardNumber].type.coding.system = "http://terminology.hl7.org/CodeSystem/v2-0203"
* identifier[idCardNumber].type.coding.code = #NNxxx
* identifier[idCardNumber].system = "http://www.moi.gov.tw"
* identifier[idCardNumber].value = "Z000000000"
* gender = #female
* birthDate = "1970-01-01"

Instance: QBCStageObservationExample
InstanceOf: QBCRawDataItemObservation
Usage: #example
Title: "合成的 QBC 分期欄位"
Description: "以原始 QBC 字串保存的合成範例。"
* id = "qbc-stage-example"
* status = #final
* code = $QBCFieldCS#D008 "（新輔助）癌症臨床分期 TNM 計算結果"
* subject = Reference(QBCPatientExample)
* effectiveDateTime = "2026-01-01T00:00:00Z"
* performer.display = "Synthetic clinical reviewer"
* valueString = "StageⅡA"

Instance: QBCNodeCountObservationExample
InstanceOf: QBCIntegerDataItemObservation
Usage: #example
Title: "合成的 QBC 淋巴結計數"
Description: "示範通過範圍檢查後，以 integer 表示 D042。"
* id = "qbc-node-count-example"
* status = #final
* code = $QBCFieldCS#D042 "（術後）腋下淋巴結陽性顆數"
* subject = Reference(QBCPatientExample)
* effectiveDateTime = "2026-01-01T00:00:00Z"
* performer.display = "Synthetic clinical reviewer"
* valueInteger = 2

Instance: QBCDiagnosisDateObservationExample
InstanceOf: QBCDateDataItemObservation
Usage: #example
Title: "合成的 QBC 診斷日期"
Description: "示範經 YYYYMMDD 規則確認後的強型別日期。"
* id = "qbc-diagnosis-date-example"
* status = #final
* code = $QBCFieldCS#D001 "（新輔助）最初診斷日期"
* subject = Reference(QBCPatientExample)
* effectiveDateTime = "2026-01-01T00:00:00Z"
* performer.display = "Synthetic clinical reviewer"
* valueDateTime = "2026-01-01T00:00:00Z"

Instance: QBCTumorSizeObservationExample
InstanceOf: QBCTumorSizeObservation
Usage: #example
Title: "合成的 QBC 腫瘤大小"
Description: "示範以 UCUM cm 表示 D047。"
* id = "qbc-tumor-size-example"
* status = #final
* code = $QBCFieldCS#D047 "（術後）手術時顯微鏡下腫瘤大小"
* subject = Reference(QBCPatientExample)
* effectiveDateTime = "2026-01-01T00:00:00Z"
* performer.display = "Synthetic clinical reviewer"
* valueQuantity.value = 1.2
* valueQuantity.unit = "cm"
* valueQuantity.system = "http://unitsofmeasure.org"
* valueQuantity.code = #cm

Instance: QBCBodyHeightObservationExample
InstanceOf: QBCQuantityDataItemObservation
Usage: #example
Title: "合成的 QBC 身高"
Description: "示範以 UCUM cm 表示 P03；QBC 主表格式為整數至多 3 位、小數至多 2 位。"
* id = "qbc-body-height-example"
* status = #final
* code = $QBCFieldCS#P03 "身高"
* subject = Reference(QBCPatientExample)
* effectiveDateTime = "2026-01-01T00:00:00Z"
* performer.display = "Synthetic clinical reviewer"
* valueQuantity.value = 158.5
* valueQuantity.unit = "cm"
* valueQuantity.system = "http://unitsofmeasure.org"
* valueQuantity.code = #cm

Instance: QBCFollowUpDateObservationExample
InstanceOf: QBCDateDataItemObservation
Usage: #example
Title: "合成的 QBC 追蹤年度"
Description: "示範 T01 追蹤年度；主表格式同為固定 8 碼 YYYYMMDD，每曆年最多一筆。"
* id = "qbc-follow-up-date-example"
* status = #final
* code = $QBCFieldCS#T01 "追蹤年度"
* subject = Reference(QBCPatientExample)
* effectiveDateTime = "2026-01-01T00:00:00Z"
* performer.display = "Synthetic clinical reviewer"
* valueDateTime = "2026-01-01T00:00:00Z"

Instance: QBCRawDataItemObservationExample
InstanceOf: QBCRawDataItemObservation
Usage: #example
Title: "合成的 QBC 原始值欄位"
Description: "示範無法安全轉型時，以 valueString 保存可逆原始值：D003 組織學分類代碼。"
* id = "qbc-raw-data-item-example"
* status = #final
* code = $QBCFieldCS#D003 "（新輔助）組織學分類"
* subject = Reference(QBCPatientExample)
* effectiveDateTime = "2026-01-01T00:00:00Z"
* performer.display = "Synthetic clinical reviewer"
* valueString = "2"

Instance: QBCProvenanceExample
InstanceOf: QBCProvenance
Usage: #example
Title: "合成的 QBC 來源紀錄"
Description: "示範人工審核後的來源紀錄。"
* id = "qbc-provenance-example"
* target = Reference(QBCStageObservationExample)
* recorded = "2026-01-01T00:00:00Z"
* agent.type.text = "manual"
* agent.who.display = "Synthetic reviewer"
* entity.role = #source
* entity.what.display = "Synthetic source document"

Instance: QBCSubmissionBundleExample
InstanceOf: QBCSubmissionBundle
Usage: #example
Title: "完全合成的 QBC Submission Bundle"
Description: "不含真實病人資料的 collection Bundle。"
* id = "qbc-submission-example"
* identifier.system = $QBCBundleId
* identifier.value = "qbc-submission-example"
* type = #collection
* timestamp = "2026-01-01T00:00:00Z"
* entry[patient].fullUrl = "https://ericeric777777.github.io/qbc-ig/Patient/qbc-patient-example"
* entry[patient].resource = QBCPatientExample
* entry[observation].fullUrl = "https://ericeric777777.github.io/qbc-ig/Observation/qbc-stage-example"
* entry[observation].resource = QBCStageObservationExample
* entry[provenance].fullUrl = "https://ericeric777777.github.io/qbc-ig/Provenance/qbc-provenance-example"
* entry[provenance].resource = QBCProvenanceExample
