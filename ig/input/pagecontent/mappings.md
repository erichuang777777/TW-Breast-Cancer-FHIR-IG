# QBC 對應方式

{% include disclaimer.md %}

## 現階段可逆對應

| QBC 資料 | FHIR 表示 | 備註 |
|---|---|---|
| 個案識別與生日 | `QBCPatient` | 衍生自 TW Core Patient |
| 個案資料集合 | `QBCSubmissionBundle` | 衍生自 TW Core Bundle，固定為 `collection` |
| 任一 QBC 欄位 | `QBCDataItemObservation` | 共同基礎 Profile；`code` 保存 QBC 欄位代碼 |
| 無法安全轉型的原始值 | `QBCRawDataItemObservation` | `valueString` 保存可逆原始值 |
| 全部 10 個 `YYYYMMDD` 日期欄位 | `QBCDateDataItemObservation` | 驗證後使用 `valueDateTime`，見下方覆蓋範圍 |
| 全部 21 個整數欄位 | `QBCIntegerDataItemObservation` | 驗證後使用 `valueInteger` |
| 身高、體重、腫瘤大小 | `QBCQuantityDataItemObservation` | `valueQuantity`，UCUM `system` 固定 |
| `D047` 腫瘤大小 | `QBCTumorSizeObservation` | 上者之衍生，單位碼固定為 UCUM `cm` |
| 擷取、規則、AI、人工來源 | `QBCProvenance` | target 指向實際 Patient 或 Observation |
| Big5 XML | 應用層輸出 | 不直接嵌入 Bundle，也不是本 IG 的 conformance artifact |

## 欄位代碼

本 IG 的 `QBCFieldCodeSystem` 收錄全部 115 欄：根欄位（`HOSPID`、`ID`、`BIRTHDAY`、`DIAG_TYPE`、`LATERALITY`）、`P01`–`P09`、`D001`–`D085`、`TM01`–`TM10` 及 `T01`–`T06`。欄位名稱依 115 年 7 月 QBC XML 格式說明整理；原始文件未打包進本 IG。

## 強型別覆蓋範圍

強型別 Profile 的 `code` binding 依主表宣告的資料型別劃分，未被涵蓋的欄位一律改用 `QBCRawDataItemObservation` 保存原始字串，不做不安全的自動轉型。

| 型別 | ValueSet | 涵蓋欄位 |
|---|---|---|
| `dateTime` | `QBCDateFieldValueSet` | `P09`、`D001`、`D025`、`D058`、`TM09`、`TM10`、`T01`、`T04`、`T05`、`T06` |
| `integer` | `QBCIntegerFieldValueSet` | `P06`、`TM01`，及生物標記百分比與淋巴結計數共 21 欄 |
| `Quantity` | `QBCQuantityFieldValueSet` | `P03`、`P04`、`D047` |
| `string`（原始值） | 不設限，`QBCFieldValueSet` 全域 | 其餘代碼型、複選型與自由文字欄位 |

主表的 `BIRTHDAY` 屬日期欄位，但在本 IG 以 `QBCPatient.birthDate` 表示，不另建 Observation，因此不列入 `QBCDateFieldValueSet`。

## 語意限制

`QBCDataItemObservation.valueString` 是過渡期的 lossless representation。分期、生物標記及治療資訊後續應分別建立強型別 Profiles，並在取得適當授權與專家審查後綁定 SNOMED CT、LOINC 等標準術語——目前這些欄位僅保存 QBC 原始代碼，未做語意對應。通過本 Profile 不等同完成 mCODE conformance。
