# RC-03 術語驗證規範

本文件定義 RC-03 的可機器重現證據。FHIR Publisher 成功、ValueSet 非空、表格簽名或單一 SHA-256 都不能單獨證明術語正確。

## 驗證範圍

發布前必須同時滿足：

1. 60 個 CodeSystem、90 個 ValueSet、2 個 ConceptMap 的結構完整且 canonical 正確。
2. 19 個 CQL 臨床 ValueSet 都有非空、具 business version 的內容及臨床核准。
3. 每個 ValueSet 都有一份與已核准內容以 SHA-256 綁定的 expansion/validate-code bundle。
4. expansion 中每一個 `(system, version, code)` tuple 都由具名術語服務回傳成功；tuple 不可重複，且必須有 display。
5. expansion 使用到的每一組 `(system, version)` 都至少有一個不存在於 expansion、且被同一服務拒絕的負向測試碼，避免把「服務永遠回傳成功」誤當驗證。
6. 兩個 ConceptMap 的 6 個實際 relationship 必須與審查清冊完全同集合；source/target release、code 解析、equivalence、審查證據與被審查 ConceptMap 的檔案 SHA-256 都必須一致。
7. 技術解析成功只證明代碼存在；臨床語意、使用情境及 equivalence 仍須由具權責的臨床／術語審查者核准。

## ValueSet 證據 bundle

`terminology-expansion-validation-register.csv` 每個 ValueSet 恰有一列。`validated` 列所指的 repository-relative JSON 檔必須具有以下資料：

```json
{
  "schema_version": "1.0",
  "valueset_url": "canonical URL",
  "valueset_version": "business version",
  "expansion_identifier": "server expansion identifier",
  "expansion_timestamp": "ISO 8601 timestamp with timezone",
  "expansion_parameters": [],
  "terminology_service": {
    "url": "service endpoint",
    "software": "service implementation",
    "version": "service/release version"
  },
  "codes": [
    {
      "system": "code-system canonical",
      "version": "code-system release",
      "code": "code",
      "display": "display returned for that release",
      "validation_result": true
    }
  ],
  "negative_tests": [
    {
      "system": "code-system canonical",
      "version": "same tested release",
      "code": "known absent test code",
      "validation_result": false
    }
  ]
}
```

稽核會重算 bundle SHA-256，並要求它同時等於 expansion register 的 hash 與臨床核准列的 `signed_artifact_sha256`。任何內容變更都會使核准失效。對本地 CodeSystem 或 compose 明列的 code，稽核還會反向計算應有 tuple，拒絕遺漏碼、版本不一致與不存在的本地碼。

## ConceptMap relationship 證據

`terminology-conceptmap-relationship-register.csv` 不以「列數相同」判定；稽核會由兩個實際 ConceptMap 重建 `(ConceptMap, source system, source code, target system, target code, equivalence)` tuple set，再要求與清冊精確相等。

每個 `approved` relationship 必須提供：

- 明確的 source 與 target system version；
- source 與 target code 均為 `resolved`；
- authoritative source version 與具權責的審查者身分、職稱、日期及決定；
- 可讀取且 SHA-256 相符的審查證據；
- 與當次實際 ConceptMap JSON 完全相符的 `reviewed_conceptmap_sha256`；
- ConceptMap group 的 `sourceVersion`、`targetVersion` 與清冊一致。

## 通過條件

RC-03 只有在以下數值同時成立時才可通過：

- empty clinical ValueSet：`0/19`
- approved clinical ValueSet：`19/19`
- validated expansion bundle：`19/19`
- versionless clinical ValueSet：`0/19`
- approved ConceptMap relationship：`6/6`
- unresolved expansion code、重複 code tuple、未核准 relationship：全部為 `0`

目前清冊保留為 `pending` 是刻意行為；在取得權威術語版本、可重現術語服務結果及人工臨床核准前，不得填成 `validated` 或 `approved`。
