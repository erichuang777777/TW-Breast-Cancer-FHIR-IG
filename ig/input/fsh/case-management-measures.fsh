// 個管指標 Task：20 個 Measure 與其共用 CQL Library。
//
// 一個 Task 兩個報表族：品質指標 bc-qi-01～06（多專科團隊層級）與個管季報
// bc-qr-01～05 五項比率、bc-qr-10～18 九張分布表（個管師層級）。兩族共用同一份
// mapping 與同一個 Library，因為它們跑在同一組臨床事實上；分開的只有輸出。
//
// 每個 population 的 criteria.expression 對應 CQL 的 define 名稱，criteria 的來源是
// mappings/case-management/case-management-population-criteria.csv。三者（criteria 表、
// CQL、Python 參考實作）必須逐條對齊，tests/test_case_management_measures.py 會檢查。
//
// 委員會的排除／加回決議不在 Measure 裡：那是逐案人為判斷，由 Task 層套用到
// MeasureReport，並保留理由。閾值同理，屬於團隊自訂，不寫進 Measure 邏輯。
// 個管師的個案判定（分期未定、拒絕中斷程度、失聯認定）同樣留在 Task 層。

Alias: $MeasureScoring = http://terminology.hl7.org/CodeSystem/measure-scoring
Alias: $MeasureImprovement = http://terminology.hl7.org/CodeSystem/measure-improvement-notation
Alias: $MeasurePopulation = http://terminology.hl7.org/CodeSystem/measure-population
Alias: $LibraryType = http://terminology.hl7.org/CodeSystem/library-type

Instance: BreastCancerCaseManagementLibrary
InstanceOf: Library
Usage: #definition
Title: "乳癌個管指標 CQL Library"
Description: "6 項乳癌品質暨核心指標與個管季報 5 項比率、9 張分布表的 population 與 stratifier criteria 規範表達。臨床代碼所引用的 ValueSet 目前為未填代碼的佔位，代碼查證完成前本 Library 無法執行；個管作業分類為院內行政代碼，已列舉。"
* id = "BreastCancerCaseManagement"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* name = "BreastCancerCaseManagement"
* version = "1.0.0"
* status = #draft
* experimental = true
* type = $LibraryType#logic-library
* content.id = "ig-loader-BreastCancerCaseManagement.cql"
* content.contentType = #text/cql

Instance: BreastCancerQualityIndicator01
InstanceOf: Measure
Usage: #definition
Title: "品質指標1－ER 陽性給予賀爾蒙治療的比率"
Description: "侵犯性乳癌病人(第1~3期)，ER 接受體陽性給予賀爾蒙治療的比率。排除 ER 介於 1~9% 的乳癌病人。"
* id = "bc-qi-01"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qi-01"
* name = "BreastCancerQualityIndicator01HormoneTherapy"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#proportion
* improvementNotation = $MeasureImprovement#increase
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "Initial Population"
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].criteria.language = #text/cql-identifier
* group.population[1].criteria.expression = "Denominator 1"
* group.population[2].code = $MeasurePopulation#denominator-exclusion
* group.population[2].criteria.language = #text/cql-identifier
* group.population[2].criteria.expression = "Denominator 1 Exclusion"
* group.population[3].code = $MeasurePopulation#numerator
* group.population[3].criteria.language = #text/cql-identifier
* group.population[3].criteria.expression = "Numerator 1"

Instance: BreastCancerQualityIndicator02
InstanceOf: Measure
Usage: #definition
Title: "品質指標2(核心1)－哨兵淋巴結取樣術的比率"
Description: "臨床第1、2期乳癌以手術為首次治療，最後病理腋下淋巴結為陰性、施行哨兵淋巴結取樣術的比率。"
* id = "bc-qi-02"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qi-02"
* name = "BreastCancerQualityIndicator02SentinelNodeBiopsy"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#proportion
* improvementNotation = $MeasureImprovement#increase
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "Initial Population"
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].criteria.language = #text/cql-identifier
* group.population[1].criteria.expression = "Denominator 2"
* group.population[2].code = $MeasurePopulation#numerator
* group.population[2].criteria.language = #text/cql-identifier
* group.population[2].criteria.expression = "Numerator 2"

Instance: BreastCancerQualityIndicator03
InstanceOf: Measure
Usage: #definition
Title: "品質指標3(核心2)－淋巴結陽性≧4顆全切除後放射治療的比率"
Description: "接受乳房全切除手術且腋下淋巴結陽性≧4顆，有進行放射治療的比率。排除乳癌第四期病人。定義原文分子另要求臨床標靶體積劑量≧4000cGy，惟現行資料無劑量欄位（N3-DOSE，見 criteria 表），本 Measure 僅驗證是否完成放射治療，計算結果為上界。"
* id = "bc-qi-03"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qi-03"
* name = "BreastCancerQualityIndicator03PostMastectomyRadiotherapy"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#proportion
* improvementNotation = $MeasureImprovement#increase
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "Initial Population"
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].criteria.language = #text/cql-identifier
* group.population[1].criteria.expression = "Denominator 3"
* group.population[2].code = $MeasurePopulation#denominator-exclusion
* group.population[2].criteria.language = #text/cql-identifier
* group.population[2].criteria.expression = "Denominator 3 Exclusion"
* group.population[3].code = $MeasurePopulation#numerator
* group.population[3].criteria.language = #text/cql-identifier
* group.population[3].criteria.expression = "Numerator 3"

Instance: BreastCancerQualityIndicator04
InstanceOf: Measure
Usage: #definition
Title: "品質指標4(核心3)－HER2 陽性淋巴轉移給予 anti HER2 藥物治療的比率"
Description: "HER2 接受體陽性且淋巴轉移之手術病人，給予 anti HER2 藥物治療的比率。排除轉移性乳癌病人。"
* id = "bc-qi-04"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qi-04"
* name = "BreastCancerQualityIndicator04AntiHER2Therapy"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#proportion
* improvementNotation = $MeasureImprovement#increase
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "Initial Population"
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].criteria.language = #text/cql-identifier
* group.population[1].criteria.expression = "Denominator 4"
* group.population[2].code = $MeasurePopulation#denominator-exclusion
* group.population[2].criteria.language = #text/cql-identifier
* group.population[2].criteria.expression = "Denominator 4 Exclusion"
* group.population[3].code = $MeasurePopulation#numerator
* group.population[3].criteria.language = #text/cql-identifier
* group.population[3].criteria.expression = "Numerator 4"

Instance: BreastCancerQualityIndicator05
InstanceOf: Measure
Usage: #definition
Title: "品質指標5－手術前組織學確診的比率"
Description: "乳癌病人在手術進行至少前一天曾經組織學確診的比率。排除原位癌及轉移性乳癌病人。"
* id = "bc-qi-05"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qi-05"
* name = "BreastCancerQualityIndicator05PreoperativeDiagnosis"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#proportion
* improvementNotation = $MeasureImprovement#increase
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "Initial Population"
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].criteria.language = #text/cql-identifier
* group.population[1].criteria.expression = "Denominator 5"
* group.population[2].code = $MeasurePopulation#denominator-exclusion
* group.population[2].criteria.language = #text/cql-identifier
* group.population[2].criteria.expression = "Denominator 5 Exclusion"
* group.population[3].code = $MeasurePopulation#numerator
* group.population[3].criteria.language = #text/cql-identifier
* group.population[3].criteria.expression = "Numerator 5"

Instance: BreastCancerQualityIndicator06
InstanceOf: Measure
Usage: #definition
Title: "品質指標6－乳房保留手術後放射線治療的比率"
Description: "病理分期侵犯性乳癌，乳房保留手術後放射線治療的比率。排除轉移性乳癌。年齡與淋巴結排除條件有 practice 與 definition 兩種讀法，由 Indicator 6 Variant 參數選擇，差異見 Task 頁。"
* id = "bc-qi-06"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qi-06"
* name = "BreastCancerQualityIndicator06PostLumpectomyRadiotherapy"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#proportion
* improvementNotation = $MeasureImprovement#increase
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "Initial Population"
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].criteria.language = #text/cql-identifier
* group.population[1].criteria.expression = "Denominator 6"
* group.population[2].code = $MeasurePopulation#denominator-exclusion
* group.population[2].criteria.language = #text/cql-identifier
* group.population[2].criteria.expression = "Denominator 6 Exclusion"
* group.population[3].code = $MeasurePopulation#numerator
* group.population[3].criteria.language = #text/cql-identifier
* group.population[3].criteria.expression = "Numerator 6"


// ==========================================================================
// 個管季報 quarterly：五項比率
//
// 核算單位是個管師個人，不是團隊。MeasureReport.reporter 帶個管師，全院數字是
// 各報告相加，不另算一次；Library 以 "Reporting Case Manager" 參數限定收案範圍。
// ==========================================================================

Instance: BreastCancerQuarterlyReport01RetentionRate
InstanceOf: Measure
Usage: #definition
Title: "季報1－留院治療率"
Description: "新診斷個案中留在本院接受治療者的比率。分母扣除分期檢查中、診斷中死亡與考慮治療且回診間隔小於一個月者；分子扣除診斷中轉院與不治療未回診者。"
* id = "bc-qr-01"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-01"
* name = "BreastCancerQuarterlyReport01RetentionRate"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#proportion
* improvementNotation = $MeasureImprovement#increase
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "New Diagnosis Case"
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].criteria.language = #text/cql-identifier
* group.population[1].criteria.expression = "Denominator QR1"
* group.population[2].code = $MeasurePopulation#denominator-exclusion
* group.population[2].criteria.language = #text/cql-identifier
* group.population[2].criteria.expression = "Denominator QR1 Exclusion"
* group.population[3].code = $MeasurePopulation#numerator
* group.population[3].criteria.language = #text/cql-identifier
* group.population[3].criteria.expression = "Numerator QR1"
* group.population[4].code = $MeasurePopulation#numerator-exclusion
* group.population[4].criteria.language = #text/cql-identifier
* group.population[4].criteria.expression = "Numerator QR1 Exclusion"

Instance: BreastCancerQuarterlyReport02RetentionRateWithinSystem
InstanceOf: Measure
Usage: #definition
Title: "季報2－留院治療率（臺大體系內矯正後）"
Description: "分母同季報1，分子加計轉往臺大體系內醫院治療者。體系判定改以 Organization.partOf 表達，取代現行以醫院名稱字串比對關鍵字清單。"
* id = "bc-qr-02"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-02"
* name = "BreastCancerQuarterlyReport02RetentionRateWithinSystem"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#proportion
* improvementNotation = $MeasureImprovement#increase
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "New Diagnosis Case"
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].criteria.language = #text/cql-identifier
* group.population[1].criteria.expression = "Denominator QR2"
* group.population[2].code = $MeasurePopulation#numerator
* group.population[2].criteria.language = #text/cql-identifier
* group.population[2].criteria.expression = "Numerator QR2"

Instance: BreastCancerQuarterlyReport03TreatmentCompletionRate
InstanceOf: Measure
Usage: #definition
Title: "季報3－完成治療率"
Description: "留院且醫師建議接受治癒性治療的新診斷個案中，完成治療者的比率。分母扣除診斷中、治療中事件與不可治癒性治療；分子扣除未完成治療者（拒絕部分治療或中斷）。"
* id = "bc-qr-03"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-03"
* name = "BreastCancerQuarterlyReport03TreatmentCompletionRate"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#proportion
* improvementNotation = $MeasureImprovement#increase
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "New Diagnosis Case"
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].criteria.language = #text/cql-identifier
* group.population[1].criteria.expression = "Denominator QR3"
* group.population[2].code = $MeasurePopulation#denominator-exclusion
* group.population[2].criteria.language = #text/cql-identifier
* group.population[2].criteria.expression = "Denominator QR3 Exclusion"
* group.population[3].code = $MeasurePopulation#numerator
* group.population[3].criteria.language = #text/cql-identifier
* group.population[3].criteria.expression = "Numerator QR3"
* group.population[4].code = $MeasurePopulation#numerator-exclusion
* group.population[4].criteria.language = #text/cql-identifier
* group.population[4].criteria.expression = "Numerator QR3 Exclusion"

Instance: BreastCancerQuarterlyReport04LossToFollowUpRate
InstanceOf: Measure
Usage: #definition
Title: "季報4－失聯率"
Description: "前一年度加本期新診斷且存活個案中，自最後一次與醫療團隊聯繫起滿一年未再聯繫者的比率。**目前無法計算**：分母需要前一年度名單，單期匯出檔從未包含。在名單補齊前本 Measure 不得呈現為已計算值，見 Task 頁的資料缺口。"
* id = "bc-qr-04"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-04"
* name = "BreastCancerQuarterlyReport04LossToFollowUpRate"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#proportion
* improvementNotation = $MeasureImprovement#decrease
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "Prior Year And Current New Diagnosis Cohort"
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].criteria.language = #text/cql-identifier
* group.population[1].criteria.expression = "Denominator QR4"
* group.population[2].code = $MeasurePopulation#numerator
* group.population[2].criteria.language = #text/cql-identifier
* group.population[2].criteria.expression = "Numerator QR4"

Instance: BreastCancerQuarterlyReport05TreatmentResumptionRate
InstanceOf: Measure
Usage: #definition
Title: "季報5－重返治療率"
Description: "期間內拒絕及中斷治療個案中，重返治療者的比率。重返認定目前由個管師逐案判斷，無可推導的臨床事實；分子表達為治療資源在中斷後重新開始，實際採用前需與個管師判定逐案比對。"
* id = "bc-qr-05"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-05"
* name = "BreastCancerQuarterlyReport05TreatmentResumptionRate"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#proportion
* improvementNotation = $MeasureImprovement#increase
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "Quarterly Caseload"
* group.population[1].code = $MeasurePopulation#denominator
* group.population[1].criteria.language = #text/cql-identifier
* group.population[1].criteria.expression = "Denominator QR5"
* group.population[2].code = $MeasurePopulation#numerator
* group.population[2].criteria.language = #text/cql-identifier
* group.population[2].criteria.expression = "Numerator QR5"


// ==========================================================================
// 個管季報 quarterly：九張分布表
//
// 分布表以 cohort Measure 加 stratifier 表達，不是九個獨立比率。stratifier 的
// 值域即報表的欄位，值域外的值代表統計會漏算，必須當成錯誤處理而不是歸入其他。
// ==========================================================================

Instance: BreastCancerQuarterlyReport10CaseloadByEntryCategory
InstanceOf: Measure
Usage: #definition
Title: "季報10－全部收案量（依收案身份）"
Description: "報告期間該個管師的全部收案，依收案身份分層。此表是唯一使用全部收案而非新診斷的表。"
* id = "bc-qr-10"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-10"
* name = "BreastCancerQuarterlyReport10CaseloadByEntryCategory"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#cohort
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "Quarterly Caseload"
* group.stratifier[0].code.text = "收案身份"
* group.stratifier[0].criteria.language = #text/cql-identifier
* group.stratifier[0].criteria.expression = "Case Entry Category"

Instance: BreastCancerQuarterlyReport11NewDiagnosisByMonth
InstanceOf: Measure
Usage: #definition
Title: "季報11－新診斷收案量（依月份）"
Description: "新診斷個案依收案月份分層。"
* id = "bc-qr-11"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-11"
* name = "BreastCancerQuarterlyReport11NewDiagnosisByMonth"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#cohort
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "New Diagnosis Case"
* group.stratifier[0].code.text = "收案月份"
* group.stratifier[0].criteria.language = #text/cql-identifier
* group.stratifier[0].criteria.expression = "Case Entry Month"

Instance: BreastCancerQuarterlyReport12NewDiagnosisByStatus
InstanceOf: Measure
Usage: #definition
Title: "季報12－新診斷動態（依收案狀態）"
Description: "新診斷個案依報告期末的收案狀態分層。仍在分期中的個案系統值為治療期，由個管師改判為診斷期，覆寫必須保留。"
* id = "bc-qr-12"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-12"
* name = "BreastCancerQuarterlyReport12NewDiagnosisByStatus"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#cohort
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "New Diagnosis Case"
* group.stratifier[0].code.text = "收案狀態"
* group.stratifier[0].criteria.language = #text/cql-identifier
* group.stratifier[0].criteria.expression = "Case Status"

Instance: BreastCancerQuarterlyReport13ClosureByReason
InstanceOf: Measure
Usage: #definition
Title: "季報13－新診斷結案量（依結案原因）"
Description: "新診斷個案依結案原因分層；未結案者無分層值。結案量即有分層值者的合計。"
* id = "bc-qr-13"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-13"
* name = "BreastCancerQuarterlyReport13ClosureByReason"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#cohort
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "New Diagnosis Case"
* group.stratifier[0].code.text = "結案原因"
* group.stratifier[0].criteria.language = #text/cql-identifier
* group.stratifier[0].criteria.expression = "Closure Reason"

Instance: BreastCancerQuarterlyReport14SexAndAgeBand
InstanceOf: Measure
Usage: #definition
Title: "季報14－新診斷個案性別與年齡層分布"
Description: "新診斷個案依性別與收案時年齡層分層。年齡層改由出生日期對收案日期計算，取代匯出檔預先算好的區間碼。"
* id = "bc-qr-14"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-14"
* name = "BreastCancerQuarterlyReport14SexAndAgeBand"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#cohort
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "New Diagnosis Case"
* group.stratifier[0].code.text = "性別"
* group.stratifier[0].criteria.language = #text/cql-identifier
* group.stratifier[0].criteria.expression = "Administrative Sex"
* group.stratifier[1].code.text = "年齡層"
* group.stratifier[1].criteria.language = #text/cql-identifier
* group.stratifier[1].criteria.expression = "Age Band At Case Entry"

Instance: BreastCancerQuarterlyReport15RegistryClass
InstanceOf: Measure
Usage: #definition
Title: "季報15－新診斷個案 Class 分類分布"
Description: "新診斷個案依 Class 分類分層。仍在分期中者一律以診斷中呈現，不論登錄的 Class 為何。Class 3 不列入 Class 表，另以附註呈現。"
* id = "bc-qr-15"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-15"
* name = "BreastCancerQuarterlyReport15RegistryClass"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#cohort
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "New Diagnosis Case"
* group.stratifier[0].code.text = "Class 分類"
* group.stratifier[0].criteria.language = #text/cql-identifier
* group.stratifier[0].criteria.expression = "Registry Case Class Reported"
* group.stratifier[1].code.text = "Class 3（表外附註）"
* group.stratifier[1].criteria.language = #text/cql-identifier
* group.stratifier[1].criteria.expression = "Is Registry Class 3"

Instance: BreastCancerQuarterlyReport16StageDistribution
InstanceOf: Measure
Usage: #definition
Title: "季報16－新診斷個案分期分布"
Description: "新診斷個案依分期分層。分期檢查未完成者為診斷中；診斷中轉院與外院資料不足者為其它。三者在現行工作表同樣填 `?`，必須在共同層分開，見 Task 頁。"
* id = "bc-qr-16"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-16"
* name = "BreastCancerQuarterlyReport16StageDistribution"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#cohort
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "New Diagnosis Case"
* group.stratifier[0].code.text = "分期"
* group.stratifier[0].criteria.language = #text/cql-identifier
* group.stratifier[0].criteria.expression = "Reported Stage Group"

Instance: BreastCancerQuarterlyReport17HistologyDistribution
InstanceOf: Measure
Usage: #definition
Title: "季報17－侵襲癌組織類型分布"
Description: "新診斷個案依組織類型分層；DCIS with microinvasion 併入侵襲癌，DCIS 與 phyllodes 為獨立分層且不計入侵襲癌分母。"
* id = "bc-qr-17"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-17"
* name = "BreastCancerQuarterlyReport17HistologyDistribution"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#cohort
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "New Diagnosis Case"
* group.stratifier[0].code.text = "組織類型"
* group.stratifier[0].criteria.language = #text/cql-identifier
* group.stratifier[0].criteria.expression = "Histology Group"

Instance: BreastCancerQuarterlyReport18SubtypeDistribution
InstanceOf: Measure
Usage: #definition
Title: "季報18－侵襲癌 HR/HER2 分型分布"
Description: "新診斷侵襲癌個案依 HR/HER2 分型分層。分型由 ER、PR、HER2 判讀推導，不儲存人工鍵入的字母；無法判斷者為獨立分層，不併入任何一型。"
* id = "bc-qr-18"
* url = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Measure/bc-qr-18"
* name = "BreastCancerQuarterlyReport18SubtypeDistribution"
* version = "1.0.0-preview.1"
* status = #draft
* experimental = true
* library = "https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG/Library/BreastCancerCaseManagement"
* scoring = $MeasureScoring#cohort
* group.population[0].code = $MeasurePopulation#initial-population
* group.population[0].criteria.language = #text/cql-identifier
* group.population[0].criteria.expression = "New Diagnosis Case"
* group.stratifier[0].code.text = "HR/HER2 分型"
* group.stratifier[0].criteria.language = #text/cql-identifier
* group.stratifier[0].criteria.expression = "HR HER2 Subtype"

Profile: BreastCancerCaseManagementReport
Parent: MeasureReport
Id: breast-cancer-case-management-report
Title: "乳癌個管指標 MeasureReport - Community Draft"
Description: "個管指標 Task 的報表輸出，兩個報表族共用。summary 版供委員會與癌症中心使用；subject-list 版含個案清單，僅限院內流通。季報的核算單位是個管師個人，reporter 必填，全院數字是各報告相加而非另算一次。委員會的排除／加回決議與自訂閾值以 extension 表達，extension 定義待設計。"
* ^status = #draft
* ^experimental = true
* type MS
* measure MS
* period MS
* reporter MS
* group MS
* group.population MS
* group.stratifier MS
* group.measureScore MS
