# 癌症診療計畫書來源格式稽核（2026-01 批次）

{% include disclaimer.md %}

## 目的與隱私邊界

本頁記錄受控環境內 2026 年 1 月診斷批次的去識別化結構稽核結果，用來補強 Cancer Care Plan Task 的來源契約、Mapping 規則與 review backlog。原始 JSON、XLSX、PDF、FHIR Bundle、檔名、識別碼及臨床內容均未提交至本 IG。

以下數字是對目前 76 組本地來源檔的實證觀察，不是官方規則、臨床必填規則或母體統計。

本工作有三個明確交付目標：

1. 將 JSON 定義成可版本化、可驗證、之後可由網頁填寫的 template／response contract。
2. 每個 JSON 欄位都要標示 `shared`、`care-plan-only` 或 `derived`，並對應到乳癌 common FHIR layer 或 Care Plan Task；不確定者必須維持 pending review。
3. 以 2026-01 樣本量測 Care Plan JSON 對 QBC 115 欄的實際支援與缺口。這是平行 Task 的 reconciliation，不建立 Care Plan → QBC 的正式上下游關係。

## 批次結果

| 檢查 | 結果 |
|---|---|
| 同名 `.case.json`／XLSX／PDF 組數 | 76 |
| JSON 可解析 | 76／76 |
| Care Plan FHIR Bundle 產生成功 | 76／76 |
| Bundle 結構／ID／reference 檢查 | 76／76 通過 |
| QuestionnaireResponse item 保存數不一致 | 0 |
| JSON schema version | 全部為 `1` |
| top-level／section shape | 各 1 種 |
| control-set variants | 6 種 |
| 觀察到的唯一 control | 314 |
| 既有單一樣本 catalog | 223；全部仍有觀察到 |
| 新增待盤點 control | 91 |
| 所有個案共同出現 control | 207 |
| input type drift | 0 |

## JSON 結構規律

六種 control-set variant 可由四個 section 的欄位數組合解釋：

| Section | 觀察到的 fields 數 | Mapping 意義 |
|---|---:|---|
| `basic` | 329 或 330 | 至少存在兩個相近表單變體；新增／缺少 control 需版本化，不可依陣列位置 Mapping |
| `reference_reports` | 固定 5 | `fields[]` 與 combined `text` 必須分開保存；76／76 均有 combined text |
| `disclosure` | 0 或 35 | 24／76 有此 block；block 缺少代表「未提供／不適用／版本未包含」，不得解讀為否定 |
| `treatment_plan` | 0 或 46 | 10／76 有 structured fields，但 76／76 均有 treatment plan text；文字不可因 fields 為空而遺失 |

每案總 field element 為 334–416，其中含 112–117 個同名 radio／checkbox options。這些 option 是一個 control group 的候選選項，不是重複臨床事件。

### 現行 capture v1 與目標 template v2

`cancer_care_plan.schema.json` 是現行 scraper capture v1 的相容契約，用於接收既有一月 JSON。它保留原網頁 control metadata、文字與 tables，但並不代表欄位定義、選項或相依規則都已審定。

`cancer_care_plan_template.schema.json` 是未來網頁填寫用的 v2 草稿契約。每個欄位必須具備：

- 穩定且不可依賴陣列順序的 `link_id` 與 `control_name`。
- `type`、`required`、`repeats`、完整 `answer_options`、實際 `answers` 與 `enable_when`。
- `ownership`：`shared`、`care-plan-only` 或 `derived`。
- 一個以上可審閱的 `fhir_mappings`，明確指出 common layer 或 Care Plan Task、resource、path、transform 與狀態。
- `review_status`；derived 欄位另須提供算法／來源 Provenance。

v2 schema 已訂好資料形狀，但 314 controls 的逐欄定義仍須從多檔 union catalog 產生並簽核。現行 select 未保存完整 option universe，欄位必填與顯示相依也尚未取得網頁 JavaScript／驗證規則，因此不得把一月觀察值直接包裝成正式 ValueSet 或 `enable_when`。

### JSON 可以提供的內容

76／76 均含下列來源 channel：

| JSON channel | 可提供內容 | 目前 FHIR 用法 | 限制 |
|---|---|---|---|
| `schema_version` | extractor／contract 版本 | 月度稽核與 Provenance 候選 | 目前 Bundle 尚未明確保存版本 |
| `scraped_at` | 網頁擷取時間 | Bundle timestamp、QuestionnaireResponse.authored、CarePlan.created | 不一定等於臨床事件時間 |
| `source` | 來源系統描述 | Provenance.entity 候選 | 不可只用顯示文字識別系統 |
| `chart`／`seqno` | 私有來源識別 | 本地 reconciliation；必要時使用受控 Identifier | 含 PHI，不得進公開範例或 log |
| `diagnosis_code` | 診斷來源值 | Condition.code 候選 | 需確認 code system、版本與顯示文字 |
| `section.label/found` | 網頁 section 狀態 | Questionnaire／audit metadata | `found=false` 不等於臨床否定 |
| `section.text` | rendered narrative | treatment plan／reference report 已保存 | basic／disclosure text 尚未完整映射 |
| `section.fields[]` | id、name、type、label、value、selected_text、checked、disabled | QuestionnaireResponse 與 reviewed common facts | 只有欄位語意審閱後才能提升為 clinical resource |
| `section.tables[]` | table index、rows、版面文字與選項上下文 | contract／layout audit；必要時 DocumentReference | 不可把所有 table cells 當成病人 facts |

一月 JSON 共含 8,951 個 table objects、14,549 rows、41,501 個文字 cells。`reference_reports` table/text 已由目前 Bundle 完整保存，`treatment_plan.text` 亦完整；basic／disclosure tables 主要包含完整 UI 模板、標題、空欄與未選 options，目前只保存有值的 source answers。完整表單定義應進入 Questionnaire／catalog，而不是把模板內容塞入個案 QuestionnaireResponse。

### FHIR Mapping readiness

| 分類 | Controls | 目前處理 |
|---|---:|---|
| 已有明確 common clinical resource 候選 | 22 | 1 個 Condition、21 個 Observation；仍需術語與臨床審閱 |
| 與 QBC 重疊但 FHIR path 待確認 | 3 | `ddlReason`、`rblHGrade`、`rblHospital` 暫存 QuestionnaireResponse |
| 既有 care-plan-only、語意待審 | 195 | lossless source answer preservation |
| derived／algorithm 待審 | 3 | QuestionnaireResponse + Provenance；不得當原始事實 |
| 一月新增、尚未進 catalog | 91 | 全部 pending；其中 12 個在樣本中曾有填值，優先審閱 |

314 controls 中有 100 個在一月樣本曾有填值、214 個未填。未填只能證明樣本中未使用，不能用來刪除欄位、縮小 ValueSet 或推導條件規則。

## Care Plan JSON 對 QBC 115 欄的覆蓋

目前 adapter 以同一份 JSON 獨立建立 QBC check view。76 筆皆可解析；重新納入 `basic.tables`、尚未登錄 catalog 的乳癌 controls，修正 sentinel／axillary node 判讀，並依治療順序推導 `DIAG_TYPE` 後，QBC 115 欄中至少在一筆一月樣本能產生值者為 **51 欄**。每筆實際產生 18–40 欄，中位數 31 欄。

先前把網頁欄位 `ddlReason=初診斷或初次治療` 直接翻成 `DIAG_TYPE=2`，並在缺值時預設為 2，屬於錯誤推論，已撤回。`ddlReason` 只能描述收案原因，不能區分直接手術與新輔助治療。依本專案確認的規則重新分類：手術早於抗癌治療（或只有手術）為 1、抗癌治療早於手術為 2、只有抗癌治療且 M1 為 3；證據不足時不得猜測。

進一步納入治療階段後，一月樣本的彙總結果為：`DIAG_TYPE=1` 52 筆、`DIAG_TYPE=2` 13 筆、`DIAG_TYPE=3` 1 筆、一般待審閱 0 筆、來源不完整 10 筆。這 10 筆的治療控制項全部未勾選，沒有治療 marker，XLSX／PDF／DOCX 也沒有補充治療證據，因此不能假裝成任何 QBC 類別。

「未產生」不能直接解讀成「JSON 沒有答案」或「必須找外部資料」。目前 115 欄分成下列四類：

| 分類 | 欄數 | 解讀 |
|---|---:|---|
| adapter 已於一月產生 | 51 | 至少一筆有 candidate；仍須依 requiredness、ValueSet、review status 驗證 |
| JSON 已有來源候選、尚未完成 QBC 正規化 | 10 | `D010`、`D027`、`D029`、`D037`、`TM01`、`TM02`、`TM05`–`TM08` |
| JSON 沒有 follow-up event | 6 | `T01`–`T06`；初始申報沒有追蹤事件時不是缺值 |
| 尚須確認來源或條件適用性 | 48 | 包含 10 筆來源不完整所影響的條件欄，以及不同收案類別真正需要補充的欄位；不能整批解讀成外部資料缺口 |

因此原先「75 欄需要額外資料」、「76 筆均為 DIAG_TYPE=2」及初次修正後「29 筆待審閱」三項結論均已撤回。現在應以逐筆收案分類、治療階段、欄位條件適用性及來源完整度共同判斷。

| 產生方式 | 唯一 QBC 欄位數 | 主要新增內容 |
|---|---:|---|
| JSON structured／table | 32 | 包含 `P01`、`P02`、`BIRTHDAY`、`D003`／`D030`、`D009`、`D028`、`D036` |
| 規則推導 | 8 | 新增以治療順序與 M1 規則推導 `DIAG_TYPE`，另含 `D008`、`D014`、`D016`、`D035`、`D044`、`D048`、`D050` |
| JSON 內 reference-report text 抽取 | 12 | 包含正確區分 sentinel `D038`–`D040` 與 axillary `D041`–`D043` |

`D047` 同時可能由 structured control 或報告文字抽取，因此三列合計 52、去重後為 51。`D019`／`D053` 僅在 HER2 IHC 為 2+ 且 FISH 有實際陽性／陰性結果時產生；「未測」不得誤轉成 QBC 陰性。

`HOSPID` 可由部署設定提供，`ID` 應由病人主檔提供；身高體重、收案行政欄位、特定檢驗及實際治療日期仍須按各筆適用條件確認來源。報表保留每個欄位的 `not_applicable_records` 與 `value_records`，避免把條件不適用誤報為來源缺漏。

`treatment_plan.text` 中的手術、放療、抗癌治療、藥物及部位是有效的「診療計畫事實」，不得因其為文字敘述而視為沒有資料。adapter 目前已將治療類別、順序與計畫日期保存為可追溯的 `care_plan_treatment_facts`，並可用於上述 `DIAG_TYPE` 規則。投影至 QBC 時，`TM01`、`TM02`、`TM05`–`TM08` 仍須完成重複事件及代碼正規化；計畫日期也不得在未確認日期語意前直接冒充 `TM09`／`TM10` 的實際執行日期。

月批次工具 `scripts/analyze_care_plan_qbc_coverage.py` 會輸出不含個案識別或值的逐欄五分類矩陣，供每月比較。

### 來源解析規則

1. Mapping key 使用 `section + control_name`，必要時再加 option value；不得使用 fields 陣列索引。
2. `checked=false` 的 radio／checkbox 即使帶 HTML `value`，也視為未選，不產生 QuestionnaireResponse answer。
3. `checked=true` 才輸出所選 option；同 group 多選必須依控制項型別與表單規則審閱。
4. select 的空字串或「請選擇」視為 absent；保留 code／raw value 與 display text，正式術語 Mapping 前不得只靠顯示文字。
5. `treatment_plan.text`、`reference_reports.text` 與各自 `fields[]` 獨立處理。
6. 缺少整個 optional block 不等於各欄皆為 false；FHIR 應表達 absent／unknown，必要時記錄 DataAbsentReason 或 Task validation issue。
7. derived／auto controls 只保留顯示結果與 Provenance；在算法與版本審閱前不得提升為原始臨床事實。

### 內容與選項規則

- radio／checkbox 的 options 可由同一 `control_name` 下的 option elements 建立候選清單，但仍需表單 owner 確認是否完整。
- 現行 select 只保存當次 `value`／`selected_text`，無法由病人樣本證明完整 allowed options；後續 extractor 應增加 `options[]`（value、label、selected、disabled）。
- 不得把一月「曾出現過的值」直接當成正式 ValueSet；它只能作 observed-value audit。
- 新 option、消失 option、同 code 不同 label、同 label 不同 code、input type drift 均須產生 review item。
- 欄位相依、顯示條件與必填規則無法只靠已填樣本可靠推導；應另取網頁 validation／JavaScript 規則或由表單 owner 簽核。

## 每月匯入稽核規則

| Gate | 條件 | 處理 |
|---|---|---|
| Blocking | JSON 無法解析、schema 不符、必要 section／field property 缺少 | 停止該檔轉換 |
| Blocking | 已審 Mapping control 的 input type 改變，或 reviewed code 不在 ValueSet | 停止 affected fact promotion；保留來源並回報 |
| Review required | 新 control、新 option、label／code 漂移、optional block 新變體 | 加入 monthly drift report，不自動更新正式 Mapping |
| Review required | XLSX／PDF 有內容但 JSON 無對應 channel | 建立 `source-gap`，確認 extractor 是否漏抓 |
| Advisory | 未審 control 有值 | 保存於 QuestionnaireResponse，禁止靜默丟棄 |
| Advisory | 已知 optional block 缺少 | 記錄 absent；不得轉為 false |

每月聚合報告不得包含檔名、chart、seqno、來源文字或個案值。Baseline 更新必須留下版本、差異、reviewer 與生效月份。

## XLSX 與 PDF 的幫助與限制

XLSX 全部可讀、每案 1 張 sheet、沒有公式，約 22–69 個非空儲存格；它是較精簡的人類可讀輸出，不保留 JSON 的 control name、checked state、source path 與完整空欄結構。PDF 為 1–12 頁且每頁均可抽取文字，主要保存版面、頁次與正式文件閱讀順序。

跨格式文字 token 的中位覆蓋率：

| 比對 | 中位數 | 解讀 |
|---|---:|---|
| XLSX token 可在 JSON 找到 | 89.4% | XLSX 大部分內容已存在 JSON |
| PDF token 可在 JSON 找到 | 81.2% | PDF 大部分內容已存在 JSON，但含更多版面／文件文字 |
| PDF token 可在 XLSX 找到 | 88.0% | PDF 與 XLSX 高度重疊 |

仍有 311 種只在單一個案出現、無法在 JSON 逐字對應的 XLSX cells：144 種為日期型、167 種為敘述／標題型；這些 cells 全部也能在同名 PDF 找到。因此 XLSX／PDF 對「發現 JSON 未逐字保存的文件內容」有價值，但這些差異可能包含格式化日期、合併標題或額外敘述，不能直接自動提升為 clinical facts。

### 建議的來源優先序

1. JSON control metadata／value 是 structured Mapping 的主要來源。
2. XLSX 用於欄位顯示、文件摘要及 JSON completeness reconciliation。
3. PDF 用於版面、頁次、簽章／正式呈現及人工比對；不以 PDF 座標作 canonical Mapping key。
4. 同一內容若只在 XLSX／PDF 出現，建立 `source-gap` review item；需先確認語意、來源欄位及 Provenance，再決定是否補進 JSON extractor 或建立 FHIR resource。
5. 需要交換原始文件時，建議以 `DocumentReference` 保存 PDF／XLSX 的 URL、hash、contentType、日期與安全標籤；不要將附件文字無條件複製成 Observation。

## 對目前 IG 的影響

- 223-control catalog 保留為 Preview 基線，但不再宣稱涵蓋全部表單變體。
- 新觀察到的 91 controls 全部先標示 `pending-field-review`；完成欄位定義、條件、值域與 FHIR path 審閱後才可加入 normative Mapping。
- 下一版 catalog 產生器應從多檔 union 建立，並增加 `first_seen_schema`、`variant_presence`、`record_presence_count` 與 review status。
- JSON→QuestionnaireResponse 已驗證能保存 parser 認得的 populated fields、treatment plan text 與 reference-report text；它不是完整 JSON document 的無損序列化。basic／disclosure text、tables、完整 option inventory 與部分 top-level metadata 仍需 contract／Provenance 設計。

## 未來由原始資料填寫診療計畫

目標資料流不是「每月 JSON 永久作為標準」，而是：

```text
病理／檢驗／影像／病史／治療原始資料
  → source-specific mapping + Provenance
  → Breast Cancer common FHIR facts
  → Cancer Care Plan composition／form-filling rules
  → Care Plan Task Bundle／必要的人類可讀文件
```

後續需要建立雙向可追蹤矩陣：`raw source element → common FHIR fact → care-plan control → rendered document/FHIR Task output`。若原始資料不足，欄位應維持 absent 或進人工補登佇列，不得從其他 Task 輸出或 XLSX／PDF 顯示文字猜測。

機器可重跑工具：`scripts/analyze_care_plan_batch.py`、`scripts/analyze_care_plan_companions.py` 與 `scripts/analyze_care_plan_qbc_coverage.py`。聚合 JSON／XLSX 稽核報告應留在 `runtime/` 或其他受控目錄，不得提交個案級輸出。
