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

- pytest：253 passed（新增逐 Measure 規格、全 IG scope claims 與八項 release-control 證據一致性檢查）。
- SUSHI 3.20.0：0 errors、0 warnings。
- PHI gate：pass。
- CQL translation：pass；runtime smoke：20/20 Measures、46/46 criteria；目前具預期值的合成分支 assertions：20/20 Measures。
- IG Publisher resource validation：0 errors、232 warnings。
- 完整網站、`qa.html` 與 `package.tgz`：遠端 run `32420689838` 已通過，0 errors、232 warnings、0 broken links；warning audit 判定 QA integrity pass、Community Preview／Formal release block。一般 Build run `32420689847` 亦完整通過。
- Strict release：blocked；仍要求 0 warnings、0 broken links，且 Publisher 已指出 `fhir.base.template#1.0.0` 的供應鏈安全問題。
- 完整 formal release gate 與 Publisher QA gate 已分離；目前只有 2/8 controls 通過，warnings 歸零也不能繞過 source mapping、terminology、獨立重算、golden cohort 與簽核。
- 新增 whole-IG claim register，分開判定 TW Core direct parent、mCODE／ICHOM semantic reference、Care Plan、QBC、TWPAS、個管 Measure 與 TCR；修正 TCR 缺口為 48 欄已驗證碼表、32 欄 pending、19 欄非 coded。

## 使用限制

本版僅供設計、互通測試與技術討論。以下事項尚未完成：

- 原始來源欄位到 canonical FHIR 的完整 mapping 與 Provenance。
- 19 個臨床 ValueSet 的正式內容與 terminology review。
- 尚餘原始資料 golden cohort、QR-04 前年度 cohort、QR-05 人工 adjudication、QR-17 分群數規格釐清、正式 terminology 與跨院一致性驗證；合成測試通過不得取代這些證據。
- QBC／P4P、TCR、TWPAS 的在地流程、VPN、回執、reconciliation 與治理簽核。

因此不得將此 alpha 版本宣稱為正式臨床決策、品質申報或主管機關認證成果。完整門檻與阻擋項目見 [PUBLICATION_READINESS.md](PUBLICATION_READINESS.md)，逐 Measure 判定見 [SPECIFICATION_CORRECTNESS_AUDIT.md](SPECIFICATION_CORRECTNESS_AUDIT.md)。
