# Must Support 實作政策

{% include disclaimer.md %}

本頁定義本社群草稿中 `mustSupport = true` 的一致解讀方式。此政策適用於宣告支援本 IG Profile 的資料產生者與資料接收者；它不代表本專案已部署 FHIR server，也不擴張 CapabilityStatement 所列的需求邊界。

## Must Support 不等於必填

`mustSupport = true` 表示實作者不得忽略該元素的交換語意，但不會把 `0..1` 或 `0..*` 自動改成必填。是否一定要出現仍由 element cardinality、slice cardinality、invariant 與特定 Task 規則共同決定：

- `min = 1`：符合該 Profile 的 instance 必須提供該元素。
- `min = 0` 且 `mustSupport = true`：資料不存在、不適用或依法不得交換時可以省略；不得為了填值而猜測、複製不相干欄位或把未知寫成否定。
- Profile 明確允許 `dataAbsentReason` 時，依該 Profile 與術語規則表達缺值；未允許時不得任意新增替代碼。
- inherited Profile 的 Must Support 義務仍然適用；本頁只補充本 IG 的本地義務，不取消 TW Core 或其他 parent Profile 的要求。

## 資料產生者義務

宣告支援某一 Profile 的產生者，對該 Profile 中每個 Must Support element 必須：

1. 能從已核准的原始來源或明示 derivation 產生該元素；來源契約尚未完成時，必須維持 `pending`／`blocking-data-gap`，不得由報表反推為原始事實。
2. 在資料存在、適用且可合法交換時送出符合 datatype、cardinality、binding、unit、reference 與 slicing 的值。
3. 保存來源值、轉換版本與 Provenance；人工補登或 override 必須保存前值、後值、理由、操作者與時間。
4. 無法支援某個 Must Support element 時，不得宣告完整符合該 Profile；應明列不支援範圍與資料影響。

## 資料接收者義務

宣告支援某一 Profile 的接收者，對每個 Must Support element 必須：

1. 能接收並解析符合規格的值，不得僅因該元素存在而拒絕資源。
2. 能將值提供給所宣告的臨床、品管、季報或轉換流程使用，或以可稽核方式保存並轉交；不得無聲丟棄而仍宣稱完整支援。
3. 能區分元素省略、明示缺值、否定結果與非法值；不得把四者合併成同一預設值。
4. 遇到 required binding、非法 unit、無法解析的 reference 或違反 cardinality 時，必須產生可追蹤的 validation outcome，不得靜默修正原值。

接收義務不表示必須提供通用 CRUD、搜尋、訂閱或永久儲存能力；可宣告的 server／exchange 能力仍以實際 CapabilityStatement、測試與部署證據為準。

## 驗證門檻

每個宣告支援的 Must Support element 至少需要下列證據：

- 一個有效陽性案例，證明產生者可送出且接收者可解析／保存或使用。
- `min = 0` 時，一個合法省略案例，證明接收者不會把缺值誤判成否定值。
- `min = 1` 時，一個缺漏反例，必須被 Validator 或等效 conformance test 拒絕。
- 有 binding、fixed/pattern、type/profile target、unit 或 slice 時，各限制至少一個有效案例與一個針對性反例。
- 會影響 Measure 的元素，另須進入 case-level truth table，證明 population membership、numerator、denominator、exclusion 或 stratum 的預期變化。

目前 48 個本地 StructureDefinition 的 differential 共有 106 個 `mustSupport = true`。其逐元素內容由 `profile-constraint-baseline.csv` 與 CI 的 SHA-256 比對鎖定；這證明審查集合沒有漂移，不等於每個元素已完成上述 producer／consumer 測試，也不等於 48 個 artifact 已獲臨床與 FHIR reviewer 核准。

## 宣告方式

實作者的 conformance statement 必須列出：支援的 Profile canonical 與版本、扮演 producer／consumer 或兩者、未支援的 Must Support elements、已通過的測試包版本，以及已知資料缺口。不得只寫「支援本 IG」而省略 Profile、角色或例外。
