# 癌症診療計畫書欄位盤點／Cancer Care Plan Field Inventory

> 本表只含表單控制項 metadata，不含個案值、病歷號、報告文字、來源雜湊或其他 PHI。

- Catalog version: `1.0.0-preview.1`
- Unique controls: **223**
- Shared with QBC: **25**
- Care-plan-only: **195**
- Derived: **3**

目前所有有值欄位都可無損保存在 QuestionnaireResponse；只有完成語意審查的欄位，才會逐步提升為共用 Condition、Observation、DiagnosticReport、Procedure 或 MedicationRequest。

| ID | Section | Control key | Type | Ownership | QBC target | Candidate FHIR path | Review |
|---|---|---|---|---|---|---|---|
| CCP-001 | basic | `cbAJCC` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-002 | basic | `cbChild` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-003 | basic | `cbUnderStagingAuto` | checkbox | derived | — | `QuestionnaireResponse.item / Provenance.entity` | pending-algorithm-review |
| CCP-004 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-005 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-006 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-007 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-008 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-009 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-010 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-011 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-012 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-013 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-014 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-015 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-016 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-017 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-018 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-019 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-020 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-021 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-022 | basic | `cblCDGeneral` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-023 | basic | `cblCMutations` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-024 | basic | `cblCMutations` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-025 | basic | `cblCMutations` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-026 | basic | `cblCMutations` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-027 | basic | `cblCMutations` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-028 | basic | `cblCMutations` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-029 | basic | `cblCMutations` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-030 | basic | `cblLCH31` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-031 | basic | `cblLCH31` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-032 | basic | `cblLCH31` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-033 | basic | `cblLCH32` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-034 | basic | `cblLCH32` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-035 | basic | `cblLCH32` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-036 | basic | `cblLCH32` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-037 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-038 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-039 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-040 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-041 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-042 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-043 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-044 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-045 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-046 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-047 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-048 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-049 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-050 | basic | `cblMetastasis` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-051 | basic | `cblMutations` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-052 | basic | `cblMutations` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-053 | basic | `cblMutations` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-054 | basic | `cblMutations` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-055 | basic | `ckbBinet` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-056 | basic | `ckbDurie` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-057 | basic | `ckbIss` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-058 | basic | `ckbRai` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-059 | basic | `ckbResectability` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-060 | basic | `ckbYPTNM1` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-061 | basic | `ddlBCLC` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-062 | basic | `ddlBinet` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-063 | basic | `ddlCFAB` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-064 | basic | `ddlClinicMGeneral` | select | shared | D007 | `Observation.component.valueCodeableConcept` | implemented-partial |
| CCP-065 | basic | `ddlClinicNGeneral` | select | shared | D006 | `Observation.component.valueCodeableConcept` | implemented-partial |
| CCP-066 | basic | `ddlClinicTGeneral` | select | shared | D005 | `Observation.component.valueCodeableConcept` | implemented-partial |
| CCP-067 | basic | `ddlDiagnosis` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-068 | basic | `ddlDurie` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-069 | basic | `ddlFAB` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-070 | basic | `ddlFIGO` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-071 | basic | `ddlGrade` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-072 | basic | `ddlHistology` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-073 | basic | `ddlIss` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-074 | basic | `ddlLymphomaB` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-075 | basic | `ddlLymphomaM` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-076 | basic | `ddlLymphomaN` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-077 | basic | `ddlLymphomaT` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-078 | basic | `ddlPathMGeneral` | select | shared | D034 | `Observation.component.valueCodeableConcept` | implemented-partial |
| CCP-079 | basic | `ddlPathNGeneral` | select | shared | D033 | `Observation.component.valueCodeableConcept` | implemented-partial |
| CCP-080 | basic | `ddlPathTGeneral` | select | shared | D032 | `Observation.component.valueCodeableConcept` | implemented-partial |
| CCP-081 | basic | `ddlRai` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-082 | basic | `ddlResectability` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-083 | basic | `histologyCheckBox` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-084 | basic | `rblAArbor` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-085 | basic | `rblALLCytogenetics` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-086 | basic | `rblAML` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-087 | basic | `rblASExtr` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-088 | basic | `rblBS` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-089 | basic | `rblCAML` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-090 | basic | `rblCClass` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-091 | basic | `rblCDGeneral` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-092 | basic | `rblCFAB` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-093 | basic | `rblClass` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-094 | basic | `rblCmmlWho` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-095 | basic | `rblCutaneousM` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-096 | basic | `rblCutaneousN` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-097 | basic | `rblCutaneousT` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-098 | basic | `rblCyto` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-099 | basic | `rblDisease` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-100 | basic | `rblExtranodal` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-101 | basic | `rblFAB` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-102 | basic | `rblINSS` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-103 | basic | `rblLCH1` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-104 | basic | `rblLCH111` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-105 | basic | `rblLCH122` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-106 | basic | `rblLCH2` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-107 | basic | `rblLCH21` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-108 | basic | `rblLCH3` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-109 | basic | `rblLugano` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-110 | basic | `rblMetastasis` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-111 | basic | `rblSJOMS` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-112 | basic | `rblSecondaryAML` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-113 | basic | `rblSecondaryCAML` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-114 | basic | `rblSpleen` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-115 | basic | `rblTherapyAML` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-116 | basic | `rblWHO` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-117 | basic | `rblWTS` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-118 | basic | `site` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-119 | basic | `txbAJCC` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-120 | basic | `txbAJCC8` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-121 | basic | `txbALLClassML` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-122 | basic | `txbALLCytogenetics` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-123 | basic | `txbAML` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-124 | basic | `txbAutoClinicGeneral` | text | derived | — | `QuestionnaireResponse.item / Provenance.entity` | pending-algorithm-review |
| CCP-125 | basic | `txbAutoLymphomaStage` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-126 | basic | `txbAutoPathGeneral` | text | derived | — | `QuestionnaireResponse.item / Provenance.entity` | pending-algorithm-review |
| CCP-127 | basic | `txbCALLCytogenetics` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-128 | basic | `txbCCyto` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-129 | basic | `txbCDDescGeneral` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-130 | basic | `txbCMutations` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-131 | basic | `txbCmmlWho` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-132 | basic | `txbCytoDesc` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-133 | basic | `txbDiagnosis` | textarea | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-134 | basic | `txbDiagnosisVer` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-135 | basic | `txbMetastasisDesc` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-136 | basic | `txbMutations` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-137 | basic | `txbOrganCode` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-138 | basic | `txbOrganName` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-139 | basic | `txbOtherHospital` | textarea | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-140 | basic | `txbRemark` | textarea | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-141 | basic | `txbWHO` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-142 | basic | `ddlECOG` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-143 | basic | `ddlReason` | select | shared | DIAG_TYPE | `QuestionnaireResponse.item.answer.value[x]` | implemented-partial |
| CCP-144 | basic | `txbFirstFillDate` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-145 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-146 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-147 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-148 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-149 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-150 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-151 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-152 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-153 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-154 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-155 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-156 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-157 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-158 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-159 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-160 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-161 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-162 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-163 | basic | `cblCD` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-164 | basic | `cblHisType` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-165 | basic | `cblHisType` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-166 | basic | `cblHisType` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-167 | basic | `cblHisType` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-168 | basic | `cblHisType` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-169 | basic | `cblHisType` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-170 | basic | `cblHisType` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-171 | basic | `cblHisType` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-172 | basic | `cblHisType` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-173 | basic | `cblHisType` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-174 | basic | `rb2HGrade1` | radio | shared | D004 | `Observation.valueCodeableConcept` | implemented-partial |
| CCP-175 | basic | `rb2Her1` | radio | shared | D018 | `Observation.value[x]` | implemented-partial |
| CCP-176 | basic | `rb2HerFISH1` | radio | shared | D019 | `Observation.value[x]` | implemented-partial |
| CCP-177 | basic | `rbl2Ki67` | radio | shared | D020 | `Observation.value[x]` | implemented-partial |
| CCP-178 | basic | `rblCD` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-179 | basic | `rblHGrade` | radio | shared | D031 | `QuestionnaireResponse.item.answer.value[x]` | implemented-partial |
| CCP-180 | basic | `rblHer` | radio | shared | D052 | `Observation.value[x]` | implemented-partial |
| CCP-181 | basic | `rblHerFISH` | radio | shared | D053 | `Observation.value[x]` | implemented-partial |
| CCP-182 | basic | `rblKi67` | radio | shared | D054 | `Observation.value[x]` | implemented-partial |
| CCP-183 | basic | `rblMargin` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-184 | basic | `txb2EReceptor1` | text | shared | D014, D015 | `Observation.value[x]` | implemented-partial |
| CCP-185 | basic | `txb2Ki67` | text | shared | D021 | `Observation.valueQuantity` | implemented-partial |
| CCP-186 | basic | `txb2PReceptor1` | text | shared | D016, D017 | `Observation.value[x]` | implemented-partial |
| CCP-187 | basic | `txbEReceptor` | text | shared | D048, D049 | `Observation.value[x]` | implemented-partial |
| CCP-188 | basic | `txbHisTypeDesc` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-189 | basic | `txbKi67` | text | shared | D055 | `Observation.valueQuantity` | implemented-partial |
| CCP-190 | basic | `txbLN` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-191 | basic | `txbLNTotal` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-192 | basic | `txbOCD` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-193 | basic | `txbPReceptor` | text | shared | D050, D051 | `Observation.value[x]` | implemented-partial |
| CCP-194 | basic | `txbSize1` | text | shared | D047 | `Observation.valueQuantity` | implemented-partial |
| CCP-195 | basic | `txbSize2` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-196 | basic | `txbSize3` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-197 | basic | `cblDxManner` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-198 | basic | `cblDxManner` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-199 | basic | `cblDxManner` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-200 | basic | `cblDxManner` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-201 | basic | `ddlDiagnosis` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-202 | basic | `ddlImage` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-203 | basic | `rblHospital` | radio | shared | D002 | `QuestionnaireResponse.item.answer.value[x]` | implemented-partial |
| CCP-204 | basic | `rblLocation` | radio | shared | LATERALITY | `Condition.bodySite` | implemented-partial |
| CCP-205 | basic | `cblFamilyHistory` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-206 | basic | `cblFamilyHistory` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-207 | basic | `cblFamilyHistory` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-208 | basic | `cblFamilyHistory` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-209 | basic | `cblPersonalHistory` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-210 | basic | `cblPersonalHistory` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-211 | basic | `cblPersonalHistory` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-212 | basic | `cblPersonalHistory` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-213 | basic | `ddlChemotherapy` | select | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-214 | basic | `rblFamilyHis` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-215 | basic | `rblHis` | radio | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-216 | basic | `rblMenopause` | radio | shared | P05 | `Observation.valueCodeableConcept` | implemented-partial |
| CCP-217 | basic | `txbMemCD` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-218 | basic | `txbOHD` | text | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-219 | reference_reports | `ckbMore` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-220 | reference_reports | `ckbPathMore` | checkbox | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-221 | reference_reports | `txbLabReport` | textarea | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-222 | reference_reports | `txbPath` | textarea | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |
| CCP-223 | reference_reports | `txbXray` | textarea | care-plan-only | — | `QuestionnaireResponse.item.answer.value[x]` | pending-field-review |

## 審查原則

- `implemented-partial`：已有 Care Plan／QBC 重疊欄位的 alignment check，但 common FHIR Profile 與術語仍須逐欄簽核。
- `pending-field-review`：目前只承諾完整保存來源答案，尚未宣告為標準化臨床事實。
- `pending-algorithm-review`：衍生欄位必須補上算法、版本、輸入與人工覆核規則。
