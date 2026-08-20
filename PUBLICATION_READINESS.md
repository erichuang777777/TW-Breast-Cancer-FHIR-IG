# 發布就緒稽核（2026-08-21）

本文件將「公開社群 Preview」與「正式臨床、院內報表或申報使用」分開判定。兩者不可共用同一個完成標準。

## 結論

| 發布層級 | 目前判定 | 理由 |
|---|---|---|
| 原始碼／研究草稿分享 | 可 | 已清楚標為 `draft`、`experimental`、非官方；無真實個案範例。 |
| 社群 Preview 網站與 package | 不可重新發布目前 HEAD | 完整 IG Publisher 尚有 20 errors、338 warnings；本機 Jekyll 工具鏈不完整；Publisher 警告目前 template 不再視為安全。 |
| 品管＋季報 computable draft | 部分可 | 20 個 Measure 與共用 CQL 已建立，CQL 可由兩條工具路徑翻譯；但只有 `bc-qi-01` 有真正執行測試。 |
| 正式院內品管／季報 | 不可 | 19 個臨床 ValueSet 仍是空佔位；34 筆共同層 Mapping 中 21 筆術語未驗證，9 筆為 blocking data gap；尚無原始資料到 canonical FHIR 的 golden-data 驗收。 |
| 正式 QBC／癌登／TWPAS 申報 | 不可 | 人工簽核、官方函釋、VPN／接收端驗收、術語與授權、資安治理尚未完成。 |

「可公開草稿」只代表讀者能正確理解目前設計與缺口，不代表數字正確、可互通或可送件。

## 2026-08-21 實測證據

| Gate | 結果 | 證明範圍 |
|---|---:|---|
| Git 與遠端同步 | pass（稽核起點） | 稽核起點 `b29aef0` 與遠端分支相同；本表記錄本機 gate，提交後的遠端結果以該 commit 的 CI run 為準。 |
| pytest | pass：208 | 靜態一致性、轉換、規則、合成案例及回歸測試。不能代替臨床正確性。 |
| SUSHI 3.20.0 | pass：0 errors / 0 warnings | 33 Profiles、9 Extensions、42 ValueSets、12 CodeSystems、55 Instances 可產生。 |
| PHI gate | pass：346 files | 公開版控檔未命中既定病歷號／個案識別規則。不能代替正式 DPIA 或人工隱私審查。 |
| CQL CLI translation | pass | `cql-to-elm-cli 3.26.0` 可產生約 370 KB ELM JSON。 |
| CQL runtime | partial：1/20 Measure | `bc-qi-01` 已對 5 組合成 R4 Bundle 執行；其餘 19 個 Measure 未做 executable test。 |
| IG Publisher 2.3.2 resource validation | fail：20 errors / 338 warnings | 20 errors 均為各 Measure 的 effective data requirements 無法解析 `FHIRHelpers|4.0.1`；warnings 另含 48 個無 target code system 的 ConceptMap、48 個缺 description 的 ValueSet、48 個缺 title 的 ConceptMap 等。 |
| IG website/package build | unavailable | Windows 無 Jekyll；未生成當前 HEAD 的 `qa.html`、網站與 `package.tgz`。8/14 的 release artifact 比目前 HEAD 少 27 commits，不能當作現況證據。 |
| Template supply-chain gate | fail | Publisher 明確警告 `fhir.base.template#1.0.0` 不再視為安全，必須依官方通知完成替換／緩解與重建。 |

本輪已修正先前未被 CI 發現的 Library binary-loader 設定、TCR QuestionnaireResponse 型別、無法解析的範例參照與 CQL `Task.input` 中間型別問題，並加入回歸測試。修正前 Publisher 為 69 errors；修正後剩 20 errors。

## 內容成熟度

### 品管＋季報

- 20 個 Measure：6 個品質指標、5 個季報比率、9 個分布表。
- 68 筆 population／stratifier criteria：66 drafted、2 not-applicable。
- Python 對應狀態：56 implemented、5 not-implemented、4 task-layer、1 divergent、1 manual-override、1 not-evaluable。
- criteria review：56 design、5 blocking-data-gap、4 open-question、3 proxy-in-use。
- 34 筆共同層 Mapping：21 筆 `candidate-unverified`；review 中 9 筆 `blocking-data-gap`。
- 19 個臨床 ValueSet 刻意不含代碼；這是正確揭露，不得為了讓畫面看似完成而填入未查證候選碼。

### 癌症診療計畫書來源

- 單一來源基線 223 controls：195 `pending-field-review`、3 `pending-algorithm-review`、25 `implemented-partial`。
- 目前整理後的表單、報表與工作簿只能當 secondary source、reconciliation copy 或進件候選，不能冒充原始病理、檢驗、影像與治療事實。
- 正式資料流必須是 `raw source element -> source adapter + Provenance -> canonical FHIR fact -> task projection -> report`；不得由報表回推 canonical fact。

### QBC 與治理

- approval register：12 `pending-human-signoff`、1 `pending-external-acceptance`、1 `blocked-until-other-gates-close`。
- 必須補齊主管機關書面確認、院內 master data、術語授權、資安／隱私、VPN receipt 與錯誤碼 reconciliation。

## 發布前必須使用的核對方式

每一筆會影響臨床語意或報表數字的 mapping 至少要有下列六層證據；高風險項目不得只靠單一工具或單一 reviewer。

1. **來源逐欄追溯**：保存權威文件／原始系統欄位、版本、SHA-256、適用條件與原文；報表只能是比對副本。
2. **FHIR conformance**：SUSHI 加 IG Publisher／FHIR Validator，檢查結構、cardinality、binding、invariant、profile 與 reference；errors 必須為 0。
3. **術語核對**：由術語服務驗證 system、code、display、版本、ValueSet expansion、授權；candidate 與 confirmed 分開。
4. **可執行規則測試**：每個 Measure 都要有 positive、negative、exclusion、missing、boundary、日期邊界與多筆事件案例，並實際執行 CQL。
5. **獨立重算**：CQL 與獨立參考實作對同一批輸入逐案比對 population membership，不只比總數；差異必須為 0 或有簽核理由。
6. **真實去識別 golden data 與端到端驗收**：由原始資料產生 FHIR，再產生報表／申報檔，與人工核定結果、接收端 receipt 和錯誤碼逐案 reconciliation。

另須獨立完成臨床雙人審查、資料治理／資安／授權審查，以及 package、網站、連結與版本 metadata 的可重現發布驗證。

## 精確發布門檻

### 社群 Preview

- CI 從乾淨 checkout 可重建網站與 `package.tgz`。
- IG Publisher：0 errors、0 broken links；每一個 warning 都修正或在 `ignoreWarnings.txt` 記錄逐項理由、owner 與核准日期。
- CQL 翻譯失敗不能回傳成功；CI 必須同時檢查 exit code、ELM 檔存在與 log 不含 translation error。
- `draft`、`experimental`、非官方、非臨床／非申報用途及已知缺口在首頁、downloads、package metadata 一致。
- PHI、授權與 template supply-chain gate 通過。

### 正式臨床／報表／申報

除 Preview 門檻外，還必須全部達成：

- 受影響 mapping 100% 有原始資料路徑、轉換規則、loss classification、Provenance 與 reviewer。
- 所有正式使用的 ValueSet／ConceptMap 100% 經版本化術語與授權審查；不得有空臨床 ValueSet 或 `candidate-unverified`。
- 20/20 Measure 均完成 executable synthetic suite；CQL 與獨立實作逐案一致。
- 代表性去識別 golden cohort 完成雙人臨床審查，分母、分子、排除、stratum 與例外逐案一致。
- 所有 approval-register blocker 關閉；外部 VPN／接收端驗收成功並保存 receipt。
- canonical、package id、publisher identity、版本政策與維護責任取得正式治理核准。

在上述條件全部有可追溯證據以前，版本只能維持 Preview，不得將「測試通過」表述為「資料正確」或「可正式使用」。
