CodeSystem: QBCWorkflowCodeSystem
Id: qbc-workflow
Title: "QBC Workflow Codes"
Description: "Field-qualified codes used to preserve QBC workflow meanings without confusing identical raw digits from different fields."
* ^status = #draft
* ^experimental = true
* ^caseSensitive = true
* ^content = #complete
* #P02-0 "Male"
* #P02-1 "Female"
* #P02-2 "Other"
* #P02-3 "Unknown"
* #LATERALITY-L "Left"
* #LATERALITY-R "Right"
* #enrollment-1 "New diagnosis - direct curative surgery"
* #enrollment-2 "New diagnosis - neoadjuvant therapy"
* #enrollment-3 "First recurrence"
* #case-class-1 "Diagnosed and treated at this institution"
* #case-class-2 "Diagnosed elsewhere and treated at this institution"
* #case-class-3 "Recurrence case"
* #facility-1 "This institution"
* #facility-2 "Other institution"
* #treatment-1 "Curative or recurrence surgery"
* #treatment-2 "Chemotherapy"
* #treatment-3 "Radiotherapy"
* #treatment-4 "Immunotherapy"
* #treatment-5 "Targeted therapy"
* #treatment-6 "Endocrine therapy"
* #treatment-7 "Other therapy"
* #treatment-status-1 "Treatment completed"
* #treatment-status-2 "Continuing treatment at this institution"
* #treatment-status-3 "Transferred for treatment"
* #treatment-status-4 "Treatment interrupted"
* #treatment-status-5 "Died during treatment"
* #treatment-status-6 "Recurrence during treatment"
* #treatment-status-X "Unknown"
* #followup-status-1 "Followed here without recurrence or metastasis"
* #followup-status-2 "Transferred for follow-up"
* #followup-status-3 "Follow-up interrupted"
* #followup-status-4 "Died during follow-up"
* #followup-status-5 "Recurrence during follow-up"
* #followup-status-X "Unknown"

ValueSet: QBCEnrollmentTypeValueSet
Id: qbc-enrollment-type
Title: "QBC Enrollment Type Value Set"
Description: "Allowed field-qualified codes for QBC DIAG_TYPE."
* ^status = #draft
* ^experimental = true
* QBCWorkflowCodeSystem#enrollment-1
* QBCWorkflowCodeSystem#enrollment-2
* QBCWorkflowCodeSystem#enrollment-3

ValueSet: QBCGenderValueSet
Id: qbc-gender
Title: "QBC Gender Value Set"
Description: "Allowed field-qualified codes for QBC P02."
* ^status = #draft
* ^experimental = true
* QBCWorkflowCodeSystem#P02-0
* QBCWorkflowCodeSystem#P02-1
* QBCWorkflowCodeSystem#P02-2
* QBCWorkflowCodeSystem#P02-3

ValueSet: QBCLateralityValueSet
Id: qbc-laterality
Title: "QBC Laterality Value Set"
Description: "Allowed field-qualified codes for QBC LATERALITY."
* ^status = #draft
* ^experimental = true
* QBCWorkflowCodeSystem#LATERALITY-L
* QBCWorkflowCodeSystem#LATERALITY-R

ValueSet: QBCLateralitySNOMEDValueSet
Id: qbc-laterality-snomed
Title: "QBC Laterality SNOMED CT Target Value Set"
Description: "SNOMED CT qualifier values used as targets of the QBC laterality ConceptMap."
* ^status = #draft
* ^experimental = true
* http://snomed.info/sct#7771000 "Left"
* http://snomed.info/sct#24028007 "Right"

ValueSet: QBCCaseClassValueSet
Id: qbc-case-class
Title: "QBC Case Class Value Set"
Description: "Allowed field-qualified codes for QBC P08."
* ^status = #draft
* ^experimental = true
* QBCWorkflowCodeSystem#case-class-1
* QBCWorkflowCodeSystem#case-class-2
* QBCWorkflowCodeSystem#case-class-3

ValueSet: QBCFacilityClassValueSet
Id: qbc-facility-class
Title: "QBC Facility Class Value Set"
Description: "Allowed field-qualified codes for same-institution versus other-institution QBC fields."
* ^status = #draft
* ^experimental = true
* QBCWorkflowCodeSystem#facility-1
* QBCWorkflowCodeSystem#facility-2

ValueSet: QBCTreatmentTypeValueSet
Id: qbc-treatment-type
Title: "QBC Treatment Type Value Set"
Description: "Allowed field-qualified codes for QBC TM02."
* ^status = #draft
* ^experimental = true
* QBCWorkflowCodeSystem#treatment-1
* QBCWorkflowCodeSystem#treatment-2
* QBCWorkflowCodeSystem#treatment-3
* QBCWorkflowCodeSystem#treatment-4
* QBCWorkflowCodeSystem#treatment-5
* QBCWorkflowCodeSystem#treatment-6
* QBCWorkflowCodeSystem#treatment-7

ValueSet: QBCTreatmentStatusValueSet
Id: qbc-treatment-status
Title: "QBC Treatment Status Value Set"
Description: "Allowed field-qualified codes for QBC T02."
* ^status = #draft
* ^experimental = true
* QBCWorkflowCodeSystem#treatment-status-1
* QBCWorkflowCodeSystem#treatment-status-2
* QBCWorkflowCodeSystem#treatment-status-3
* QBCWorkflowCodeSystem#treatment-status-4
* QBCWorkflowCodeSystem#treatment-status-5
* QBCWorkflowCodeSystem#treatment-status-6
* QBCWorkflowCodeSystem#treatment-status-X

ValueSet: QBCFollowUpStatusValueSet
Id: qbc-followup-status
Title: "QBC Follow-up Status Value Set"
Description: "Allowed field-qualified codes for QBC T03."
* ^status = #draft
* ^experimental = true
* QBCWorkflowCodeSystem#followup-status-1
* QBCWorkflowCodeSystem#followup-status-2
* QBCWorkflowCodeSystem#followup-status-3
* QBCWorkflowCodeSystem#followup-status-4
* QBCWorkflowCodeSystem#followup-status-5
* QBCWorkflowCodeSystem#followup-status-X

Extension: QBCEnrollmentType
Id: qbc-enrollment-type
Title: "QBC Enrollment Type"
Description: "Preserves DIAG_TYPE independently from clinical disease status."
Context: EpisodeOfCare
* ^status = #draft
* ^experimental = true
* value[x] only CodeableConcept
* valueCodeableConcept 1..1
* valueCodeableConcept from QBCEnrollmentTypeValueSet (required)

Extension: QBCCaseClass
Id: qbc-case-class
Title: "QBC Case Class"
Description: "Preserves P08 independently from DIAG_TYPE."
Context: EpisodeOfCare
* ^status = #draft
* ^experimental = true
* value[x] only CodeableConcept
* valueCodeableConcept 1..1
* valueCodeableConcept from QBCCaseClassValueSet (required)

Extension: QBCDiagnosisFacilityClass
Id: qbc-diagnosis-facility-class
Title: "QBC Diagnosis Facility Class"
Description: "Preserves whether diagnosis occurred at this or another institution when the actual Organization is unavailable."
Context: Encounter
* ^status = #draft
* ^experimental = true
* value[x] only CodeableConcept
* valueCodeableConcept 1..1
* valueCodeableConcept from QBCFacilityClassValueSet (required)

Extension: QBCTreatmentSequence
Id: qbc-treatment-sequence
Title: "QBC Treatment Sequence"
Description: "Preserves the positive integer ordering required by TM01."
Context: Procedure, MedicationAdministration
* ^status = #draft
* ^experimental = true
* value[x] only positiveInt
* valuePositiveInt 1..1

Extension: QBCTreatmentType
Id: qbc-treatment-type
Title: "QBC Treatment Type"
Description: "Preserves the QBC treatment class while detailed FHIR resources carry the clinical intervention."
Context: Procedure, MedicationAdministration
* ^status = #draft
* ^experimental = true
* value[x] only CodeableConcept
* valueCodeableConcept 1..1
* valueCodeableConcept from QBCTreatmentTypeValueSet (required)

Extension: QBCTreatmentFacilityClass
Id: qbc-treatment-facility-class
Title: "QBC Treatment Facility Class"
Description: "Preserves whether treatment occurred at this or another institution."
Context: Procedure, MedicationAdministration
* ^status = #draft
* ^experimental = true
* value[x] only CodeableConcept
* valueCodeableConcept 1..1
* valueCodeableConcept from QBCFacilityClassValueSet (required)

Extension: QBCTreatmentStatus
Id: qbc-treatment-status
Title: "QBC Treatment Status"
Description: "Preserves T02 without overloading EpisodeOfCare.status."
Context: EpisodeOfCare
* ^status = #draft
* ^experimental = true
* value[x] only CodeableConcept
* valueCodeableConcept 1..1
* valueCodeableConcept from QBCTreatmentStatusValueSet (required)

Extension: QBCFollowUpStatus
Id: qbc-followup-status
Title: "QBC Follow-up Status"
Description: "Preserves T03 without overloading EpisodeOfCare.status."
Context: EpisodeOfCare
* ^status = #draft
* ^experimental = true
* value[x] only CodeableConcept
* valueCodeableConcept 1..1
* valueCodeableConcept from QBCFollowUpStatusValueSet (required)

Extension: QBCTransferDate
Id: qbc-transfer-date
Title: "QBC Transfer Date"
Description: "Preserves T04 separately from the episode end or closure date."
Context: EpisodeOfCare
* ^status = #draft
* ^experimental = true
* value[x] only date
* valueDate 1..1

Instance: QBCGenderToFHIRAdministrativeGender
InstanceOf: ConceptMap
Usage: #definition
Title: "QBC Gender to FHIR Administrative Gender"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ConceptMap/QBCGenderToFHIRAdministrativeGender"
* version = "1.0.0-preview.1"
* name = "QBCGenderToFHIRAdministrativeGender"
* description = "Maps the four QBC P02 values to FHIR AdministrativeGender without inference."
* status = #draft
* experimental = true
* sourceUri = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/qbc-gender"
* targetUri = "http://hl7.org/fhir/ValueSet/administrative-gender"
* group.source = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/qbc-workflow"
* group.target = "http://hl7.org/fhir/administrative-gender"
* group.element[+].code = #P02-0
* group.element[=].target.code = #male
* group.element[=].target.display = "Male"
* group.element[=].target.equivalence = #equivalent
* group.element[+].code = #P02-1
* group.element[=].target.code = #female
* group.element[=].target.display = "Female"
* group.element[=].target.equivalence = #equivalent
* group.element[+].code = #P02-2
* group.element[=].target.code = #other
* group.element[=].target.display = "Other"
* group.element[=].target.equivalence = #equivalent
* group.element[+].code = #P02-3
* group.element[=].target.code = #unknown
* group.element[=].target.display = "Unknown"
* group.element[=].target.equivalence = #equivalent

Instance: QBCLateralityToSNOMEDCT
InstanceOf: ConceptMap
Usage: #definition
Title: "QBC Laterality to SNOMED CT"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ConceptMap/QBCLateralityToSNOMEDCT"
* version = "1.0.0-preview.1"
* name = "QBCLateralityToSNOMEDCT"
* description = "Maps QBC L and R laterality codes to SNOMED CT left and right qualifier values."
* status = #draft
* experimental = true
* sourceUri = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/qbc-laterality"
* targetUri = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/ValueSet/qbc-laterality-snomed"
* group.source = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/qbc-workflow"
* group.target = "http://snomed.info/sct"
* group.element[+].code = #LATERALITY-L
* group.element[=].target.code = #7771000
* group.element[=].target.display = "Left"
* group.element[=].target.equivalence = #equivalent
* group.element[+].code = #LATERALITY-R
* group.element[=].target.code = #24028007
* group.element[=].target.display = "Right"
* group.element[=].target.equivalence = #equivalent
