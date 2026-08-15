// Breast-cancer community layer.
// These draft profiles are reusable across task modules. They derive from TW Core
// where a stable structural parent is available and do not claim mCODE conformance.

Profile: BreastCancerPatient
Parent: $TWCorePatient
Id: breast-cancer-patient
Title: "Breast Cancer Patient - Community Draft"
Description: "Reusable patient profile for breast-cancer task modules in the Taiwan context. This profile is structurally based on TW Core Patient; mCODE and ICHOM are semantic references only."
* ^status = #draft
* ^experimental = true
* identifier MS
* name MS
* gender MS
* birthDate MS
* deceased[x] MS

Profile: BreastCancerPrimaryCondition
Parent: Condition
Id: breast-cancer-primary-condition
Title: "Breast Cancer Primary Condition - Community Draft"
Description: "Minimal reusable representation of a primary breast-cancer diagnosis. Detailed morphology, staging and registry rules remain governed by task-specific profiles until the community model is clinically reviewed."
* ^status = #draft
* ^experimental = true
* clinicalStatus MS
* verificationStatus MS
* code 1..1 MS
* subject 1..1 MS
* subject only Reference(BreastCancerPatient)
* bodySite MS
* onset[x] MS
* recordedDate MS

Profile: BreastCancerSourceObservation
Parent: Observation
Id: breast-cancer-source-observation
Title: "Breast Cancer Source Observation - Community Draft"
Description: "Abstract source-evidence observation extracted from pathology, laboratory, imaging or other signed clinical reports. It preserves the report, specimen, performer and effective-time lineage before task-specific projection."
* ^status = #draft
* ^experimental = true
* ^abstract = true
* status MS
* code 1..1 MS
* subject 1..1 MS
* subject only Reference(BreastCancerPatient)
* effective[x] MS
* performer MS
* specimen MS
* derivedFrom MS

Profile: BreastCancerSourceDiagnosticReport
Parent: DiagnosticReport
Id: breast-cancer-source-diagnostic-report
Title: "Breast Cancer Source Diagnostic Report - Community Draft"
Description: "Abstract signed source-report shell for pathology, laboratory and breast ultrasound reports. The report is an evidence container; reusable atomic facts are represented by referenced observations and specimens."
* ^status = #draft
* ^experimental = true
* ^abstract = true
* status MS
* category MS
* code 1..1 MS
* subject 1..1 MS
* subject only Reference(BreastCancerPatient)
* effective[x] MS
* issued MS
* performer MS
* specimen MS
* result MS
* result only Reference(BreastCancerSourceObservation)
* imagingStudy MS
* presentedForm MS

Profile: BreastCancerSourceSpecimen
Parent: Specimen
Id: breast-cancer-source-specimen
Title: "Breast Cancer Source Specimen - Community Draft"
Description: "Abstract specimen lineage used by pathology and laboratory source observations."
* ^status = #draft
* ^experimental = true
* ^abstract = true
* subject 1..1 MS
* subject only Reference(BreastCancerPatient)
* type MS
* collection MS
* receivedTime MS

Profile: BreastCancerPathologySpecimen
Parent: BreastCancerSourceSpecimen
Id: breast-cancer-pathology-specimen
Title: "Breast Cancer Pathology Specimen - Community Draft"
Description: "Concrete specimen profile for breast pathology source reports."
* ^status = #draft
* ^experimental = true

Profile: BreastCancerPathologyReport
Parent: BreastCancerSourceDiagnosticReport
Id: breast-cancer-pathology-report
Title: "Breast Cancer Pathology Report - Community Draft"
Description: "Concrete source-evidence report for breast pathology. Atomic findings are referenced as observations and retain specimen lineage."
* ^status = #draft
* ^experimental = true
* specimen only Reference(BreastCancerPathologySpecimen)

Profile: BreastCancerLaboratoryReport
Parent: BreastCancerSourceDiagnosticReport
Id: breast-cancer-laboratory-report
Title: "Breast Cancer Laboratory Report - Community Draft"
Description: "Concrete source-evidence report for laboratory results used in breast-cancer care."
* ^status = #draft
* ^experimental = true

Profile: BreastCancerUltrasoundReport
Parent: BreastCancerSourceDiagnosticReport
Id: breast-cancer-ultrasound-report
Title: "Breast Ultrasound Report - Community Draft"
Description: "Concrete source-evidence report for breast ultrasound. Imaging lineage uses the standard FHIR ImagingStudy resource; structured findings are referenced observations."
* ^status = #draft
* ^experimental = true

Profile: BreastCancerStageGroupObservation
Parent: BreastCancerSourceObservation
Id: breast-cancer-stage-group-observation
Title: "Breast Cancer Stage Group Observation - Community Draft"
Description: "Reusable stage-group observation shell. The staging system and edition SHALL be preserved in method or supporting provenance; this draft does not reproduce licensed AJCC content."
* ^status = #draft
* ^experimental = true
* status MS
* code 1..1 MS
* subject 1..1 MS
* subject only Reference(BreastCancerPatient)
* focus MS
* focus only Reference(BreastCancerPrimaryCondition)
* effective[x] MS
* value[x] 1..1 MS
* value[x] only CodeableConcept
* method MS

Profile: BreastCancerTumorMarkerObservation
Parent: BreastCancerSourceObservation
Id: breast-cancer-tumor-marker-observation
Title: "Breast Cancer Tumor Marker Observation - Community Draft"
Description: "Reusable shell for ER, PR, HER2, Ki-67, PD-L1 and other breast-cancer marker results. Assay, specimen, scoring method and units are retained when known; task modules must not infer missing assay metadata."
* ^status = #draft
* ^experimental = true
* status MS
* code 1..1 MS
* subject 1..1 MS
* subject only Reference(BreastCancerPatient)
* effective[x] MS
* value[x] 1..1 MS
* value[x] only CodeableConcept or Quantity or Ratio or string
* specimen MS
* method MS
* interpretation MS

Profile: BreastCancerTreatmentProcedure
Parent: Procedure
Id: breast-cancer-treatment-procedure
Title: "Breast Cancer Treatment Procedure - Community Draft"
Description: "Reusable procedure shell for breast-cancer surgery, radiotherapy and other non-medication treatment activities."
* ^status = #draft
* ^experimental = true
* status MS
* code 1..1 MS
* subject 1..1 MS
* subject only Reference(BreastCancerPatient)
* performed[x] MS
* bodySite MS

Profile: BreastCancerMedicationRequest
Parent: MedicationRequest
Id: breast-cancer-medication-request
Title: "Breast Cancer Medication Request - Community Draft"
Description: "Reusable medication-request shell for breast-cancer systemic treatment. Reimbursement and prior-authorization constraints belong to their respective task modules."
* ^status = #draft
* ^experimental = true
* status MS
* intent MS
* medication[x] 1..1 MS
* subject 1..1 MS
* subject only Reference(BreastCancerPatient)
* authoredOn MS
* requester MS

Profile: BreastCancerEpisodeOfCare
Parent: EpisodeOfCare
Id: breast-cancer-episode-of-care
Title: "Breast Cancer Episode of Care - Community Draft"
Description: "Reusable episode shell linking diagnosis, treatment and follow-up task modules without imposing QBC-specific workflow codes."
* ^status = #draft
* ^experimental = true
* status MS
* patient 1..1 MS
* patient only Reference(BreastCancerPatient)
* diagnosis.condition only Reference(BreastCancerPrimaryCondition)
* period MS

Profile: BreastCancerCommonFactsBundle
Parent: Bundle
Id: breast-cancer-common-facts-bundle
Title: "Breast Cancer Common FHIR Facts Bundle - Community Draft"
Description: "Task-neutral collection of reviewed breast-cancer source evidence and reusable clinical facts. Parallel task modules such as Cancer Care Plan and QBC consume this layer independently; no task artifact is the source of another task."
* ^status = #draft
* ^experimental = true
* type = #collection (exactly)
* timestamp 1..1 MS
* entry 2..* MS
* entry.fullUrl 1..1 MS
* entry.resource 1..1 MS
