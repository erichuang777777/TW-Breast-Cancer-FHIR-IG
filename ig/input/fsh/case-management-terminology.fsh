// 個管指標 Task 的術語佔位。
//
// 這些 ValueSet 目前**刻意不列舉任何代碼**。mappings/case-management 的對應表把每一個
// 候選 LOINC／SNOMED CT 代碼標記為 candidate-unverified；在逐碼比對發布版之前，
// 把候選碼寫進 ValueSet 會讓未查證的內容看起來像已確認的事實。
//
// 因此每個 ValueSet 只宣告「這裡應該放什麼」，由 CQL 引用；ValueSet 補齊之前，
// Library 無法執行，這正是目前的真實狀態。填入代碼時必須同步把對應表的
// terminology_status 改為已驗證，並補上驗證來源與版本。

ValueSet: CMClinicalStageGroupCodes
Id: cm-clinical-stage-group-code
Title: "個管指標－臨床期別 Observation 代碼"
Description: "用來辨識「臨床期別」分期 Observation 的代碼。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMPathologicalStageGroupCodes
Id: cm-pathological-stage-group-code
Title: "個管指標－病理期別 Observation 代碼"
Description: "用來辨識「病理期別」分期 Observation 的代碼，含前導性治療後的 ypStage。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMPathologicalNodeCategoryCodes
Id: cm-pathological-n-category-code
Title: "個管指標－病理 N 分類 Observation 代碼"
Description: "用來辨識病理區域淋巴結分類 Observation 的代碼。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMPathologicalTumorCategoryCodes
Id: cm-pathological-t-category-code
Title: "個管指標－病理 T 分類 Observation 代碼"
Description: "用來辨識病理原發腫瘤分類 Observation 的代碼。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMEstrogenReceptorCodes
Id: cm-estrogen-receptor-code
Title: "個管指標－ER 檢驗 Observation 代碼"
Description: "用來辨識雌激素接受體檢驗 Observation 的代碼。指標1 需要百分比數值，不是判讀結果。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMHER2ImmunohistochemistryCodes
Id: cm-her2-ihc-code
Title: "個管指標－HER2 免疫組織化學染色 Observation 代碼"
Description: "用來辨識 HER2 IHC 判讀（0／1+／2+／3+）Observation 的代碼。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMHER2InSituHybridizationCodes
Id: cm-her2-ish-code
Title: "個管指標－HER2 原位雜交 Observation 代碼"
Description: "用來辨識 HER2 ISH／FISH Observation 的代碼；僅在 IHC 為 2+ 時需要。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMBreastSurgeryProcedureCodes
Id: cm-breast-surgery-procedure
Title: "個管指標－乳癌手術 Procedure 代碼"
Description: "任何以治療乳癌為目的之乳房手術。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMBreastConservingSurgeryProcedureCodes
Id: cm-breast-conserving-surgery-procedure
Title: "個管指標－乳房保留手術 Procedure 代碼"
Description: "乳房保留手術（BCT／partial mastectomy）。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMTotalMastectomyProcedureCodes
Id: cm-total-mastectomy-procedure
Title: "個管指標－乳房全切除 Procedure 代碼"
Description: "乳房全切除，含 MRM、SM 與 NSM。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMSentinelLymphNodeBiopsyProcedureCodes
Id: cm-sentinel-lymph-node-biopsy-procedure
Title: "個管指標－哨兵淋巴結取樣術 Procedure 代碼"
Description: "哨兵淋巴結取樣術（SLNB）。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMAxillaryLymphNodeDissectionProcedureCodes
Id: cm-axillary-lymph-node-dissection-procedure
Title: "個管指標－腋下淋巴結廓清術 Procedure 代碼"
Description: "腋下淋巴結廓清術（ALND）。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMCoreNeedleBiopsyProcedureCodes
Id: cm-core-needle-biopsy-procedure
Title: "個管指標－乳房粗針切片 Procedure 代碼"
Description: "術前組織學確診用的乳房粗針切片。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMRadiotherapyProcedureCodes
Id: cm-radiotherapy-procedure
Title: "個管指標－放射線治療 Procedure 代碼"
Description: "體外放射線治療療程。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMHormoneTherapyMedicationCodes
Id: cm-hormone-therapy-medication
Title: "個管指標－賀爾蒙治療藥品代碼"
Description: "乳癌賀爾蒙治療藥品，含 tamoxifen、aromatase inhibitor 與 LHRH agonist。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMCytotoxicChemotherapyMedicationCodes
Id: cm-cytotoxic-chemotherapy-medication
Title: "個管指標－化學治療藥品代碼"
Description: "乳癌細胞毒性化學治療藥品。用於判定手術是否為首次治療。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMAntiHER2MedicationCodes
Id: cm-anti-her2-medication
Title: "個管指標－anti HER2 藥品代碼"
Description: "抗 HER2 藥品，含 trastuzumab、pertuzumab、T-DM1 與 trastuzumab deruxtecan。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

// ==========================================================================
// 季報用的臨床代碼佔位（與上方同樣待查證）
// ==========================================================================

ValueSet: CMProgesteroneReceptorCodes
Id: cm-progesterone-receptor-code
Title: "個管指標－PR 檢驗 Observation 代碼"
Description: "用來辨識黃體素接受體檢驗 Observation 的代碼。季報 HR/HER2 分型需要 ER 與 PR 兩者。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

ValueSet: CMHistologyMorphologyCodes
Id: cm-histology-morphology-code
Title: "個管指標－組織型態 Observation 代碼"
Description: "用來辨識組織型態（morphology）Observation 的代碼；值為 ICD-O-3 型態碼。取代現行以自由文字加正規表達式歸併 27 種拼法的作法。內容待驗證後補齊。"
* ^status = #draft
* ^experimental = true

// ==========================================================================
// 個管作業分類：院內行政代碼
// ==========================================================================
//
// 以下 CodeSystem 與上方的臨床 ValueSet 性質不同，**刻意列舉代碼**。
//
// 這些不是臨床發現，是個管團隊自己定義、自己維護的作業分類：收案身份、收案
// 狀態、結案原因、Class 分類、留治處置、治癒性治療處置、完治結果。它們沒有
// 對應的 LOINC 或 SNOMED CT 概念可查證，查證也不是正確的動作——它們的權威來源
// 就是個管團隊本身。因此列舉代碼在這裡是誠實的，在上方的臨床 ValueSet 則不是。
//
// 這些代碼是 Task-only 資料的表達方式，**不得提升為乳癌共用臨床術語**，
// 見 mappings/case-management/case-management-task-only-fields.csv。

CodeSystem: CMCaseEntryCategoryCS
Id: cm-case-entry-category
Title: "個管收案身份"
Description: "個管師登錄的收案身份，決定個案是否進入新診斷各表（CM-TASK-002）。"
* ^status = #draft
* ^experimental = true
* ^caseSensitive = true
* #new-diagnosis "新診斷"
* #existing-case "舊案"
* #delayed-entry-same-year "延遲收案-當年度"
* #delayed-entry-prior-year "延遲收案-非當年度"
* #first-recurrence-curable "首復發可治癒"
* #first-recurrence-noncurable "首復發不可治癒"

ValueSet: CMCaseEntryCategoryVS
Id: cm-case-entry-category-vs
Title: "個管收案身份值集"
Description: "CM-TASK-002 收案身份的完整值域。"
* ^status = #draft
* ^experimental = true
* include codes from system CMCaseEntryCategoryCS

CodeSystem: CMCaseStatusCS
Id: cm-case-status
Title: "個管收案狀態（新診斷動態）"
Description: "個案在報告期末的個管狀態（CM-TASK-003）。仍在分期中的個案系統值為治療期，由個管師改為診斷期，覆寫與理由必須保留在稽核輸出。"
* ^status = #draft
* ^experimental = true
* ^caseSensitive = true
* #diagnosis "診斷期"
* #treatment "治療期"
* #clinical-trial "臨床試驗"
* #follow-up "追蹤期"
* #palliative "緩和醫療"
* #refused-interrupted "拒絕與中斷"
* #closed "結案"

ValueSet: CMCaseStatusVS
Id: cm-case-status-vs
Title: "個管收案狀態值集"
Description: "CM-TASK-003 收案狀態的完整值域。"
* ^status = #draft
* ^experimental = true
* include codes from system CMCaseStatusCS

CodeSystem: CMClosureReasonCS
Id: cm-closure-reason
Title: "個管結案原因"
Description: "結案個案的結案原因（CM-TASK-003 與 CM-BC-031、CM-BC-036）。死亡與轉院有臨床事實支撐，拒絕返診與病危 AAD 是個管判斷。"
* ^status = #draft
* ^experimental = true
* ^caseSensitive = true
* #death "死亡"
* #transferred "轉院"
* #refused-return "拒絕返診"
* #critical-aad "病危AAD"

ValueSet: CMClosureReasonVS
Id: cm-closure-reason-vs
Title: "個管結案原因值集"
Description: "結案原因的完整值域。"
* ^status = #draft
* ^experimental = true
* include codes from system CMClosureReasonCS

CodeSystem: CMRegistryCaseClassCS
Id: cm-registry-case-class
Title: "癌症登記 Class 分類"
Description: "個管師指派的登記 Class 分類（CM-TASK-001），兩個報表族共用。Class 3 目前寫在 subtype 自由文字欄，靠字串比對撈回；明確登錄後此代理即解除。"
* ^status = #draft
* ^experimental = true
* ^caseSensitive = true
* #class-0 "Class 0"
* #class-1 "Class 1"
* #class-2 "Class 2"
* #class-3 "Class 3"

ValueSet: CMRegistryCaseClassVS
Id: cm-registry-case-class-vs
Title: "Class 分類值集"
Description: "CM-TASK-001 Class 分類的完整值域。"
* ^status = #draft
* ^experimental = true
* include codes from system CMRegistryCaseClassCS

CodeSystem: CMRetentionDispositionCS
Id: cm-retention-disposition
Title: "留院治療處置"
Description: "是否留院治療及不留院原因（CM-TASK-004、CM-TASK-005），bc-qr-01 與 bc-qr-02 的分子與排除來源。"
* ^status = #draft
* ^experimental = true
* ^caseSensitive = true
* #stay "留院治療"
* #transfer-during-staging "診斷中轉院"
* #no-treatment-no-return "完全不治療且未回診"
* #untreated-return-over-1m "未接受治療且回診間隔大於一個月"
* #considering-return-under-1m "考慮治療且回診間隔小於一個月"
* #staging-in-progress "分期檢查中"
* #death-during-staging "診斷中死亡"

ValueSet: CMRetentionDispositionVS
Id: cm-retention-disposition-vs
Title: "留院治療處置值集"
Description: "留治處置與不列入分母原因的完整值域。"
* ^status = #draft
* ^experimental = true
* include codes from system CMRetentionDispositionCS

CodeSystem: CMCurativeTreatmentDispositionCS
Id: cm-curative-treatment-disposition
Title: "可治癒性治療細目"
Description: "bc-qr-03 完治率分母的處置分類（CM-TASK-006）。事件本身可由治療資源推導，醫師的判斷理由不行。"
* ^status = #draft
* ^experimental = true
* ^caseSensitive = true
* #in-curative-treatment "接受治癒性治療中"
* #death-during-treatment "治療中死亡"
* #transfer-during-treatment "治療中轉院"
* #physician-advised-stop "醫師建議停止治療"
* #not-advisable "特殊狀況不建議治癒性治療"
* #active-surveillance "積極監測"
* #noncurative "不可治癒性治療"

ValueSet: CMCurativeTreatmentDispositionVS
Id: cm-curative-treatment-disposition-vs
Title: "可治癒性治療細目值集"
Description: "CM-TASK-006 的完整值域。"
* ^status = #draft
* ^experimental = true
* include codes from system CMCurativeTreatmentDispositionCS

CodeSystem: CMTreatmentCompletionCS
Id: cm-treatment-completion
Title: "完成治療結果"
Description: "bc-qr-03 分子與 bc-qr-05 分母的來源（CM-TASK-007）。完成可由治療資源狀態推導；拒絕與中斷不行。"
* ^status = #draft
* ^experimental = true
* ^caseSensitive = true
* #completed-here "留院完成治療"
* #completed-then-death "完治後死亡"
* #completed-then-transfer "完治後轉院"
* #incomplete-refused-part "未完成治療-拒絕部分治療"
* #incomplete-interrupted "未完成治療-中斷治療"

ValueSet: CMTreatmentCompletionVS
Id: cm-treatment-completion-vs
Title: "完成治療結果值集"
Description: "CM-TASK-007 的完整值域。"
* ^status = #draft
* ^experimental = true
* include codes from system CMTreatmentCompletionCS

CodeSystem: CMTaskInputTypeCS
Id: cm-task-input-type
Title: "個管 Task 輸入欄位型別"
Description: "個管作業資料掛在 `Task.input.type` 上的欄位型別代碼；每一個對應一項 Task-only 欄位。CQL 以這些代碼取值，不從臨床資源猜測。"
* ^status = #draft
* ^experimental = true
* ^caseSensitive = true
* #case-entry-category "收案身份（CM-TASK-002）"
* #case-status "收案狀態（CM-TASK-003）"
* #closure-reason "結案原因（CM-TASK-003）"
* #registry-case-class "Class 分類（CM-TASK-001）"
* #retention-disposition "留院治療處置（CM-TASK-004、CM-TASK-005）"
* #curative-treatment-disposition "可治癒性治療細目（CM-TASK-006）"
* #treatment-completion "完成治療結果（CM-TASK-007）"

ValueSet: CMTaskInputTypeVS
Id: cm-task-input-type-vs
Title: "個管 Task 輸入欄位型別值集"
Description: "Task.input.type 可用的欄位型別。"
* ^status = #draft
* ^experimental = true
* include codes from system CMTaskInputTypeCS
