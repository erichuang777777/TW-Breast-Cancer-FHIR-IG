# FHIR IG 發布與資料正確性驗收矩陣

本文件把「程式能建置」、「可公開社群 Preview」與「可供院內品管／季報使用」分開。任何一層通過都不能替代下一層的證據。

## 目前判定

| 層級 | 目前結果 | 尚缺證據 |
|---|---:|---|
| 原始碼／研究草稿 | pass | 必須持續標示 `draft`、`experimental`、非官方及非臨床用途。 |
| 可重現技術建置 | pass | Publisher 2.3.2：0 errors、232 warnings、0 broken links；一般 CI 與 artifact 均已留存。 |
| 社群 Preview 發布 | block | 缺範例與 CRMI dependency 兩類已歸零；其餘 4 類 Publisher warning 尚未完成具名、限期核准。 |
| Computable Measure Preview | block | 20 個 Measure 僅 `bc-qi-01` 有真正 runtime test；19 個臨床 ValueSet 為空。 |
| 院內品管／季報 | block | 缺原始來源 mapping、正式 terminology、完整 reporting-period cohort、golden cohort 與逐案 reconciliation。 |
| 跨院／正式申報 | block | 除上述項目外，仍缺跨實作驗證、在地治理、VPN／接收端回執與主管機關規則確認。 |

## 必須使用的六種核對方法

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

## 數量與正確性門檻

### Mapping

- 正式使用範圍內的 required facts：100% 完成來源與 FHIR mapping。
- `blocking-data-gap`：0。
- `candidate-unverified`：0。
- 每一個有損轉換均要標記 loss classification，並有 reviewer 決定是否可接受。
- 每一個人工補登／覆寫都必須保存原值、新值、理由、操作者、時間與適用 Measure。

### Measure 與測試

- 20/20 Measure 均需 translation 與 runtime execution；目前是 1/20。
- 每個 Measure 的測試數不以任意固定樣本數取代 coverage。最低要求是所有 truth-table branch、排除、缺值、邊界、日期邊界及多筆事件行為全部有案例。
- Golden cohort 要鎖版並逐案核對 100%，允許的未解釋差異為 0。
- 若要主張跨院可實作，至少需兩個彼此獨立的 source adapter／實作者完成同一套 conformance 與 golden tests；否則只能宣稱單一環境驗證。

### Publisher warnings

最新 232 warnings 的精確基線為：

| 類別 | 數量 | 現況 |
|---|---:|---|
| OID 建議 | 133 | 未核准 OID root，不得自行虛構。 |
| TCR ConceptMap 無 target system | 48 | 刻意不宣稱未審查的標準術語等價關係。 |
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

除社群 Preview 外，20/20 Measure、正式 terminology 與全部合成 branch coverage 必須完成。此層仍不代表院內數字正確，除非已有原始資料 golden cohort。

### 院內品管／季報

除 Computable Preview 外，正式使用範圍內的 mapping 必須 100% 完成，並至少對一個完整報告期間的所有納入個案做 source-to-FHIR-to-report 逐案 reconciliation。所有未解釋差異必須為 0。

### 跨院或正式申報

除上述門檻外，還要有至少兩個獨立實作、跨院 terminology／workflow review、資安與隱私審查，以及 VPN／接收端成功回執。若缺主管機關或院方必要核准，只能發布非官方技術草稿，不能宣稱正式可用。
