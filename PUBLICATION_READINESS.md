# 發布就緒稽核（2026-08-21）

目前結論：本專案已達到「可重現建置的社群草稿」階段，但尚未達到可正式發布或投入臨床／申報使用的門檻。

技術面的 FHIR Publisher 資源驗證已由最初的 69 errors 降至 0 errors；Linux publication-readiness workflow 亦已產生完整網站、`qa.html` 與 `package.tgz`，結果為 0 errors、232 warnings、0 broken links。臨床面的原始資料 mapping、正式值集、golden cohort 與治理簽核仍是阻擋項目。

精確的發布層級、六種核對方法與逐項通過門檻見 [PUBLICATION_ACCEPTANCE_MATRIX.md](PUBLICATION_ACCEPTANCE_MATRIX.md)。20 個個管品質／季報 Measure 的逐項規格判定、六層資料驗證與八項正式發布控制，見 [SPECIFICATION_CORRECTNESS_AUDIT.md](SPECIFICATION_CORRECTNESS_AUDIT.md)。

## 本次驗證結果

| Gate | 結果 | 說明 |
|---|---:|---|
| pytest | pass：245 tests | 包含 mapping、PHI、CQL、IG export、Publisher warning policy、逐 Measure 規格 audit、完整 release-control gate 與 publication workflow 契約測試。 |
| SUSHI 3.20.0 | pass：0 errors / 0 warnings | FSH 可穩定產生 IG resources。 |
| PHI gate | pass | 目前版本庫未檢出疑似病人識別資料；正式來源資料仍須在受控環境處理。 |
| CQL CLI translation | pass | `cql-to-elm-cli 3.26.0` 可產生 ELM；FHIRHelpers 由 `hl7.fhir.uv.cql#2.0.0` 解析。 |
| CQL runtime smoke | pass：20/20 Measures、46/46 criteria | 每個 Measure 所引用的 population／stratifier expression 均已在 ELM engine 執行；這只證明可執行性。 |
| CQL branch assertions | pass with clinical limitations：20/20 Measures | 全部 Measure 已通過具預期結果的合成 R4 Bundle 分支案例；分布 Measure 另覆蓋全部列舉 strata、月份、年齡帶、缺值與非法值。QR-04 仍受真實前年度 cohort 阻擋，QR-05 仍是候選規則。 |
| IG Publisher 2.3.2 resource validation | pass with warnings：0 errors / 232 warnings | 已消除原有錯誤，補齊 5 個缺失範例並升級 CRMI 2.0.0；其餘 warning 由機器可讀政策逐類鎖定。 |
| 完整 IG website/package | pass：0 errors / 232 warnings / 0 broken links | GitHub Actions run `32420689838` 使用 Jekyll 與 Publisher 2.3.2，已保存網站、`qa.html`、`package.tgz` 與 warning audit artifact；QA integrity pass，Community Preview／Formal release block。 |
| 完整 release controls | integrity pass；2/8 controls pass | RC-02 FHIR conformance 與 RC-04 executable rules 通過；source mapping、terminology、independent recalculation、golden cohort、governance 與 operational acceptance 均 blocked。Publisher warnings 即使歸零也不會讓此 gate 誤判通過。 |
| Strict release QA | blocked | 正式 release gate 仍要求 0 warnings；完整 QA 的 232 個 warning 尚未逐一修正或完成具體審查紀錄。 |
| Template supply-chain | blocked | Publisher 報告 `fhir.base.template#1.0.0` 已不再被視為安全；升級前不得宣告正式可發布。 |

## 目前可以做什麼

- 繼續撰寫 CQL 的結構、共同函式、資料需求與合成測試。
- 使用報表作為 secondary source、reconciliation copy 或欄位盤點依據。
- 建立 mapping table 的骨架、來源責任欄位與待確認狀態。
- 透過 CI 重現 SUSHI、CQL、Publisher 與測試結果。

目前不能把報表欄位直接宣告為原始事實，也不能因現有系統能輸出報表，就反向假設其欄位已對應到可信任的 canonical FHIR 資料。正確資料流應為：

`raw source element -> source adapter + Provenance -> canonical FHIR fact -> task projection -> report`

## 阻擋正式使用的項目

1. **原始資料 mapping**：每個指標輸入都要有來源系統、table/column 或 API element、型別、時間語意、單位、缺值規則、轉換規則、Provenance、owner 與 reviewer。
2. **正式 terminology**：19 個臨床 ValueSet 目前刻意保持空白，避免把未確認的代碼當成正式值集；TCR ConceptMap 的 unmatched 狀態也不得用虛構 target system 消除 warning。
3. **Measure 可執行性**：20 個 Measure 均有具預期值的合成分支測試；QR-04 尚需真實前年度 cohort，QR-05 尚需人工 truth set，QR-17 的來源文件「11 組」與目前 criteria/CQL「10 組」仍須由報表 owner 裁決。
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

## 下一個可驗收里程碑

Preview 技術候選版至少需要：

- 遠端完整 Publisher build 已成功；後續每個候選 commit 仍須產出可下載的網站、`qa.html` 與 `package.tgz`。
- `qa.html` 為 0 errors、0 broken links；每個 warning 修正或有具體理由、影響、owner 與核准紀錄。
- 20/20 Measures 皆有 ELM translation 與可執行合成測試。
- 取得至少一批去識別原始資料，完成一個端到端 source-to-FHIR-to-CQL golden cohort。

正式臨床／申報使用仍需再完成全部 source mapping、正式 terminology、跨院驗證與治理簽核。
