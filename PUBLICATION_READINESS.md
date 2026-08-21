# 發布就緒稽核（2026-08-21）

目前結論：本專案已達到「可重現建置的社群草稿」階段，但尚未達到可正式發布或投入臨床／申報使用的門檻。

全 IG publication scope gate 目前也是 blocked：10 個固定 scope（3 normative、6 informative、1 excluded）尚有 **0/10** 完成人工簽核。RC-08 要求全部 scope 的角色與宣稱邊界均具名核准，且 QBC 與個管品管／季報兩個 normative Task 必須達 `formal-release-ready`；單一 Task 通過或 operational approvals 完成，不能代表 whole IG 可正式發布。

逐 artifact conformance audit 已完整納入 46 個 StructureDefinition（33 Profile＋13 Extension，包含 4 個手寫 TCR extension）。46/46 的 generated parent/type/kind/status 與合成範例證據一致，但人工規格核准是 0/46，因此目前只能支持「technical structure with synthetic examples」，不能支持臨床語意或正式規格正確性的宣稱。

完整 terminology audit 已納入 152 個 artifact（60 CodeSystem＋90 ValueSet＋2 ConceptMap），技術完整性通過。個管臨床 terminology gate 仍 blocked：19 個 ValueSet 為空且核准 0/19；其中 18 個被 CQL 引用，1 個腋下淋巴結廓清術值集僅定義未引用。這些空值集是刻意的 fail-closed 狀態，必須取得權威版本、完整代碼內容、測試與具名核准後才能解除，不能由現有報表反推補值。

完整 FHIR resource manifest 也已鎖定：260 個 resources＝224 definitions＋36 synthetic examples，其中 222 個具有 canonical URL；來源分為 157 個 FSH 生成與 103 個手寫 JSON。260 個 type/id 與 ImplementationGuide 的 259 個 resource references 已逐項一致，並修正 TCR abstraction Task 被錯列為 definition。技術 inventory gate 通過，但 canonical business-version 政策尚未通過：24 個明確 package-version、1 個 CQL-version、96 個 package-context policy pending、101 個手寫 TCR resources 使用與 FHIR 版本碰撞且無來源證據的 `4.0.1`；四組目前核准 **0/4**，所以 provenance gate 仍 blocked。

完整 reference graph 技術 gate 亦已通過：精確鎖定 994 個 edge＝633 個本地 URL link＋326 個 FHIR Reference＋35 個外部 canonical。本地 190 個唯一 target 全部解析且型別相符；外部只允許 18 個已審 canonical URL，依賴固定為 FHIR R4 `4.0.1` 與 TW Core `1.0.0`。這只證明結構引用閉合，不會解除原始資料、臨床語意或版本治理阻擋。

技術面的 FHIR Publisher 資源驗證已由最初的 69 errors 降至 0 errors；完整網站目前為 0 errors、52 warnings、0 broken links。原本 133 個逐資源 missing-OID warnings 與 48 個錯誤 TCR targetless ConceptMap warnings 已歸零；271 筆 OID assignment 保留既有識別碼（包含 48 個已退役資源，不回收重用），尚有 1 個 OID root registry governance warning。臨床面的原始資料 mapping、正式值集、golden cohort 與治理簽核仍是阻擋項目。

精確的發布層級、六種核對方法與逐項通過門檻見 [PUBLICATION_ACCEPTANCE_MATRIX.md](PUBLICATION_ACCEPTANCE_MATRIX.md)。20 個個管品質／季報 Measure 的逐項規格判定、六層資料驗證與八項正式發布控制，見 [SPECIFICATION_CORRECTNESS_AUDIT.md](SPECIFICATION_CORRECTNESS_AUDIT.md)。整份 IG 各 Task 與 TW Core／mCODE／ICHOM／TWPAS 等外部規格的宣稱邊界，見 [IG_SCOPE_CONFORMANCE_AUDIT.md](IG_SCOPE_CONFORMANCE_AUDIT.md)。

## 本次驗證結果

| Gate | 結果 | 說明 |
|---|---:|---|
| pytest | pass：323 tests | 包含 mapping、PHI、CQL、IG export、OID assignment、TCR 術語 backlog、Publisher warning policy、完整 260-resource manifest、994-edge reference graph、52-fact 原始來源與 20-Measure 真實資料證據 gate、四組 canonical version policy、逐 Measure、46 個 StructureDefinition 與 152 個 terminology artifact 的規格／簽核完整性 audit、全 IG scope claims／決策、完整 release-control gate、template supply-chain 與 publication workflow 契約測試。 |
| SUSHI 3.20.0 | pass：0 errors / 0 warnings | FSH 可穩定產生 IG resources。 |
| PHI gate | pass | 目前版本庫未檢出疑似病人識別資料；正式來源資料仍須在受控環境處理。 |
| CQL CLI translation | pass | `cql-to-elm-cli 3.26.0` 可產生 ELM；FHIRHelpers 由 `hl7.fhir.uv.cql#2.0.0` 解析。 |
| CQL runtime smoke | pass：20/20 Measures、46/46 criteria | 每個 Measure 所引用的 population／stratifier expression 均已在 ELM engine 執行；這只證明可執行性。 |
| CQL branch assertions | pass with clinical limitations：20/20 Measures | 全部 Measure 已通過具預期結果的合成 R4 Bundle 分支案例；分布 Measure 另覆蓋全部列舉 strata、月份、年齡帶、缺值與非法值。QR-04 仍受真實前年度 cohort 阻擋，QR-05 仍是候選規則。 |
| IG Publisher 2.3.2 resource validation | pass with warnings：0 errors / 52 warnings | missing-OID 與 TCR targetless ConceptMap warnings 均為 0；剩餘 40 個 FHIRHelpers anchor、11 個 CQL validator limitation 與 1 個 OID registry warning 由機器可讀政策逐類鎖定。 |
| 完整 IG website/package | pass：0 errors / 52 warnings / 0 broken links | Linux Publisher 2.3.2 已產生網站、`qa.html` 與 `package.tgz`；warning audit 為 QA integrity pass，Community Preview／Formal release block。 |
| 完整 release controls | integrity pass；2/8 controls pass | RC-02 FHIR conformance 與 RC-04 executable rules 通過；source mapping、terminology、independent recalculation、golden cohort、governance 與 operational acceptance 均 blocked。RC-07 鎖定 QBC 14-Gate、Measure 20-approval 與 StructureDefinition 46-approval 完整集合；目前 Measure 0/20、artifact 0/46。Publisher warnings 即使歸零也不會讓此 gate 誤判通過。 |
| Terminology inventory | technical pass；clinical block | 完整集合 152（60 CodeSystem、90 ValueSet、2 ConceptMap）；19 個個管臨床 ValueSet 為空、核准 0/19，因此 RC-03 blocked。 |
| FHIR resource inventory | technical pass；version provenance block | 精確集合 260（224 definitions、36 examples、222 canonical）；259 個 IG manifest references 全數解析。222 canonical 已分成 24 package-explicit、1 CQL、96 package-context pending、101 TCR version collision；政策核准 0/4，因此 RC-08 blocked。 |
| FHIR reference graph | technical pass | 精確 994 edges：633 local URL、326 FHIR Reference、35 external canonical；190 unique local targets 全部解析且型別正確，18 unique external canonical 只由 pinned FHIR R4／TW Core dependencies 解析。 |
| Strict release QA | blocked | 正式 release gate 仍要求 0 warnings；完整 QA 的 52 個 warning 尚未逐一修正或完成具體審查紀錄。 |
| Template supply-chain | technical pass | 已依 2026-03 安全公告固定使用 `fhir2.base.template#0.1.0` 與套件 SHA-1；CI 證明載入精確版本且不再出現 insecure-template notice。已發布模板的多語系 jurisdiction flag 路徑缺陷以最小 include overlay 修正並由 0 broken links gate 鎖定；此項通過不解除臨床／治理發布阻擋。 |

## 目前可以做什麼

- 繼續撰寫 CQL 的結構、共同函式、資料需求與合成測試。
- 使用報表作為 secondary source、reconciliation copy 或欄位盤點依據。
- 建立 mapping table 的骨架、來源責任欄位與待確認狀態。
- 透過 CI 重現 SUSHI、CQL、Publisher 與測試結果。

目前不能把報表欄位直接宣告為原始事實，也不能因現有系統能輸出報表，就反向假設其欄位已對應到可信任的 canonical FHIR 資料。正確資料流應為：

`raw source element -> source adapter + Provenance -> canonical FHIR fact -> task projection -> report`

## 阻擋正式使用的項目

1. **原始資料 mapping**：每個指標輸入都要有來源系統、table/column 或 API element、型別、時間語意、單位、缺值規則、轉換規則、Provenance、owner 與 reviewer。
2. **正式 terminology**：19 個臨床 ValueSet 目前刻意保持空白，避免把未確認的代碼當成正式值集；2,169 個 TCR code 的標準術語對應維持 `not-started` backlog，未完成 target、relationship、reviewer 與 evidence 前不得發布為 ConceptMap。
3. **Measure 可執行性與規格核准**：20 個 Measure 均有具預期值的合成分支測試，但逐項規格具名核准仍為 0/20；QR-04 尚需真實前年度 cohort，QR-05 尚需人工 truth set，QR-17 的來源文件「11 組」與目前 criteria/CQL「10 組」仍須由報表 owner 裁決。
4. **資料正確性**：需要由原始資料建立 golden cohort，逐案比對 FHIR fact、population membership、分子、分母、排除與分層結果。
5. **人工作業與治理**：手動補登、報表匯出、VPN 送件、回執與 reconciliation 必須有明確 ownership、稽核軌跡與簽核。
6. **發布供應鏈**：完整 Publisher/Jekyll build、0 broken links、warning disposition、template security 與 package metadata 均須有 CI 證據。

## Mapping table 現階段的建立方式

如果尚未取得原始資料，mapping table 可以先建立，但只能填到「需求與待查證」層級：

- 每列以一個 canonical clinical fact 或品質指標輸入為單位。
- 報表欄位記為 `secondary/reconciliation source`，不可標成 authoritative source。
- 原始欄位未知時，明確填入 `blocking-data-gap`，並記錄應向哪個系統 owner 查詢。
- terminology 對應未確認時使用 `candidate-unverified`，不得直接發布成正式 ValueSet/ConceptMap 關係。
- 先完成 CQL 所需的 FHIR resource/profile/path、時間窗、缺值與排除規則；待原始資料到位後再補 source adapter 與 Provenance。

本階段骨架已建立於 `mappings/publication/source-traceability-register.csv`：精確涵蓋 34 個共同 fact 與 18 個 task-only fact，共 52 項；目前權威來源核准為 0/52。各館既有報表欄位已明確留在 notes／secondary reconciliation 邊界，不能使原始來源 gate 通過。逐 Measure 的獨立重算與完整期別驗證則記錄於 `measure-validation-evidence-register.csv`，目前均為 0/20。兩份登錄由 `audit_data_correctness_evidence.py` 在本機與 CI 強制檢查。

quality 交接匯入包本身已完成逐檔整合核對：11 個直接對應檔及 2 個 instruction／patch 檔均有處理結論，34 mapping、20 Measure、68 criteria、18 Task-only IDs 與 22 個 FSH symbols 無遺漏；完整證據見 [QUALITY_IMPORT_INTEGRATION_AUDIT.md](QUALITY_IMPORT_INTEGRATION_AUDIT.md)。這只證明匯入完整，不提升真實資料 gate。

## 下一個可驗收里程碑

Preview 技術候選版至少需要：

- 遠端完整 Publisher build 已成功；後續每個候選 commit 仍須產出可下載的網站、`qa.html` 與 `package.tgz`。
- `qa.html` 為 0 errors、0 broken links；每個 warning 修正或有具體理由、影響、owner 與核准紀錄。
- 20/20 Measures 皆有 ELM translation 與可執行合成測試。
- 取得至少一批去識別原始資料，完成一個端到端 source-to-FHIR-to-CQL golden cohort。

正式臨床／申報使用仍需再完成全部 source mapping、正式 terminology、跨院驗證與治理簽核。
