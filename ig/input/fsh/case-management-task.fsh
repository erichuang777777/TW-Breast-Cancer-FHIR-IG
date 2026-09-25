Profile: BreastCancerCaseManagementTask
Parent: Task
Id: breast-cancer-case-management-task
Title: "乳癌個管品管與季報 Task - Community Draft"
Description: "承載品管與季報無法由臨床資源推導的個管行政事實。每一個 input slice 皆以本 IG 的 Task input type 識別並綁定個管團隊自有值域；不得用本 Task 覆寫原始臨床事實。"
* ^status = #draft
* ^experimental = true
* for 1..1
* for only Reference(BreastCancerPatient)
* focus 0..1
* focus only Reference(BreastCancerPrimaryCondition or BreastCancerEpisodeOfCare)
* owner 1..1
* authoredOn 1..1
* input 1..*
* input ^slicing.discriminator.type = #pattern
* input ^slicing.discriminator.path = "type"
* input ^slicing.rules = #open
* input contains
    caseEntryCategory 0..1 and
    caseStatus 0..1 and
    closureReason 0..1 and
    registryCaseClass 0..1 and
    retentionDisposition 0..1 and
    curativeTreatmentDisposition 0..1 and
    treatmentCompletion 0..1
* input[caseEntryCategory].type = CMTaskInputTypeCS#case-entry-category
* input[caseEntryCategory].value[x] only CodeableConcept
* input[caseEntryCategory].valueCodeableConcept from CMCaseEntryCategoryVS (required)
* input[caseStatus].type = CMTaskInputTypeCS#case-status
* input[caseStatus].value[x] only CodeableConcept
* input[caseStatus].valueCodeableConcept from CMCaseStatusVS (required)
* input[closureReason].type = CMTaskInputTypeCS#closure-reason
* input[closureReason].value[x] only CodeableConcept
* input[closureReason].valueCodeableConcept from CMClosureReasonVS (required)
* input[registryCaseClass].type = CMTaskInputTypeCS#registry-case-class
* input[registryCaseClass].value[x] only CodeableConcept
* input[registryCaseClass].valueCodeableConcept from CMRegistryCaseClassVS (required)
* input[retentionDisposition].type = CMTaskInputTypeCS#retention-disposition
* input[retentionDisposition].value[x] only CodeableConcept
* input[retentionDisposition].valueCodeableConcept from CMRetentionDispositionVS (required)
* input[curativeTreatmentDisposition].type = CMTaskInputTypeCS#curative-treatment-disposition
* input[curativeTreatmentDisposition].value[x] only CodeableConcept
* input[curativeTreatmentDisposition].valueCodeableConcept from CMCurativeTreatmentDispositionVS (required)
* input[treatmentCompletion].type = CMTaskInputTypeCS#treatment-completion
* input[treatmentCompletion].value[x] only CodeableConcept
* input[treatmentCompletion].valueCodeableConcept from CMTreatmentCompletionVS (required)

Instance: BreastCancerCaseManagementTaskExample
InstanceOf: BreastCancerCaseManagementTask
Usage: #example
Title: "Synthetic Breast Cancer Case Management Task"
Description: "完全合成的個管 Task 範例，示範收案身份、狀態、結案原因與 Class 分類；不代表真實病人或已核准的院內作業決策。"
* id = "breast-cancer-case-management-task-example"
* status = #completed
* intent = #order
* for = Reference(BreastCancerPatientExample)
* focus = Reference(BreastCancerPrimaryConditionExample)
* owner.display = "Synthetic case manager"
* authoredOn = "2026-06-30T12:00:00+08:00"
* input[caseEntryCategory].valueCodeableConcept = CMCaseEntryCategoryCS#new-diagnosis
* input[caseStatus].valueCodeableConcept = CMCaseStatusCS#closed
* input[closureReason].valueCodeableConcept = CMClosureReasonCS#refused-return
* input[registryCaseClass].valueCodeableConcept = CMRegistryCaseClassCS#class-1
