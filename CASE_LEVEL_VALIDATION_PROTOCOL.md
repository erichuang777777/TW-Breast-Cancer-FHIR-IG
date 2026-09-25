# 逐案資料正確性驗證協定

## 用途與邊界

本協定是 RC-05（獨立重算）與 RC-06（原始資料端到端 golden cohort）的最低證據格式。它不允許以報表總數、抽樣列、螢幕截圖或只有 SHA-256 的摘要代替逐案比較。

真實個案資料不得提交到 Git。正式驗證應在受控環境產生與本 repository 內 [`mappings/publication/case-level-comparison-register.csv`](mappings/publication/case-level-comparison-register.csv) 相同欄位的 manifest，再用 `audit_data_correctness_evidence.py` 指向該受控檔案。Repository 只保存空白模板、規則及非敏感稽核結果。

## 個案代碼

- `case_token` 必須是 64 位十六進位 HMAC-SHA256；key 由院方受控保存，不得提交。
- token 的輸入必須是穩定的 facility namespace、case identifier 與 cohort version，不能直接對姓名、病歷號或低熵流水號做未加密 SHA-256。
- 同一個鎖定 cohort 在 VM-05、VM-06 及 truth set 使用相同 token；不同發布 cohort 應更換 key 或 namespace。
- Aggregate MeasureReport 列固定使用 `case_token=aggregate`，不得混作個案 token。

## 必須比較的精確集合

### VM-05：獨立重算

對每個 Measure 與每個 in-scope case，必須比較該 Measure 在 FSH 中宣告的每一個 `criteria.expression`。目前是 20 個 Measures、62 個 Measure-expression uses、46 個 unique CQL expressions。完整性是集合相等，不是「比較筆數大於個案數」。多一列、少一列、重複列或使用不屬於該 Measure 的 expression 都會失敗。

### VM-06：golden cohort

對每個 Measure 與每個 in-scope case，必須同時包含：

1. 該 Measure 的全部 expression 結果；
2. 該 Measure criteria 與共同 initial population 所依賴的全部 source facts，包括明確的 absent／null／invalid 狀態；
3. 適用的人工 override／adjudication facts；
4. 每個 Measure 一列完整、正規化後的 `MeasureReport` resource 比較。

`case_count` 必須等於 manifest 中該 Measure 的 unique case tokens。`case_population_comparison_count`、`source_fact_comparison_count`、`manual_override_comparison_count` 與兩種 manifest row counts 必須等於 manifest 實際值。

## 值正規化與雜湊

manifest 不保存原始臨床值，而保存正規化後的 expected／actual SHA-256。正規化程式本身必須版本化，並把執行檔或來源 artifact 的 SHA-256 填入 `comparison_normalizer_sha256`。

- `CV-1`：用於 expression、source fact 與 manual override。正規化記錄必須明確保存 state（present／absent／null／invalid）、FHIR type、值、code system/version、unit、時間精度與時區；UTF-8、Unicode NFC、排序鍵及無多餘空白的確定性 JSON 序列化後取 SHA-256。
- `FHIR-MR-1`：用於整份 MeasureReport。正規化器必須排除事先列明的 transport-only metadata，保留 measure、period、reporter、group、population、stratifier、score、subject/list reference 及所有影響報表意義的 extension；排序／排除規則必須由 `comparison_normalizer_sha256` 鎖版。

稽核器會檢查每列使用正確的 `normalization_rule_id`，但臨床 reviewer 仍須在受控環境確認 normalizer 沒有排除會改變臨床意義的欄位。

## 差異門檻

- `expected_value_sha256 == actual_value_sha256` 時，`comparison_status` 必須是 `match`。
- 不相等時必須是 `difference`；不得以備註或手動改 status 隱藏。
- 正式 approved manifest 的 `independent_difference_count` 與 `golden_difference_count` 都必須為 0。
- 發現過的差異應留在獨立 issue／adjudication log；修正程式、mapping 或 truth set 後重新產生最終 manifest。僅「已解釋但仍不一致」不能通過正式發布。

## 鎖版與簽核

每個 Measure 的 validation register 必須保存 source extract、FHIR Bundle、CQL、獨立實作、truth set、normalizer 與整份 comparison manifest 的 SHA-256，以及完整 reporting period、具名 reviewer、組織／職稱、日期與 evidence URI。任何一個 hash 或 manifest tuple set 改變，都必須重新驗證與簽核。
