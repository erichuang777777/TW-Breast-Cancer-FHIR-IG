// Synthetic conformance examples used by the publication QA gate.
// These resources test structure only. They are not source-derived clinical
// facts, validated registry submissions, or evidence that a Measure is correct.

Alias: $TCRFieldCS = https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/tcr-field
Alias: $TCRSexCS = https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CodeSystem/tcr-breast-sex
Alias: $TCRIllegalCode = https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/tcr-illegal-code
Alias: $ActReason = http://terminology.hl7.org/CodeSystem/v3-ActReason

Instance: TCRDataItemObservationExample
InstanceOf: TCRDataItemObservation
Usage: #example
Title: "Synthetic TCR Data Item Observation"
Description: "Structure-only example of the common TCR data-item profile; it is not a registry submission."
* id = "tcr-data-item-observation-example"
* meta.security = $ActReason#HTEST "test health data"
* status = #final
* code = $TCRFieldCS#PK
* subject = Reference(BreastCancerPatientExample)
* valueString = "SYNTHETIC-REGISTRY-KEY"

Instance: TCRRawDataItemObservationExample
InstanceOf: TCRRawDataItemObservation
Usage: #example
Title: "Synthetic TCR Raw Data Item Observation"
Description: "Structure-only example showing reversible preservation of an unstandardized source value."
* id = "tcr-raw-data-item-observation-example"
* meta.security = $ActReason#HTEST "test health data"
* status = #final
* code = $TCRFieldCS#DXDATE
* subject = Reference(BreastCancerPatientExample)
* valueString = "2026/01/01"

Instance: TCRCodedDataItemObservationExample
InstanceOf: TCRCodedDataItemObservation
Usage: #example
Title: "Synthetic TCR Coded Data Item Observation"
Description: "Structure-only example whose value uses an existing local TCR code table; it is not clinically asserted."
* id = "tcr-coded-data-item-observation-example"
* meta.security = $ActReason#HTEST "test health data"
* status = #final
* code = $TCRFieldCS#SEX
* subject = Reference(BreastCancerPatientExample)
* valueCodeableConcept = $TCRSexCS#2

Instance: TCRIllegalCodeNegativeExample
InstanceOf: QuestionnaireResponse
Usage: #example
Title: "Synthetic TCR Illegal Code Negative Test"
Description: "Deliberate negative test: the raw answer is preserved as text and marked for review instead of being represented as a nonexistent Coding."
* id = "tcr-illegal-code-negative-example"
* meta.security = $ActReason#HTEST "test health data"
* status = #in-progress
* subject = Reference(BreastCancerPatientExample)
* item.linkId = "demographics"
* item.item.linkId = "SEX"
* item.item.answer.valueString = "NOT-A-LEGAL-CODE"
* item.item.answer.extension[0].url = $TCRIllegalCode
* item.item.answer.extension[0].valueString = "NOT-A-LEGAL-CODE is outside the verified code table; review required"

Instance: BreastCancerCaseManagementReportExample
InstanceOf: BreastCancerCaseManagementReport
Usage: #example
Title: "Synthetic Breast Cancer Case Management MeasureReport"
Description: "Structure-only summary report with synthetic counts. It does not demonstrate clinical correctness or reproduce a hospital report."
* id = "breast-cancer-case-management-report-example"
* meta.security = $ActReason#HTEST "test health data"
* status = #complete
* type = #summary
* measure = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qi-01"
* date = "2026-04-01T00:00:00+08:00"
* reporter.display = "Synthetic case manager"
* period.start = "2026-01-01T00:00:00+08:00"
* period.end = "2026-03-31T23:59:59+08:00"
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].count = 10
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].count = 10
* group.population[2].code = $MeasurePopulation#denominator-exclusion
* group.population[2].count = 2
* group.population[3].code = $MeasurePopulation#numerator
* group.population[3].count = 7
* group.measureScore.value = 0.875
