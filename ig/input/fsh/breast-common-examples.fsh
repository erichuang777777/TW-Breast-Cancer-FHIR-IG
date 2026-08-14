Instance: BreastCancerPatientExample
InstanceOf: BreastCancerPatient
Usage: #example
Title: "Synthetic Breast Cancer Patient"
Description: "Completely synthetic example for validating the reusable community layer."
* id = "breast-cancer-patient-example"
* identifier[idCardNumber].type.coding.system = "http://terminology.hl7.org/CodeSystem/v2-0203"
* identifier[idCardNumber].type.coding.code = #NNxxx
* identifier[idCardNumber].system = "http://www.moi.gov.tw"
* identifier[idCardNumber].value = "Z000000000"
* gender = #female
* birthDate = "1970-01-01"

Instance: BreastCancerPrimaryConditionExample
InstanceOf: BreastCancerPrimaryCondition
Usage: #example
Title: "Synthetic Primary Breast Cancer Condition"
Description: "Synthetic diagnosis example; the code demonstrates a breast malignant neoplasm without asserting histology or stage."
* id = "breast-cancer-primary-condition-example"
* clinicalStatus = http://terminology.hl7.org/CodeSystem/condition-clinical#active
* verificationStatus = http://terminology.hl7.org/CodeSystem/condition-ver-status#confirmed
* code = http://snomed.info/sct#254837009 "Malignant neoplasm of breast"
* subject = Reference(BreastCancerPatientExample)
* recordedDate = "2026-01-01"

Instance: BreastCancerPathologySpecimenExample
InstanceOf: BreastCancerPathologySpecimen
Usage: #example
Title: "Synthetic Breast Cancer Pathology Specimen"
Description: "Completely synthetic specimen used only to validate source lineage."
* id = "breast-cancer-pathology-specimen-example"
* status = #available
* type.text = "Synthetic breast tissue specimen"
* subject = Reference(BreastCancerPatientExample)
* collection.collectedDateTime = "2026-01-01T00:00:00+08:00"
* receivedTime = "2026-01-01T01:00:00+08:00"

Instance: BreastCancerStageGroupObservationExample
InstanceOf: BreastCancerStageGroupObservation
Usage: #example
Title: "Synthetic Breast Cancer Stage Group Observation"
Description: "Synthetic structure example. It intentionally does not reproduce licensed staging content."
* id = "breast-cancer-stage-group-example"
* status = #final
* code.text = "Breast cancer stage group"
* subject = Reference(BreastCancerPatientExample)
* focus = Reference(BreastCancerPrimaryConditionExample)
* effectiveDateTime = "2026-01-01T00:00:00+08:00"
* performer.display = "Synthetic multidisciplinary reviewer"
* valueCodeableConcept.text = "Synthetic stage value"
* method.text = "Synthetic staging system and edition"

Instance: BreastCancerTumorMarkerObservationExample
InstanceOf: BreastCancerTumorMarkerObservation
Usage: #example
Title: "Synthetic Breast Cancer Tumor Marker Observation"
Description: "Synthetic marker structure demonstrating preservation of method metadata without assigning an assay-specific code."
* id = "breast-cancer-tumor-marker-example"
* status = #final
* code.text = "Synthetic breast cancer marker"
* subject = Reference(BreastCancerPatientExample)
* effectiveDateTime = "2026-01-01T00:00:00+08:00"
* performer.display = "Synthetic laboratory reviewer"
* valueString = "Synthetic result"
* method.text = "Synthetic assay method"

Instance: BreastCancerTreatmentProcedureExample
InstanceOf: BreastCancerTreatmentProcedure
Usage: #example
Title: "Synthetic Breast Cancer Treatment Procedure"
Description: "Synthetic non-medication treatment example."
* id = "breast-cancer-treatment-procedure-example"
* status = #completed
* code.text = "Synthetic breast cancer treatment procedure"
* subject = Reference(BreastCancerPatientExample)
* performedDateTime = "2026-01-15T00:00:00+08:00"

Instance: BreastCancerMedicationRequestExample
InstanceOf: BreastCancerMedicationRequest
Usage: #example
Title: "Synthetic Breast Cancer Medication Request"
Description: "Synthetic systemic-treatment request with no real drug, prescriber or patient data."
* id = "breast-cancer-medication-request-example"
* status = #active
* intent = #order
* medicationCodeableConcept.text = "Synthetic antineoplastic medication"
* subject = Reference(BreastCancerPatientExample)
* authoredOn = "2026-01-10"
* requester.display = "Synthetic prescriber"

Instance: BreastCancerEpisodeOfCareExample
InstanceOf: BreastCancerEpisodeOfCare
Usage: #example
Title: "Synthetic Breast Cancer Episode of Care"
Description: "Synthetic episode linking the reusable patient and primary-condition examples."
* id = "breast-cancer-episode-example"
* status = #active
* patient = Reference(BreastCancerPatientExample)
* diagnosis.condition = Reference(BreastCancerPrimaryConditionExample)
* period.start = "2026-01-01T00:00:00+08:00"

Instance: BreastCancerPathologyReportExample
InstanceOf: BreastCancerPathologyReport
Usage: #example
Title: "Synthetic Breast Cancer Pathology Report"
Description: "Synthetic signed-report structure; it contains no real patient or pathology data."
* id = "breast-cancer-pathology-report-example"
* status = #final
* code.text = "Synthetic breast pathology report"
* subject = Reference(BreastCancerPatientExample)
* effectiveDateTime = "2026-01-01T00:00:00+08:00"
* issued = "2026-01-01T02:00:00+08:00"
* performer.display = "Synthetic pathology service"
* specimen = Reference(BreastCancerPathologySpecimenExample)
* result = Reference(BreastCancerTumorMarkerObservationExample)

Instance: BreastCancerLaboratoryReportExample
InstanceOf: BreastCancerLaboratoryReport
Usage: #example
Title: "Synthetic Breast Cancer Laboratory Report"
Description: "Synthetic laboratory report structure with no real result data."
* id = "breast-cancer-laboratory-report-example"
* status = #final
* code.text = "Synthetic laboratory report"
* subject = Reference(BreastCancerPatientExample)
* effectiveDateTime = "2026-01-02T00:00:00+08:00"
* issued = "2026-01-02T01:00:00+08:00"
* performer.display = "Synthetic laboratory service"
* result = Reference(BreastCancerTumorMarkerObservationExample)

Instance: BreastCancerUltrasoundReportExample
InstanceOf: BreastCancerUltrasoundReport
Usage: #example
Title: "Synthetic Breast Ultrasound Report"
Description: "Synthetic ultrasound report structure; a future source adapter may link a standard FHIR ImagingStudy when available."
* id = "breast-cancer-ultrasound-report-example"
* status = #final
* code.text = "Synthetic breast ultrasound report"
* subject = Reference(BreastCancerPatientExample)
* effectiveDateTime = "2026-01-03T00:00:00+08:00"
* issued = "2026-01-03T01:00:00+08:00"
* performer.display = "Synthetic imaging service"

Instance: BreastCancerSyntheticScenarioBundleExample
InstanceOf: Bundle
Usage: #example
Title: "Completely Synthetic Breast Cancer Scenario Bundle"
Description: "End-to-end synthetic scenario linking atomic source reports, reusable breast cancer facts, and treatment records. It represents no real person and is not for clinical decisions or official submission."
* id = "breast-cancer-synthetic-scenario"
* type = #collection
* timestamp = "2026-01-15T00:00:00+08:00"
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Patient/breast-cancer-patient-example"
* entry[=].resource = BreastCancerPatientExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Condition/breast-cancer-primary-condition-example"
* entry[=].resource = BreastCancerPrimaryConditionExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Specimen/breast-cancer-pathology-specimen-example"
* entry[=].resource = BreastCancerPathologySpecimenExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Observation/breast-cancer-tumor-marker-example"
* entry[=].resource = BreastCancerTumorMarkerObservationExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Observation/breast-cancer-stage-group-example"
* entry[=].resource = BreastCancerStageGroupObservationExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/DiagnosticReport/breast-cancer-pathology-report-example"
* entry[=].resource = BreastCancerPathologyReportExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/DiagnosticReport/breast-cancer-laboratory-report-example"
* entry[=].resource = BreastCancerLaboratoryReportExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/DiagnosticReport/breast-cancer-ultrasound-report-example"
* entry[=].resource = BreastCancerUltrasoundReportExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Procedure/breast-cancer-treatment-procedure-example"
* entry[=].resource = BreastCancerTreatmentProcedureExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/MedicationRequest/breast-cancer-medication-request-example"
* entry[=].resource = BreastCancerMedicationRequestExample
* entry[+].fullUrl = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/EpisodeOfCare/breast-cancer-episode-example"
* entry[=].resource = BreastCancerEpisodeOfCareExample
