// Cancer Care Plan task layer.
// These profiles formalize the current care-plan JSON bridge without making
// the derived document the source of truth for atomic clinical facts.

Profile: CancerCarePlanTaskQuestionnaireResponse
Parent: QuestionnaireResponse
Id: cancer-care-plan-task-questionnaire-response
Title: "Cancer Care Plan Source Response - Task Draft"
Description: "Structured preservation of populated fields from the current cancer-care-plan JSON source. QBC-unmapped fields remain here rather than being discarded or forced into QBC semantics."
* ^status = #draft
* ^experimental = true
* status 1..1 MS
* subject 1..1 MS
* subject only Reference(BreastCancerPatient)
* authored 1..1 MS
* item 1..* MS
* item.linkId 1..1 MS
* item.text MS
* item.answer 1..* MS

Profile: CancerCarePlanTaskCarePlan
Parent: CarePlan
Id: cancer-care-plan-task-care-plan
Title: "Cancer Care Plan - Task Draft"
Description: "CarePlan representation produced by the cancer-care-plan task. It links the reusable breast-cancer diagnosis to the complete source response and planned activities."
* ^status = #draft
* ^experimental = true
* status 1..1 MS
* intent 1..1 MS
* category 1..* MS
* subject 1..1 MS
* subject only Reference(BreastCancerPatient)
* addresses 1..* MS
* addresses only Reference(BreastCancerPrimaryCondition)
* created 1..1 MS
* author MS
* supportingInfo 1..* MS
* supportingInfo only Reference(CancerCarePlanTaskQuestionnaireResponse)
* activity MS
* activity.detail.status MS
* activity.detail.description MS

Profile: CancerCarePlanTaskProvenance
Parent: Provenance
Id: cancer-care-plan-task-provenance
Title: "Cancer Care Plan Source Provenance - Task Draft"
Description: "Lineage from the private source JSON to the task CarePlan and source response. Public examples use only a synthetic source digest."
* ^status = #draft
* ^experimental = true
* target 1..* MS
* target only Reference(CancerCarePlanTaskCarePlan or CancerCarePlanTaskQuestionnaireResponse)
* recorded 1..1 MS
* agent 1..* MS
* agent.who 1..1 MS
* entity 1..* MS
* entity.role = #source (exactly)
* entity.what 1..1 MS

Profile: CancerCarePlanTaskBundle
Parent: Bundle
Id: cancer-care-plan-task-bundle
Title: "Cancer Care Plan Exchange Bundle - Task Draft"
Description: "Collection Bundle carrying the patient, diagnosis, complete source response, derived CarePlan and source Provenance. It is parallel to QBC and is not a QBC input."
* ^status = #draft
* ^experimental = true
* identifier 1..1 MS
* type = #collection (exactly)
* timestamp 1..1 MS
* entry 5..* MS
* entry.fullUrl 1..1 MS
* entry.resource 1..1 MS

Instance: CancerCarePlanTaskQuestionnaireResponseExample
InstanceOf: CancerCarePlanTaskQuestionnaireResponse
Usage: #example
Title: "Completely Synthetic Cancer Care Plan Source Response"
Description: "Synthetic populated fields showing both QBC-shared content and care-plan-only content. It represents no real person."
* id = "cancer-care-plan-response-example"
* status = #completed
* subject = Reference(BreastCancerPatientExample)
* authored = "2026-01-15T08:00:00+08:00"
* item[+].linkId = "laterality"
* item[=].text = "Synthetic laterality"
* item[=].answer.valueString = "Left"
* item[+].linkId = "ecog"
* item[=].text = "Synthetic ECOG performance status"
* item[=].answer.valueString = "1"
* item[+].linkId = "family-history"
* item[=].text = "Synthetic family history"
* item[=].answer.valueString = "Synthetic first-degree family history present"
* item[+].linkId = "planned-treatment"
* item[=].text = "Synthetic planned treatment narrative"
* item[=].answer.valueString = "Synthetic multidisciplinary treatment plan"

Instance: CancerCarePlanTaskCarePlanExample
InstanceOf: CancerCarePlanTaskCarePlan
Usage: #example
Title: "Completely Synthetic Cancer Care Plan"
Description: "Synthetic CarePlan derived from the synthetic source response; not for clinical decisions or official submission."
* id = "cancer-care-plan-example"
* status = #active
* intent = #plan
* category.text = "Cancer care plan task"
* subject = Reference(BreastCancerPatientExample)
* addresses = Reference(BreastCancerPrimaryConditionExample)
* created = "2026-01-15T08:00:00+08:00"
* author.display = "Synthetic cancer care planning service"
* supportingInfo = Reference(CancerCarePlanTaskQuestionnaireResponseExample)
* activity.detail.status = #scheduled
* activity.detail.description = "Synthetic multidisciplinary treatment plan"

Instance: CancerCarePlanTaskProvenanceExample
InstanceOf: CancerCarePlanTaskProvenance
Usage: #example
Title: "Completely Synthetic Cancer Care Plan Provenance"
Description: "Synthetic lineage record using a non-production digest and no source filename or patient identifier."
* id = "cancer-care-plan-provenance-example"
* target[+] = Reference(CancerCarePlanTaskCarePlanExample)
* target[+] = Reference(CancerCarePlanTaskQuestionnaireResponseExample)
* recorded = "2026-01-15T08:00:00+08:00"
* agent.who.display = "Synthetic cancer care plan JSON importer"
* entity.role = #source
* entity.what.display = "source-sha256:SYNTHETIC-NOT-A-REAL-DIGEST"

Instance: CancerCarePlanTaskBundleExample
InstanceOf: CancerCarePlanTaskBundle
Usage: #example
Title: "Completely Synthetic Cancer Care Plan Task Bundle"
Description: "Synthetic end-to-end task output preserving care-plan-only fields before QBC projection. It represents no real person."
* id = "cancer-care-plan-task-bundle-example"
* identifier.system = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/sid/cancer-care-plan-bundle-id"
* identifier.value = "cancer-care-plan-task-bundle-example"
* type = #collection
* timestamp = "2026-01-15T08:00:00+08:00"
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Patient/breast-cancer-patient-example"
* entry[=].resource = BreastCancerPatientExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Condition/breast-cancer-primary-condition-example"
* entry[=].resource = BreastCancerPrimaryConditionExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/QuestionnaireResponse/cancer-care-plan-response-example"
* entry[=].resource = CancerCarePlanTaskQuestionnaireResponseExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CarePlan/cancer-care-plan-example"
* entry[=].resource = CancerCarePlanTaskCarePlanExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Provenance/cancer-care-plan-provenance-example"
* entry[=].resource = CancerCarePlanTaskProvenanceExample
