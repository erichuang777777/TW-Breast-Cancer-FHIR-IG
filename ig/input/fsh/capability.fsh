Instance: BreastCancerCommunityCapabilityStatement
InstanceOf: CapabilityStatement
Usage: #definition
Title: "Breast Cancer Community Draft Capability Statement"
Description: "Requirements-level capability statement listing the resource families expected across breast-cancer task modules. Individual tasks define their own required operations and exchange bundles."
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/CapabilityStatement/BreastCancerCommunityCapabilityStatement"
* version = "1.0.0-preview.1"
* name = "BreastCancerCommunityCapabilityStatement"
* status = #draft
* experimental = true
* date = "2026-08-14"
* publisher = "Breast Cancer FHIR Community Draft"
* kind = #requirements
* fhirVersion = #4.0.1
* format[+] = #json
* format[+] = #xml
* rest.mode = #server
* rest.documentation = "A conforming implementation supports only the resources required by its declared task modules; this community capability statement is not an authorization to claim every task."
* rest.resource[+].type = #Patient
* rest.resource[=].supportedProfile = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-patient"
* rest.resource[+].type = #Condition
* rest.resource[=].supportedProfile = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-primary-condition"
* rest.resource[+].type = #Observation
* rest.resource[=].supportedProfile[+] = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-source-observation"
* rest.resource[=].supportedProfile[+] = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-stage-group-observation"
* rest.resource[=].supportedProfile[+] = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-tumor-marker-observation"
* rest.resource[+].type = #Procedure
* rest.resource[=].supportedProfile = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-treatment-procedure"
* rest.resource[+].type = #MedicationRequest
* rest.resource[=].supportedProfile = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-medication-request"
* rest.resource[+].type = #MedicationAdministration
* rest.resource[=].supportedProfile = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-medication-administration"
* rest.resource[+].type = #EpisodeOfCare
* rest.resource[=].supportedProfile = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-episode-of-care"
* rest.resource[+].type = #DiagnosticReport
* rest.resource[=].supportedProfile[+] = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-pathology-report"
* rest.resource[=].supportedProfile[+] = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-laboratory-report"
* rest.resource[=].supportedProfile[+] = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-ultrasound-report"
* rest.resource[+].type = #Specimen
* rest.resource[=].supportedProfile = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-pathology-specimen"
* rest.resource[+].type = #CarePlan
* rest.resource[=].supportedProfile = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/cancer-care-plan-task-care-plan"
* rest.resource[+].type = #QuestionnaireResponse
* rest.resource[=].supportedProfile = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/cancer-care-plan-task-questionnaire-response"
* rest.resource[+].type = #Task
* rest.resource[=].supportedProfile[+] = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-case-management-task"
* rest.resource[=].supportedProfile[+] = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/tcr-registry-abstraction-task"
* rest.resource[+].type = #Bundle
* rest.resource[=].supportedProfile[+] = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/breast-cancer-common-facts-bundle"
* rest.resource[=].supportedProfile[+] = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/cancer-care-plan-task-bundle"
* rest.resource[=].supportedProfile[+] = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/StructureDefinition/qbc-submission-bundle"
