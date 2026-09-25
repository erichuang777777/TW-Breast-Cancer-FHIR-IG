# TCR 術語 mapping 待審清冊

`terminology-mapping-backlog.csv` 是非 FHIR 的工作清冊，2,169 個已驗證 TCR code
各一列。空白的 `target_system`、`target_code` 與 `relationship` 代表尚未審查，
不是已判定沒有對應。

只有在同一列完成下列欄位後，才可以由已核准列建立 FHIR `ConceptMap`：

- `target_system` 與 `target_version`
- `target_code`
- FHIR R4 ConceptMap relationship/equivalence
- `reviewer`
- `evidence_reference`
- `decision_date`

若審查結論確實為沒有對應，才可使用 `unmatched`。清冊由
`tcr_workbench.ig_export.write_terminology_mapping_backlog` 產生；重新產生會保留
「尚未開始」的基線，不得覆寫已有人工作業的審查結果。

這份清冊只處理 TCR code 到標準術語的對應，不能代替院內原始資料
table/column/API 到 FHIR element 的 source mapping。後者在尚未取得原始 schema
時仍維持 blocked。
