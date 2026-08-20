# 個管指標 Task

{% include disclaimer.md %}

## Task 定位

乳癌個案管理團隊固定週期產出兩份報表：向癌症委員會提報的 **6 項品質暨核心指標**，以及向癌症中心提報的 **個管季報**（收案量、新診斷動態、人口學與分期分布、留治率與完治率）。兩份報表由不同的人簽核、在不同的會議上被檢視，但**跑在同一組臨床事實上**。

本 Task 因此是一個 Task、一份 mapping，內部以 `indicator_family` 區分 `quality` 與 `quarterly` 兩個報表族。拆成兩份 mapping 維護過，同一個分期 `Observation` 被描述兩次、兩個 id、兩條投影規則，而且沒有任何機制強迫兩邊一致——**輸出分開是呈現決定，模型分開是維護負債**。

本 Task 與 [QBC／P4P Task](task-qbc.html) 及 [品質監控指標](quality-indicators.html) 頁面所述的健保署方案指標**沒有關係**。兩者都在乳癌範疇之下，部分指標標題讀起來相似，但分母定義、排除條件、閾值、報告對象與核算單位都不同：方案指標由健保署依 VPN 登錄資料核算，本 Task 的指標由院內團隊計算、由癌症委員會或癌症中心審議。**兩邊的定義不得互相套用。**

本 Task 與其他 Task 平級，各自從乳癌 canonical facts 投影，不從任何 Task 的輸出轉入。

## 兩個報表族

| | 品質指標 `quality` | 個管季報 `quarterly` |
|---|---|---|
| 稽核者 | 多專科團隊、癌症委員會 | 癌症中心 |
| 審查重點 | 臨床指引符合度 | 個管工作量與留治成效 |
| 核算單位 | 多專科團隊（全隊一個數字） | **個管師個人**（每人一欄） |
| Measure | `bc-qi-01`～`bc-qi-06` | `bc-qr-01`～`bc-qr-05`、`bc-qr-10`～`bc-qr-18` |
| 閾值 | 團隊自訂，逐年設定 | 無自訂閾值 |
| Task-only 主要來源 | 委員會決議 | 個管作業處置 |

## 輸入與輸出

| 項目 | 定義 |
|---|---|
| Trigger | 季報產出，或個管師修正原始資料後重跑 |
| Current input | 品質指標：個管師維護的季度工作表（分期、治療旗標、手術紀錄自由文字）。季報：個管系統單一匯出檔（一位個管師一檔，56 欄）加個案判定檔 |
| Target input | 乳癌 canonical facts：`Patient`、`EpisodeOfCare`、`Condition`、分期與 marker `Observation`、`Procedure`、`MedicationRequest`、`DiagnosticReport`、`Encounter`、`Organization` |
| FHIR representation | 11 個 proportion `Measure`、9 個 cohort `Measure`、對應 `Library`（CQL）、`MeasureReport`（summary 與 subject-list 各一） |
| Task-only input | Class 分類、收案身份與作業處置、團隊自訂閾值、委員會排除／加回決議、個管師個案判定 |
| Output | `MeasureReport`、逐案／逐格可反查的稽核明細、癌症委員會報告與季報工作表 |
| Acceptance | CQL 與 Python 參考實作在同一組合成資料上逐案一致；每個報表數字都能追到組成它的個案 |

## 來源結構盤點

目前基線已用不讀出個案值的方式盤點品質指標來源、季報來源與共用 Python 參考實作。盤點結果只保存副檔名統計、工作簿結構簽章、欄位 schema、FHIR Mapping 與阻擋項，不保存原始路徑、檔名、sheet 名稱、病歷號、姓名或儲存格值。

2026-08-21 基線包含 15 種工作簿結構、70 種工作表尺寸／公式組合、61 筆來源欄位描述與 34 項共同層 Mapping。另有 20 筆 criterion／mapping 層級的審閱列；同一資料缺口可能同時出現在兩個層級，因此此數字不是 20 個互不重複的臨床問題。

可重跑工具為 `scripts/build_case_management_source_audit.py`，輸出為 `outputs/case_management_source_audit/case_management_source_inventory.xlsx`。來源目錄必須由執行者明確傳入，工具不內建任何院內路徑；原始報表必須留在受控環境且不得進版控。

## 品質指標（`quality`）

| Measure | 核心指標 | 指標 | 2026Q1 參考結果 |
|---|---|---|---|
| `bc-qi-01` | 否 | 侵犯性乳癌(第1~3期)ER 陽性給予賀爾蒙治療的比率 | 77/77 |
| `bc-qi-02` | 核心1 | 臨床第1、2期以手術為首次治療且最終病理腋下淋巴結陰性者施行哨兵淋巴結取樣術的比率 | 45/45 |
| `bc-qi-03` | 核心2 | 乳房全切除且腋下淋巴結陽性≧4顆有進行放射治療的比率 | 4/4 |
| `bc-qi-04` | 核心3 | HER2 陽性且淋巴轉移之手術病人給予 anti HER2 藥物治療的比率 | 5/5 |
| `bc-qi-05` | 否 | 手術前曾經組織學確診的比率 | 94/94 |
| `bc-qi-06` | 否 | 病理分期侵犯性乳癌乳房保留手術後放射線治療的比率 | 14/15 |

### `bc-qi-06` 的定義與實作歧異

定義原文的排除條件是「年齡 ≧ 70 **且** 病理 N0」（AND）。歷年實作把它拆成兩個獨立排除：排除所有年齡 ≧ 70 者，並排除所有病理 N0 者。以 2026Q1 資料實測：

| 算法 | 分母 | 分子 | 指標率 |
|---|---|---|---|
| 歷年實作 | 15 | 14 | 93.3% |
| 定義原文 | 42 | 25 | 59.5% |

閾值為 ≧82.5%，兩種算法一過一不過。以 2026Q1 逐案比對：**31 例定義原文納入但歷年實作排除、4 例歷年實作納入但定義原文排除**（分母 15 → 42）。那 4 例（年齡 57／43／52／56，病理N `3a`／`1a`／`1mi`／`1mi`）病理期別皆記為「不適用」，即下一節 `D6-INVASIVE` 分歧所指的同一批個案：兩種算法都只排除病理期別 `= 0`，不排除「不適用」，因此這 4 例在 practice 與 definition 下都被算進分母，但其分期完整性其實有疑義。criteria 表把這兩列（`D6-INVASIVE`、`N6-RT`）的 `review_status` 都標為 `blocking-data-gap`，同屬一類尚待補齊的資料缺陷。

**目前不建議直接改用定義原文。** 分子加回的個案理由全部是「總院RT」，代表 `放射線治療` 旗標只記錄本院；被排除的 N0 族群同樣可能在總院完成放療而未登錄。在放療執行院所（`CM-BC-025`）與劑量（`CM-BC-024`）補齊之前，定義原文算出的數字會低估實際成效。

兩種算法在 criteria 表中以 `variant` 欄區分（`practice` 與 `definition`），差異個案一律逐案輸出供團隊審議。此項在共同層補齊放療來源後重新評估。

### CQL 與 Python 目前的已知分歧

`python-implementation-manifest.json`（由 `個管品管_1_品質核心指標統計/pipeline/rules.py` 的 `CRITERION_IDS`／`UNIMPLEMENTED_CRITERIA` 產生，`tests/test_case_management_measures.py` 逐條比對 criteria 表的 `python_status`）記錄了 `quality` 家族目前已知的四處分歧。**委員會已核定 2026Q1 六項指標的報告數字，rules.py 的演算法不因此變動**——以下只是誠實記錄分歧，不代表任何一邊即將被改成配合另一邊：

| criterion_id | 內容 | Python 現況 | 實測影響（2026Q1） |
|---|---|---|---|
| `D4-SURGERY` | 指標4 分母須有手術 Procedure | rules.py 指標4 分母**完全未檢查**手術 | 5/5 → 3/3 |
| `X5-INSITU-STAGE4` | 指標5 分母須排除原位癌／期別 IV | rules.py 指標5 分母**沒有**這項排除 | 94/94 → 92/92 |
| `D6-INVASIVE` | 指標6 分母須為侵犯性乳癌（病理期別非 0 且非空） | rules.py practice 僅測「病理期別 != '0'」，「不適用」仍留在分母 | 14/15 → 10/11 |
| `N3-DOSE` | 指標3 分子須驗證放射劑量 ≧4000 cGy | rules.py 與 CQL 皆**完全未評估**（無劑量欄位） | 無法評估 |

**Acceptance 段落所寫的「CQL 與 Python 參考實作在同一組合成資料上逐案一致」尚未達成**：目前只有 `bc-qi-01` 建立真正的合成 CQL execution 基線，其餘 Measure 尚未逐案執行；而且上述三項（`D4-SURGERY`、`X5-INSITU-STAGE4`、`D6-INVASIVE`）目前就是已知、已記錄、且刻意保留的分歧。`N3-DOSE` 雙邊皆誠實標示未評估，不算分歧。全體逐案一致要嘛等資料缺口補齊，要嘛委員會決議接受分歧並記錄理由，才能算數。

### 合成 CQL execution 基線

`bc-qi-01` 已用 CQFramework `cql-execution` 與 R4 `cql-exec-fhir` 實際執行，不再只停在 CQL→ELM 翻譯。五組完全合成 Bundle 分別涵蓋符合分子、只符合分母、ER <10% 排除、ER 缺值排除與 Stage IV 不進分母；預期聚合為 initial population 5、denominator 4、denominator exclusion 2、numerator 1，並與合成 `MeasureReport` fixture 完整比對。

正式臨床 ValueSet 仍維持空佔位。execution test 透過獨立、明確標示 `synthetic-test-only` 的代碼服務辨識測試資料，不會把未查證代碼寫入 IG。這證明的是 canonical FHIR facts → CQL → MeasureReport 的執行路徑；原始院內資料 → canonical FHIR facts、正式術語與真實資料驗收仍為 pending。

## 個管季報（`quarterly`）

五項比率：

| Measure | 指標 | 2026H1 參考結果 |
|---|---|---|
| `bc-qr-01` | 留院治療率 | 157/177 = 88.70% |
| `bc-qr-02` | 留院治療率（臺大體系內矯正後） | 173/177 = 97.74% |
| `bc-qr-03` | 完成治療率 | 56/59 = 94.92% |
| `bc-qr-04` | 失聯率 | 無法計算，缺前一年度名單 |
| `bc-qr-05` | 重返治療率 | 0/3 = 0% |

九張分布表（`bc-qr-10`～`bc-qr-18`）以 cohort `Measure` 加 stratifier 表達：收案身份、收案月份、新診斷動態、結案原因、性別與年齡層、Class 分類、分期、組織類型、HR/HER2 分型。

`bc-qr-04` 失聯率在 `Measure` 中以 `Prior Year Cohort Available` 參數把關：呼叫端未宣告已載入前一年度名單時，分母族群為空，報表拿到的是「沒有族群」而不是一個看起來已算好的數字。`bc-qr-05` 的分子（重返治療）目前由個管師逐案認定，CQL 中的表達是候選規則，取代人工判定前必須逐案比對。

### `分期 = ?` 的三個去向

`分期` 欄留白在現行工作表裡混合了三種完全不同的狀況，必須在共同層拆開，否則分期分布表的「診斷中」與「其它」永遠要靠人工分派：

| 實際狀況 | 現行表現 | 應有的 FHIR 表達 |
|---|---|---|
| 分期檢查尚未完成 | `分期 = ?` 且 `留院治療不列入分母原因 = 分期檢查中` | 分期 `Observation` 存在，`dataAbsentReason = temp-unknown` |
| 分期期間即轉院，本院從未取得分期 | `分期 = ?` 且 `不留院治療原因 = 診斷中轉院` | 無分期 `Observation`；`EpisodeOfCare` 指向接手的 `Organization` |
| 外院已分期但本院取不到資料 | `分期 = ?` 且 subtype 欄寫「無外院資料」 | 分期 `Observation`，`dataAbsentReason = unknown`，並記錄來源機構 |

## 共用的事實

34 項共同層事實中，6 項兩個報表族都要，投影規則必須一致；只改一邊就是缺陷：

| 概念 | mapping | 原 id |
|---|---|---|
| 收案時年齡 | `CM-BC-001` | QI-BC-001 / QR-BC-002 |
| 收案 episode | `CM-BC-002` | QI-BC-002 / QR-BC-003 |
| 原發乳癌診斷 | `CM-BC-003` | QI-BC-003 / QR-BC-005 |
| 臨床期別 | `CM-BC-004` | QI-BC-004 / QR-BC-007 |
| 病理期別 | `CM-BC-005` | QI-BC-005 / QR-BC-008 |
| ER 等 marker | `CM-BC-008` | QI-BC-008 / QR-BC-011 |

Task-only 也有兩項共用：`CM-TASK-001`（Class 分類）與 `CM-TASK-002`（收案身份／確診醫院）。兩者在兩個報表族都是行政分類，**都不提升為共用臨床術語**。

## Criteria 的兩種表達並存

CQL 是 `Measure` 的標準表達，可被其他系統執行；Python 參考實作現在就能跑、負責產出報表與稽核檔。兩者都**由同一份 population criteria 表產生並比對**：

```
case-management-population-criteria.csv   ← 單一事實來源
        ├── Library (CQL)      規範表達，隨 IG 發布
        └── Python 參考實作     報表產出與稽核
                    ↓
        同一組合成資料，逐案比對分母與分子
        不一致即為發布阻擋條件
```

分工：

- **CQL** 是規範。指標定義變更時先改 criteria 表與 CQL。
- **Python** 是參考實作與驗收工具，另外承擔 CQL 無法涵蓋的部分：委員會的排除／加回決議、個管師的個案判定、報告文件產出、與前次執行的差異比對。
- 任一邊獨有的行為都必須在 criteria 表標記，不能只存在於程式碼裡。

目前狀態：CQL 已依 criteria 表逐條起草（66 條 criteria 標記 `drafted`，2 條委員會決議標記 `not-applicable`），但**尚未翻譯執行**——臨床 ValueSet 仍是未填代碼的佔位，代碼查證完成前 Library 無法跑。個管作業分類（收案身份、收案狀態、結案原因、Class、留治與治療處置、完治結果）是個管團隊自有的行政代碼，權威來源就是團隊本身，因此在 `case-management-terminology.fsh` 中明確列舉；臨床代碼則一律不列舉。兩者的處理方式不同不是不一致，而是因為可查證的對象不同。

CQL 與 Python 兩邊的逐案比對尚未執行，那是 Library 可翻譯之後的驗收條件，不是現在可宣稱的狀態。

現行 Python 實作已內建交叉驗證：同一份數字由兩套不共用程式碼的算法各算一次（逐欄位彙總 vs 逐案標記），逐格必須相同；另檢查各分區小計是否等於個案總數、跨區塊一致性、以及所有欄位值是否落在已知值域內。CQL 併入後成為再一個來源，比對機制不變。

## 目前的代理條件

工作表沒有日期與劑量欄位、分期是單一自由文字欄、醫院名稱是字串，現行實作只能用代理。這些代理**全部可由共同層事實解除**，是本 Task 導入 FHIR 的主要理由。

品質指標：

| Measure | 定義原文要求 | 現行代理 | FHIR 來源 |
|---|---|---|---|
| `bc-qi-02` | 手術日期 < 治療開始日期 | 抗癌治療類別 ≠ 新輔助 | `Procedure.performedDateTime` 對 `MedicationRequest.authoredOn` |
| `bc-qi-03` | 放射劑量 ≧ 4000 cGy | 完全未評估 | `RadiotherapyCourseSummary.totalDoseDelivered` |
| `bc-qi-04` | 術後 HER-2 = 3+ 或 2+ 且 FISH 陽性 | 分子分型 ∈ {B2, H} | HER2 IHC 與 ISH `Observation` |
| `bc-qi-05` | 手術日期 > 切片日期 | 僅檢查切片存在 | 切片與手術兩個 `Procedure.performedDateTime` |

季報：

| 項目 | 現行代理 | FHIR 來源 |
|---|---|---|
| 分期未完成 | `分期` 欄填 `?`，再由個管師讀「備註二」自由文字逐案判定 | 分期 `Observation` 加 `dataAbsentReason`（`CM-BC-033`） |
| 分期本身 | 單一 `分期` 欄，不區分臨床或病理 | 臨床與病理兩個 stage group `Observation`（`CM-BC-004`／`CM-BC-005`） |
| HR/HER2 分型 | 人工鍵入的字母 A／B1／B2／H／T | 四個 marker `Observation` 推導（`CM-BC-008`～`CM-BC-012`） |
| 組織類型 | 自由文字，11 個分群寫成 27 種拼法，靠正規表達式字典歸併 | 編碼 morphology（`CM-BC-032`） |
| 體系內轉院 | 以醫院名稱字串比對關鍵字清單 | `Organization.partOf`（`CM-BC-034`） |
| 年齡層 | 匯出檔預先算好的區間碼 | `Patient.birthDate` 對收案日期計算（`CM-BC-001`） |
| Class 3 | 未記在 Class 欄，寫在 subtype 自由文字裡，靠字串比對撈回 | Task-only cohort label 明確登錄（`CM-TASK-001`） |
| 失聯 | 整欄由人手填 | `Encounter.period.end`（`CM-BC-037`）；仍需前一年度名單（`CM-BC-038`） |

另有兩項人工作業同樣可由建模解除：

- **執行院所**寫在值字串裡（`1(總院)`、`1(外院)`）。改以 `Procedure.performer` 與 `Procedure.location` 表達後，2026Q1 五筆「總院RT」分子加回不再需要人工處理。
- **ER 以自由文字記錄**（`＞95`、`僅RT`、`外院資料不足`）。改為 `Observation.valueQuantity` 加 `dataAbsentReason` 後，1–9% 排除帶可精確判定。

`分類`（A／B1／B2／H／T）是由 ER、PR、HER2、Ki-67 判讀而來的**衍生值**。共同層應保存四個 marker `Observation`，由 Task 層推導分型；不應把判讀結果的字母當成共用臨床事實儲存。

以 2026 上半年一位個管師的 201 位新診斷個案實測：季報需要人工判定的只有 10 案，其中 7 案的根因是「分期欄留白、真正期別藏在自由文字」。`CM-BC-033` 一補上，這 7 案即消失。

## 邊界

- 本 Task 不重現也不取代國民健康署、健保署或任何主管機關的核算程式；院內計算結果不等同官方核定值。
- 團隊自訂閾值、Class 分類、收案身份、個管作業處置、委員會決議都是 Task-only 資料，不提升為乳癌通用臨床術語。
- 排除、加回與個案判定是臨床與行政判斷，**不可由規則推導**。必須以個案為單位、附理由登錄，並在輸出中保留，讓審查者看得到什麼被覆寫、為什麼。
- 失聯率在前一年度名單補齊前一律標示為手填，不得呈現為已計算。
- 個案層級輸出（subject-list `MeasureReport`）含可識別資訊，僅限院內流通；對外版本一律去識別化，且去識別編號須由鹽值雜湊產生，不可用出現順序編號——列序一變編號就變，人工判定會整批錯位。
- 原始資料修正後必須重跑，並保留輸入檔的 SHA-256 與前後差異，否則無法說明同一期為何有兩份數字。

## 相關檔案

設計來源：

- `mappings/case-management/breast-common-to-case-management.csv` — 34 項共同層事實對應
- `mappings/case-management/case-management-population-criteria.csv` — 68 條 population 與 stratifier criteria
- `mappings/case-management/case-management-measure-catalog.csv` — 20 個 Measure
- `mappings/case-management/case-management-task-only-fields.csv` — 18 項 Task-only 資料

產出物（兩個報表族共用，不分檔）：

- `ig/input/fsh/case-management-measures.fsh` — 20 個 `Measure`（11 個 proportion、9 個 cohort）、共用 `Library` 與 `MeasureReport` Profile
- `ig/input/cql/BreastCancerCaseManagement.cql` — 兩族共用的 population 與 stratifier 表達
- `ig/input/fsh/case-management-terminology.fsh` — 臨床代碼佔位（待查證）與個管作業分類（院內行政代碼，已列舉）
- `tests/test_case_management_measures.py` — criteria 表、FSH、CQL 三者對齊檢查

檢查項目包含：每個目錄中的 Measure 都有對應的 `Measure` instance、每個 `criteria.expression` 都指得到 CQL 的 define、每個 criterion_id 都在 CQL 中可追、閾值與委員會決議沒有被寫進 Measure。任一邊單獨修改都會在此失敗。

## 相關頁面

- [Task 目錄](task-index.html)
- [乳癌共同資料模型](common-model.html)
