# v0.1.0-alpha.1

乳癌 FHIR Implementation Guide 社群草稿，FHIR package version 為 `1.0.0-preview.1`。本版本整合乳癌共同資料層、癌症診療計畫書、QBC／P4P 品管與季報、TCR 與 TWPAS 等平行 Task；它不是衛福部、健保署、HL7 或 ICHOM 的正式出版品。

## 本版重點

- 以 TW Core IG 1.0.0 為基礎，提供 Patient、Condition、Observation、DiagnosticReport、Procedure、MedicationRequest 與 Task 等共用模型。
- 將報表定位為 secondary/reconciliation source；目標資料流為原始來源到 canonical FHIR，再投影至 Task 與報表。
- 建立 20 個乳癌個案管理品質 Measure 草稿與共同 CQL Library。
- 20/20 Measure 的 46 個 population／stratifier criteria 已完成 ELM runtime smoke 與具預期值的合成分支測試；分布 Measure 另覆蓋全部列舉 strata、12 個月份、10 個年齡帶、缺值與非法值。QR-04 是須載入前年度 cohort 才可運算的條件測試，QR-05 仍是待人工逐案核對的候選規則。
- FHIRHelpers 改由 `hl7.fhir.uv.cql#2.0.0` 的正式 namespace 與 package artifact 解析。
- CRMI dependency 已升級為 `hl7.fhir.uv.crmi#2.0.0`，並通過完整建置與 CQL regression checks。
- TCR ValueSet 與 ConceptMap 補齊 shareable metadata，但不主張尚未審查的標準術語等價關係。
- 為先前缺少範例的 4 個 Profile 與 1 個 Extension 加入 HTEST 合成正／負例。
- 新增完整 IG Publisher 遠端驗證流程，固定 Publisher 2.3.2、安裝 Jekyll 並保存網站及 QA 證據。

## 驗證狀態（2026-08-21）

- pytest：307 passed（新增 OID assignment、TCR 術語 backlog、完整 260-resource manifest、四組 canonical version policy、逐 Measure、46 個 StructureDefinition 與 152 個 terminology artifact 的規格／簽核完整性、全 IG scope claims／決策、template supply-chain 與八項 release-control 證據一致性檢查）。
- SUSHI 3.20.0：0 errors、0 warnings。
- PHI gate：pass。
- CQL translation：pass；runtime smoke：20/20 Measures、46/46 criteria；目前具預期值的合成分支 assertions：20/20 Measures。
- IG Publisher resource validation：0 errors、52 warnings；133 個逐資源 missing-OID 與 48 個錯誤 TCR targetless ConceptMap warnings 已歸零，剩餘 1 個 OID registry governance warning。
- 完整網站、`qa.html` 與 `package.tgz`：0 errors、52 warnings、0 broken links；warning audit 判定 QA integrity pass、Community Preview／Formal release block。
- Template supply-chain：已依 2026-03 安全公告遷移至固定版本 `fhir2.base.template#0.1.0`；精確套件載入、無 insecure-template notice，並以最小 include overlay 修正該版已知多語系 jurisdiction flag 路徑缺陷。
- Strict release：blocked；仍要求 0 warnings、完整 warning disposition 與其餘正式發布控制通過；模板安全阻擋已解除，但不取代原始資料、術語、golden cohort 與治理證據。
- 完整 formal release gate 與 Publisher QA gate 已分離；目前只有 2/8 controls 通過，warnings 歸零也不能繞過 source mapping、terminology、獨立重算、golden cohort 與簽核。
- 新增 20/20 Measure 規格決策登錄；RC-07 現在同時要求完整 QBC 14-Gate、完整 Measure 20-approval、有效簽署證據及 `draft_definition_alignment=approved`，避免刪除待辦或簽署未解決規格而誤過正式發布。
- 新增 10/10 whole-IG scope 角色決策登錄；目前 0/10 簽核。RC-08 現在鎖定 3 normative、6 informative、1 excluded，並要求 normative Task 達 `formal-release-ready`，避免單一 Task 或 operational approval 被擴張成整份 IG 可正式發布。
- 新增 46/46 StructureDefinition conformance register 與機器稽核（33 Profile、13 Extension，包含 4 個非 FSH 的 TCR extension）；逐列驗證 parent、type、kind、draft/experimental 及合成範例。技術證據 46/46 pass，人工規格核准 0/46；RC-07 現在也要求這 46 項全部具名簽核。
- 新增完整 terminology conformance audit：鎖定 152 個 artifact（60 CodeSystem、90 ValueSet、2 ConceptMap）並驗證 canonical、內容、參照與 CQL 使用狀態。完整清冊技術檢查通過；19 個個管臨床 ValueSet 仍為空、核准 0/19（18 個被 CQL 引用、1 個 defined-not-referenced），因此 RC-03 維持 blocked。
- 新增精確 260-row FHIR resource inventory 與 IG manifest graph audit：224 definitions、36 synthetic examples、222 canonical resources，來源為 157 FSH-generated＋103 manual JSON；259 個 IG resource references 必須逐項解析。修正 TCR abstraction Task 被誤標為 definition。另新增完整 canonical version policy register：222 項分為 24 package-explicit、1 CQL、96 package-context pending、101 手寫 TCR version collision；四組政策均須具名簽核，目前 0/4，因此 RC-08 保持 blocked，不能只修正一個 Questionnaire 或擅自猜版本。
- QBC mapping 重建改以 committed `qbc_fields.json` 技術擷取契約為輸入，乾淨 checkout 不再依賴未納入版本庫的 DOCX；115 列仍保留原始文件 SHA-256。重建器只有在 Gate 提案、owner 與驗收條件完全未變時才保留既有人工簽核，內容變更即失效重簽。
- 新增 whole-IG claim register，分開判定 TW Core direct parent、mCODE／ICHOM semantic reference、Care Plan、QBC、TWPAS、個管 Measure 與 TCR；修正 TCR 缺口為 48 欄已驗證碼表、32 欄 pending、19 欄非 coded。
- 新增 canonical-derived UUIDv5 OID root 與 271 筆 committed assignments；逐資源 OID warning 由 133 降為 0，root registry 登錄仍待治理。
- 退役 48 個以 `unmatched` 誤表達「尚未審查」的 TCR ConceptMap；改以 2,169 列非 FHIR 清冊逐碼記錄待審 target、relationship、reviewer 與 evidence，已配置的 OID 保留且不重用。

## 使用限制

本版僅供設計、互通測試與技術討論。以下事項尚未完成：

- 原始來源欄位到 canonical FHIR 的完整 mapping 與 Provenance。
- 19 個臨床 ValueSet 的正式內容與 terminology review。
- 尚餘原始資料 golden cohort、QR-04 前年度 cohort、QR-05 人工 adjudication、QR-17 分群數規格釐清、正式 terminology 與跨院一致性驗證；合成測試通過不得取代這些證據。
- QBC／P4P、TCR、TWPAS 的在地流程、VPN、回執、reconciliation 與治理簽核。

因此不得將此 alpha 版本宣稱為正式臨床決策、品質申報或主管機關認證成果。完整門檻與阻擋項目見 [PUBLICATION_READINESS.md](PUBLICATION_READINESS.md)，逐 Measure 判定見 [SPECIFICATION_CORRECTNESS_AUDIT.md](SPECIFICATION_CORRECTNESS_AUDIT.md)。
