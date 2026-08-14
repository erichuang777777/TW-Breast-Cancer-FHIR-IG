CodeSystem: BreastCancerInformationCategoryCodeSystem
Id: breast-cancer-information-category
Title: "Breast Cancer Information Category Codes - Community Draft"
Description: "Local metadata codes used to classify reusable breast-cancer information areas. These are architecture labels, not substitutes for clinical terminologies."
* ^status = #draft
* ^experimental = true
* ^caseSensitive = true
* ^content = #complete
* #diagnosis "Diagnosis"
* #staging "Staging"
* #pathology "Pathology"
* #biomarker "Biomarker"
* #genomics "Genomics"
* #treatment "Treatment"
* #follow-up "Follow-up"
* #outcome "Outcome"

ValueSet: BreastCancerInformationCategoryValueSet
Id: breast-cancer-information-category
Title: "Breast Cancer Information Category Value Set - Community Draft"
Description: "All architecture categories defined by this community draft."
* ^status = #draft
* ^experimental = true
* include codes from system BreastCancerInformationCategoryCodeSystem
