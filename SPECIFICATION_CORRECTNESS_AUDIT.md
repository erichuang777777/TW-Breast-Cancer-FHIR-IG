# FHIR IG 規格正確性稽核

本文件回答三件不同的事：哪些內容要比對、資料要正確到什麼程度、以及目前能不能宣稱規格正確。結論必須拆開看：

- **FHIR 技術結構：目前通過。** IG 以 FHIR R4 `4.0.1` 建置；SUSHI、完整 Publisher、reference、profile 與 expression wiring 都通過現有自動檢查。
- **CQL 機械行為：目前通過合成測試。** 20/20 Measure、46/46 criteria 可轉譯與執行，且現有 draft 規則的正負、缺值、邊界與列舉分層已有預期值測試。
- **臨床與作業規格：尚未證明正確。** 目前沒有已核准的原始資料契約、19 個臨床 ValueSet 仍為空、沒有獨立重算與真實完整報告期間 golden cohort，且仍有已知定義矛盾或缺資料規則。

因此目前可發布的最高宣稱仍是 **非官方、experimental 的技術草稿**；不能宣稱院內品管數字正確、跨院可互通或可正式申報。

## 技術規格基準與宣稱邊界

本次技術判定只依 IG 實際固定的版本：FHIR R4 `4.0.1`、TW Core `1.0.0`、CQL IG `2.0.0`、CRMI `2.0.0`，以及本專案固定的 IG Publisher `2.3.2`。核心資源語法以 HL7 FHIR R4 的 [Measure](https://hl7.org/fhir/R4/measure.html) 與 [MeasureReport](https://hl7.org/fhir/R4/measurereport.html) 為準；依賴版本以 `ig/sushi-config.yaml` 為準。

Publisher／SUSHI 通過所證明的是「產出的資源符合目前載入的 FHIR package 與本 IG profile 約束」。它不會證明：

- 醫院欄位被投影到正確的臨床概念；
- 指標定義本身得到癌委會或報表 owner 核准；
- 未列為 dependency／未宣告 conformance 的 CQF Measures 或其他 IG 也已符合；
- 臺灣主管機關、HL7、TW Core、mCODE 或 ICHOM 對本 IG 有認可。

若未來要增加任何外部 conformance 宣稱，必須先固定該 package/version、套用其 profile、通過完整 validator，再把宣稱與證據加入本表；不能由「語意參考」推論成 conformance。

## 到底要用幾種方式核對

### 資料與 Measure 正確性：六層證據，全部必須通過

1. 原始來源逐欄追溯。
2. FHIR 結構與語意 conformance。
3. terminology 逐碼與版本化 expansion 核對。
4. CQL 合成 truth-table／boundary 測試。
5. 不共用 CQL 邏輯的獨立重算。
6. 一個完整報告期間的 source-to-FHIR-to-MeasureReport 逐案 golden cohort reconciliation。

這六項不是六選一，也不能用總數相同代替逐案相同。完整門檻見 [PUBLICATION_ACCEPTANCE_MATRIX.md](PUBLICATION_ACCEPTANCE_MATRIX.md)。

### 要升級成正式發布：再加兩個 release control，共八項

7. 臨床、病理、術語、資料治理 owner 對定義、版本、例外與人工 override 的具名簽核。
8. 發布與營運驗收：隱私／資安、canonical 與 package 版本不可變性、artifact hash、接收端或 VPN 回執，以及跨院主張所需的第二個獨立實作者。

所以答案是：**驗證數字正確需要六種；要宣稱正式可發布，總共要八種控制全部完成。**

八項控制的機器可讀狀態位於 [`mappings/publication/release-control-register.csv`](mappings/publication/release-control-register.csv)，20 個 Measure 的逐項規格核准位於 [`mappings/publication/case-management-measure-approval-register.csv`](mappings/publication/case-management-measure-approval-register.csv)。`scripts/audit_release_controls.py` 依 Measure audit、19 個臨床 ValueSet、完整且不重複的 QBC 14-Gate 集合、完整且不重複的 Measure 20-approval 集合、簽核內容與 Publisher audit 重新推導，並拒絕刪列或 register 自稱與證據不一致。現況為 **2/8 pass**：只有 RC-02 FHIR conformance 與 RC-04 合成規則執行通過；RC-01、03、05、06、07、08 均 blocked。即使未來 Publisher warnings 降到 0，也不能繞過這六個阻擋項目取得 formal release pass。

RC-08 另外驗證全 IG 的 10 個 scope claim 與 10 個逐項角色決策；目前 0/10 簽核。QBC 與個管品管／季報是 normative Task，因此兩者的 claim evidence 都必須升級為 `formal-release-ready`，才可能通過 whole-IG publication gate。單一 Task 的技術驗證或 operational approval 不會自動擴張成整份 IG 的正式發布證據。

Profile／Extension 規格也採逐項核對，而不是只看 Publisher 總數。目前正式集合為 **46 個 StructureDefinition：33 Profile、13 Extension**；其中 4 個 TCR extension 是手寫 JSON，不能因不在 FSH 清單中而漏掉。`artifact-conformance-register.csv` 鎖定每個 artifact 的 parent、type、kind、scope 與合成範例，技術稽核為 46/46 pass；但逐 artifact 的臨床／FHIR reviewer 核准仍是 **0/46**，所以 RC-07 繼續 blocked。

Terminology 也不能只計算 FSH 檔案或只檢查 CQL 有沒有名稱。實際發布集合是 **152 個 artifact：60 CodeSystem、90 ValueSet、2 ConceptMap**；機器稽核目前確認其 canonical、狀態、基本內容與內部參照完整。個管範圍另有精確的 19 項臨床 ValueSet 核准集合：18 項已被 CQL 引用，腋下淋巴結廓清術 1 項是 defined-not-referenced；19 項目前皆無內容且 **0/19** 完成具名、版本化簽核。因此能證明的是「terminology inventory 技術完整」，不能證明臨床代碼集合或 CQL cohort 語意正確，RC-03 仍 blocked。

全 IG 另有一份不可用「總數相同」取代的精確 resource manifest：**260 個 type/id** 必須逐項一致，其中 224 個 definitions、36 個 synthetic examples、222 個 canonical resources；260 項中 157 項由 FSH 生成、103 項為手寫 JSON。技術稽核要求生成的 ImplementationGuide 精確引用其餘 259 項，並驗證 example 分類、canonical、CapabilityStatement、Library／Measure 與 NamingSystem 關係。稽核發現並修正 TCR abstraction Task 被錯標為 definition。這證明發布包沒有漏件或角色漂移，不證明每一資源的臨床內容正確。

版本語意仍有一項明確缺口：`Questionnaire/tcr-breast-longform.version` 目前是 `4.0.1`，與 FHIR R4 版本相同，但沒有權威 TCR 表單版本來源。依 FHIR R4 [`Questionnaire.version`](https://hl7.org/fhir/R4/questionnaire-definitions.html#Questionnaire.version) 定義，這是表單本身由作者管理的 business version；因此目前只能標示為 ambiguous，RC-08 business-version provenance gate 為 blocked。不能直接把它改成推測的年份或版號。

## 每一筆資料應比對的內容

任何會改變 initial population、denominator、exclusion、numerator 或 stratifier 的欄位，都必須逐筆保存並比對：

| 面向 | 必要內容 | 通過標準 |
|---|---|---|
| 來源身分 | 系統、table/column 或 API path、資料字典版本、來源 owner | 正式範圍 100%，不得只寫報表欄名 |
| 資料語意 | 型別、cardinality、允許值、缺值原因、日期／時區、單位、laterality | 每一種值與缺值皆能無歧義解釋 |
| FHIR 投影 | Resource、Profile、element path、reference、slice、cardinality | Validator／Publisher 通過，且與來源語意一致 |
| 術語 | system、version、code、display、ValueSet、ConceptMap relationship | 使用碼 100% 可解析；正式值集不得為空 |
| 轉換 | normalize、derive、filter、loss classification、round-trip policy | 每個有損步驟均具名核准；不得默默預設未知值 |
| Provenance | 原值、轉後值、來源時間、轉換程式版本、操作者 | 可由任一報表數字回溯到原始 fact |
| 人工處理 | override 前後值、理由、操作者、時間、適用 Measure | 100% 留痕；不能覆寫原始事實 |
| 計算結果 | 每案 population membership 與 stratum，最後才是 aggregate | 逐案差異 0；總數相同但成員不同仍算失敗 |

目前各館報表只可填在 `secondary/reconciliation source`，可用來找欄位、建立人工 truth set 和比對輸出；不能取代原始 source evidence，也不能由報表值反推 canonical FHIR fact。

## 20 個 Measure 的目前判定

機器可讀的逐項結果位於 [`mappings/publication/case-management-measure-audit.csv`](mappings/publication/case-management-measure-audit.csv)。共同結果如下：

- FHIR conformance：20/20 pass。
- CQL 合成執行：20/20 pass，但 QR-04 是「完整 cohort 已提供」時的條件測試，QR-05 是 candidate 規則測試。
- 原始來源 mapping 完成：0/20。
- 獨立重算完成：0/20。
- 真實 golden cohort 完成：0/20。
- Measure 規格具名核准完成：0/20。
- 可供院內臨床／品管正式發布：0/20。

RC-07 要求每個 Measure 同時滿足兩件事：approval register 有 `approve`、signer、組織／職稱、ISO 日期、證據 URI 與 64 位 SHA-256；Measure audit 的 `draft_definition_alignment` 也必須是 `approved`。因此不能用空泛簽名接受仍標為 `known-incomplete`、`candidate` 或 `contradiction` 的規格。

### 已知會直接改變結果的特定缺口

| Measure | 判定 | 不能發布的精確原因 |
|---|---|---|
| QI-03 | known incomplete | 定義要求臨床標靶體積劑量 ≥4000 cGy；目前沒有 dose source/profile，現行 CQL 只證明做過 RT，結果是上界而非正式分子。 |
| QI-04 | definition/data open | 有一筆歷史分母案例與手術欄位衝突；HER2 IHC／ISH 又被手填 subtype 代理。 |
| QI-06 | definition open | 定義原文是「年齡 ≥70 且 N0」排除，歷年實作是兩個獨立排除；兩者結果不同，不能由開發者決定。 |
| QR-02 | governance open | `Organization.partOf` 的臺大體系根節點尚未由 master-data owner 核准。 |
| QR-04 | data-contract blocked | 單期匯出沒有前一年 cohort 與完整最後聯繫歷史，無法建立正確分母／分子。 |
| QR-05 | candidate only | 拒絕／中斷事件、治療意圖與何種後續治療算「重返」仍需 owner adjudication 與 truth set。 |
| QR-17 | specification contradiction | 來源說 27 種拼法歸為 11 群，但現行 criteria/CQL 只列 10 群；第 11 群未被任何權威資料說明。 |

其他 Measure 並非已證明正確；它們只是目前沒有額外已知矛盾，仍共同缺少原始 mapping、術語、獨立重算與 golden cohort。

## 規格正確性的發布判詞

發布時只能使用與證據相符的判詞：

| 判詞 | 目前是否成立 | 意義 |
|---|---:|---|
| FHIR R4 技術草稿可重現建置 | 是 | 資源能產生、驗證、連結與打包。 |
| Draft CQL 可計算且合成案例符合預期 | 是 | 證明程式按目前寫下的規則運作。 |
| 臨床定義已由權責單位核准 | 否 | 尚有定義矛盾、candidate terminology 與待簽核事項。 |
| 真實資料產出的指標正確 | 否 | 無原始資料 mapping 與完整期別 golden cohort。 |
| 跨院可互通 | 否 | 無第二個獨立 adapter／實作者與跨院 terminology/workflow 驗證。 |
| 正式申報可接受 | 否 | 無接收端／VPN 回執及全部治理、隱私與發布核准。 |

綠色 CI 只能支持前兩個判詞，不能支持後四個。

本表主要深入個管品管／季報 Measure。整份 repository 其他 Task 與外部標準的獨立判定見 [IG_SCOPE_CONFORMANCE_AUDIT.md](IG_SCOPE_CONFORMANCE_AUDIT.md)；任一 Task 的證據不得外推成另一個 Task 或 whole-IG conformance。
