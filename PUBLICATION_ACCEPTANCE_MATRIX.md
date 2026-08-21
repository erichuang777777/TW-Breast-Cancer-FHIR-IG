# FHIR IG 發布與資料正確性驗收矩陣

本文件把「程式能建置」、「可公開社群 Preview」與「可供院內品管／季報使用」分開。任何一層通過都不能替代下一層的證據。

## 目前判定

| 層級 | 目前結果 | 尚缺證據 |
|---|---:|---|
| 原始碼／研究草稿 | pass | 必須持續標示 `draft`、`experimental`、非官方及非臨床用途。 |
| 可重現技術建置 | pass | Publisher 2.3.2：0 errors、52 warnings、0 broken links；一般 CI 與 artifact 均已留存。 |
| 社群 Preview 發布 | block | 缺範例、CRMI dependency、missing-OID 與 TCR targetless ConceptMap 四類已歸零；其餘 3 類 Publisher warning 尚未完成具名、限期核准。 |
| Computable Measure Preview | block | 20/20 Measure、46 個 criteria 已完成 ELM runtime smoke 與合成分支測試；但 20/20 Measure 規格決策仍待具名核准，QR-04／QR-05 仍有資料與人工 adjudication 限制、QR-17 分群數尚有規格矛盾，且 19 個臨床 ValueSet 為空。 |
| 院內品管／季報 | block | 缺原始來源 mapping、正式 terminology、完整 reporting-period cohort、golden cohort 與逐案 reconciliation。 |
| 跨院／正式申報 | block | 除上述項目外，仍缺跨實作驗證、在地治理、VPN／接收端回執與主管機關規則確認。 |

## 必須使用的六種資料正確性核對方法

高風險資料與所有會改變分母、分子、排除或分層的欄位，六種方法必須全部通過。單純顯示欄位可依風險降低執行範圍，但不得省略來源追溯與 FHIR conformance。

| # | 核對方法 | 比對單位 | 通過門檻 | 權威證據 |
|---:|---|---|---|---|
| 1 | 原始來源逐欄追溯 | 每個 source element | 100% 有來源系統、table/column 或 API path、版本、型別、時間語意、單位、缺值與轉換規則；報表只能列 secondary source。 | 原始 schema／data dictionary、版本雜湊、source owner 簽核。 |
| 2 | FHIR 結構與語意驗證 | 每個 Profile／resource／reference | SUSHI 0 errors/0 warnings；Publisher 0 errors/0 broken links；cardinality、binding、invariant、reference 與 slicing 全部通過。 | SUSHI log、Publisher `qa.html`、FHIR Validator／Publisher artifact。 |
| 3 | 術語核對 | 每個 system/code/display/ValueSet/ConceptMap | 使用中的代碼 100% 可由指定版本解析；ValueSet expansion 可重現；不得有空的正式臨床 ValueSet、`candidate-unverified` 或未核准 equivalence。 | 官方 terminology package/service、版本化 expansion、terminologist 雙人審查。 |
| 4 | 可執行規則測試 | 每個 Measure expression | 20/20 Measure 均實際執行；每個至少覆蓋 positive、negative、exclusion、missing、boundary，另依規則加入多事件、時間窗與 laterality 案例；預期與實際 100% 一致。 | CQL→ELM log、合成 Bundle、逐案 population 結果、MeasureReport fixture。 |
| 5 | 獨立重算 | 每一個 golden case 的每個 population | CQL 與獨立參考實作逐案 membership 完全一致；不能只比總數。所有差異必須為 0，或有具名 reviewer、理由與版本化核准。 | 獨立實作輸出、逐案 diff、鎖定的測試資料與程式 SHA-256。 |
| 6 | 原始資料端到端 golden cohort | 原始列／事件到最終報表 | 由原始資料產生 FHIR，再計算 MeasureReport／報表；100% 個案逐案核對來源 fact、分母、分子、排除、stratum 與人工 override。零個未解釋差異。 | 去識別原始資料、Provenance、人工 truth set、輸出報表、接收端 receipt／reconciliation。 |

這六種方法不是「六選一」。對 Measure 輸入與臨床 mapping 而言，它們是由來源到輸出的六層連續證據。

若要由資料正確性進一步宣稱「正式發布」，還必須增加兩個 release control：具名的臨床／術語／資料治理簽核，以及隱私、資安、版本、artifact、接收端回執與跨院實作驗收。因此數字正確性是六層，正式發布合計是八項控制。逐 Measure 判定見 [FHIR IG 規格正確性稽核](SPECIFICATION_CORRECTNESS_AUDIT.md)。

八項控制的宣告狀態位於 `mappings/publication/release-control-register.csv`，20 個 Measure 的逐項規格決策位於 `mappings/publication/case-management-measure-approval-register.csv`。CI 會用 `scripts/audit_release_controls.py` 從底層證據重新推導，並要求 QBC 14 個 Gate 與 Measure 20 個 approval ID 都是完整且不重複的集合；刪除待核准項目不能讓 gate 變綠。Publisher formal QA 與完整 formal release 是兩個不同 gate，前者通過不得取代後者。

RC-08 也要求 `ig-scope-claim-register.csv` 與 `publication-scope-decision-register.csv` 精確涵蓋同一組 10 個 claim。三個 normative scope（IG core、QBC、個管品管／季報）、六個 informative scope 與一個 excluded scope 的角色已鎖定；現況 0/10 簽核。即使 operational approvals 已簽署，只要任一 scope 尚未簽核或 normative Task 未達 `formal-release-ready`，完整 formal release 仍為 blocked。

RC-07 另要求 `artifact-conformance-register.csv` 精確涵蓋全部 **46 個 StructureDefinition（33 Profile、13 Extension）**。`scripts/audit_artifact_conformance.py` 會把 FSH 產物與 4 個手寫 TCR extension 一起比對 parent canonical、FHIR type/kind、draft/experimental 狀態及合成範例使用證據。現況技術一致性為 46/46，但人工規格核准為 0/46；Publisher 綠燈不能替代這 46 項核准。

RC-03 的 terminology 範圍也已鎖定為生成後與手寫資源的完整聯集：**152 個 terminology artifact（60 CodeSystem、90 ValueSet、2 ConceptMap）**。`scripts/audit_terminology_conformance.py` 逐項檢查 canonical、draft/experimental、CodeSystem 內容、ValueSet include system、ConceptMap element/target，以及 CQL 宣告與實際引用。完整清冊的技術完整性目前通過；但 19 個個管臨床 ValueSet 仍為空，18 個被 CQL 實際引用，另 1 個腋下淋巴結廓清術值集僅定義而未引用。`case-management-terminology-approval-register.csv` 鎖定這 19 項，現況核准 **0/19**，因此 RC-03 必須維持 blocked。這項技術盤點不等於 152 項均已取得臨床語意核准。

RC-02 現在另以 `fhir-resource-inventory.csv` 鎖定生成後完整集合：**260 個 FHIR resources、224 個 publication definitions、36 個 synthetic examples、222 個 canonical resources**；來源為 157 個 FSH 生成資源與 103 個手寫 JSON。`scripts/audit_fhir_resource_inventory.py` 要求 260 個 type/id 與 259 個 `ImplementationGuide.definition.resource` reference 精確一致，並核對 example／definition 標記、canonical 唯一性、CapabilityStatement supportedProfile、20 Measure 到 CQL Library 的引用及 NamingSystem URI。此次稽核也修正 `Task/tcr-breast-abstraction-example` 被誤標為 definition 的問題。

資源存在不代表引用正確，因此 RC-02 另鎖定完整 reference graph：共 **994 個 edge**，包含 633 次本地 URL 連結、326 次 `Reference.reference` 與 35 次外部 canonical。633 次本地連結再分為 219 canonical fields、240 extension uses、138 CodeSystem uses、19 Bundle fullUrls、13 fixed extension URLs、2 NamingSystem uses、2 ConceptMap CodeSystem uses；190 個唯一的本地 URL target 全部可解析且目標 resource type 正確。326 次 FHIR Reference 包含 259 個 IG manifest references 與 67 個臨床／範例資源 references，全部可解析。35 次外部 canonical 只允許 18 個已審 URL，並由 FHIR R4 `4.0.1`（33 次）與 TW Core `1.0.0`（2 次）固定依賴解析。這證明引用圖技術閉合，不證明每一條臨床關係在真實資料上語意正確。

RC-08 進一步要求全部 222 個 canonical resources 的 business-version provenance，而不是只看 package version 或單一 Questionnaire。機器稽核把完整集合鎖成四個互斥群組：24 個明確使用 package version、1 個 CQL Library 使用 CQL lifecycle version、96 個生成資源目前只隱含於 package context、101 個手寫 TCR canonical resources 皆填入 `4.0.1`。後一數值與 FHIR R4 版本碰撞，但缺少 TCR 表單／手冊／碼表的權威版本證據；依 FHIR R4 的 [`Questionnaire.version`](https://hl7.org/fhir/R4/questionnaire-definitions.html#Questionnaire.version) 等 canonical resource version 定義，resource `version` 是內容的 business version，不是 `fhirVersion`。四組政策登錄於 `canonical-version-policy-register.csv`，目前 **0/4** 完成具名簽核，因此 gate blocked。這是語意／治理阻擋，不是 Publisher 結構錯誤；取得權威來源後須決定 96 項是否接受 package-context-only policy，並為 101 項填入或明確繼承真正的來源版本及證據，不得猜值。

## 數量與正確性門檻

### Mapping

- 可重現重建使用 committed、版本化且帶原始文件 SHA-256 的 `qbc_workbench/data/qbc_fields.json`；它是來源文件的技術擷取契約，不是原始文件本身。受控環境仍須以該 SHA-256 重新核對原始 DOCX，不能因衍生 JSON 可重建就宣稱原始規格已驗真。
- 正式使用範圍內的 required facts：100% 完成來源與 FHIR mapping。
- `blocking-data-gap`：0。
- `candidate-unverified`：0。
- 每一個有損轉換均要標記 loss classification，並有 reviewer 決定是否可接受。
- 每一個人工補登／覆寫都必須保存原值、新值、理由、操作者、時間與適用 Measure。

### Measure 與測試

- Translation、runtime smoke 與具預期值的合成分支驗證均已達 20/20 Measure、46/46 criteria；分布 Measure 另驗證全部列舉 strata、月份、年齡帶、缺值與非法值。QR-04 只證明 cohort 已載入時的條件行為，QR-05 只證明候選規則的機械行為，兩者都不構成真實資料正確性證據。
- Measure 規格核准目前為 0/20；每一項都必須保存具名 signer、組織／職稱、決定日期、證據 URI 與被簽 artifact 的 SHA-256，且 `draft_definition_alignment` 必須明確為 `approved`。只有簽名欄位或只有綠色 CQL 測試都不足以通過 RC-07。
- 每個 Measure 的測試數不以任意固定樣本數取代 coverage。最低要求是所有 truth-table branch、排除、缺值、邊界、日期邊界及多筆事件行為全部有案例。
- Golden cohort 要鎖版並逐案核對 100%，允許的未解釋差異為 0。
- 若要主張跨院可實作，至少需兩個彼此獨立的 source adapter／實作者完成同一套 conformance 與 golden tests；否則只能宣稱單一環境驗證。

### Publisher warnings

最新 52 warnings 的精確基線為：

| 類別 | 數量 | 現況 |
|---|---:|---|
| 逐資源 OID 缺漏 | 0 | 以 canonical URL 決定性產生 UUIDv5 `2.25` root，並固定 271 筆 `oids.ini` assignment；不得回歸。 |
| OID root registry | 1 | root 尚未登錄 FHIR `ig-registry/oid-assignments.json`；正式發布前仍須完成外部治理。 |
| TCR ConceptMap 無 target system | 0 | 未審查不等於 `unmatched`；48 個錯誤骨架已退役，2,169 個 source codes 改由非 FHIR backlog 逐碼追蹤。 |
| FHIRHelpers 重複 XHTML anchor | 40 | Publisher／CQL narrative tooling 問題。 |
| `text/cql-identifier` 無法由 generic validator 驗證 | 11 | 每個 expression 仍須由 CQL execution 獨立證明。 |
| Profile／extension 缺 example | 0 | 已加入合成正／負例；政策上限降為 0，防止回歸。 |
| CRMI dependency 過舊 | 0 | 已升級 `hl7.fhir.uv.crmi#2.0.0`，並通過 SUSHI、pytest、CQL CI 與完整 Publisher；政策上限降為 0。 |

機器可讀政策位於 `mappings/publication/publisher-warning-policy.csv`。每類包含上限、理由、owner、所需證據與核准欄位。`scripts/audit_publisher_qa.py` 會拒絕：

- 任一新而未分類的 warning；
- 任一 warning 同時符合多個類別；
- 任一類數量增加；
- `qa.txt` 與 `qa.html` 統計不一致；
- Publisher errors 或 broken links 不為 0。

Warning 數量下降可直接通過基線稽核；增加、改型或未核准例外不得悄悄進入下一版。正式 release 仍要求 0 warnings，除非治理程序明確修改發布政策並留下核准與期限。

## 何時可以發布

### 社群 Preview

必須同時滿足：技術建置可重現、0 errors、0 broken links、缺範例與 dependency review 項目完成；其餘 warning 每類均有具名核准、核准日、到期日與影響說明；首頁、package metadata、下載頁均一致標示限制。

### Computable Preview

除社群 Preview 外，20/20 Measure 必須完成逐項規格核准、正式 terminology 與全部合成 branch coverage。此層仍不代表院內數字正確，除非已有原始資料 golden cohort。

### 院內品管／季報

除 Computable Preview 外，正式使用範圍內的 mapping 必須 100% 完成，並至少對一個完整報告期間的所有納入個案做 source-to-FHIR-to-report 逐案 reconciliation。所有未解釋差異必須為 0。

### 跨院或正式申報

除上述門檻外，還要有至少兩個獨立實作、跨院 terminology／workflow review、資安與隱私審查，以及 VPN／接收端成功回執。若缺主管機關或院方必要核准，只能發布非官方技術草稿，不能宣稱正式可用。
