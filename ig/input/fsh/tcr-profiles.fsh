// 癌症登記模組：與 QBC 模組平行的第二個申報目標。
// Observation profile 沿用 QBC 的分層方式（基礎 / raw / 日期 / 整數），
// 讓兩個模組的中介資料形狀一致。

Profile: TCRDataItemObservation
Parent: Observation
Id: tcr-data-item-observation
Title: "TCR Data Item Observation Base"
Description: "癌症登記長表欄位 Observation 的共同基礎限制。"
* ^status = #draft
* ^experimental = true
* status = #final (exactly)
* status MS
* code 1..1
* code from TCRFieldValueSet (required)
* code MS
* subject 1..1
* subject MS
* value[x] 1..1
* value[x] MS

Profile: TCRRawDataItemObservation
Parent: TCRDataItemObservation
Id: tcr-raw-data-item-observation
Title: "TCR Raw Data Item Observation"
Description: "以 valueString 保存原始癌登值的可逆中介層；不表示已完成臨床術語標準化。"
* ^status = #draft
* ^experimental = true
* value[x] only string

Profile: TCRCodedDataItemObservation
Parent: TCRDataItemObservation
Id: tcr-coded-data-item-observation
Title: "TCR Coded Data Item Observation"
Description: "值域已由本 IG 的癌登 CodeSystem 驗證的欄位。"
* ^status = #draft
* ^experimental = true
* value[x] only CodeableConcept

ValueSet: TCRFieldValueSet
Id: tcr-field-vs
Title: "TCR Longform Field Codes"
Description: "癌症登記長表欄位代碼值集。"
* ^status = #draft
* ^experimental = true
* include codes from system TCRFieldCodeSystem

Profile: TCRRegistryAbstractionTask
Parent: Task
Id: tcr-registry-abstraction-task
Title: "癌症登記摘錄任務"
Description: "為某一顆原發乳癌完成癌症登記長表摘錄：input 是來源文件，output 是填好的 QuestionnaireResponse 與產生的申報列。與 QBC 申報並列為本 IG 的另一個 task。"
* ^status = #draft
* ^experimental = true
* focus 1..1
* focus only Reference(Condition)
* focus ^short = "被申報的原發癌症"
* for 1..1
* for only Reference(Patient)
* input 1..*
* input ^short = "來源文件：病理報告、門診／手術／放療／化療紀錄"
* output 0..*
* output ^short = "填好的 QuestionnaireResponse 與產生的癌登申報列"
