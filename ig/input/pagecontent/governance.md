# 人工審查與 VPN 驗收

{% include disclaimer.md %}

## 什麼需要人工審查，什麼不需要

115 欄的規則是健保署公布的法定規格。**這些規則本身不需要任何人「核准」**——依定義即為準據，本專案的工作是忠實遵循，不是評價其正確性。

因此人工審查只針對 Word 文字未明示、由本專案補上的解讀：

| 層次 | 由誰把關 | 現況 |
|---|---|---|
| 官方規則是否正確 | 不適用——法定規格即為準據 | — |
| 逐字轉錄是否忠實 | 機器 | 來源 SHA-256 鎖定版本；`test_every_word_row_is_preserved_and_conditional_rows_are_traceable` 斷言 115 列逐字保留，`test_every_enumerated_word_code_is_in_the_machine_value_set` 斷言 Word 中每個列舉代碼都在值域內 |
| 驗證器是否實作正確 | 自動化測試 | `tests/test_conformance.py` 覆蓋三種 `DIAG_TYPE`、跨欄位相依、日期順序與 Big5 round-trip |
| **本地解讀是否成立** | **人** | `clinical_review_template.csv`，見下 |

## 本地解讀簽核

`clinical_review_template.csv` 只列出本專案補上的解讀，不逐欄列出官方規則。每一列記錄 Word 的原始依據（`word_basis`）、本專案的解讀（`local_interpretation`）、受影響欄位範圍，以及應簽核的角色。

`decision` 的值：

- `pending`：待具權責人員簽核
- `resolved`：已由專案決議，`notes` 記錄決議日期與保留事項

受影響欄位由實作的 `rule_ids` 反查產生，不是手寫，因此不會與程式脫節。若某項區段規則沒有任何欄位引用，產生腳本會直接失敗。

簽核角色依項目性質區分：區段必填觸發條件由 QBC 申報負責人簽核；組織型態、分期與例外判定由病理／臨床專家簽核；FHIR 對應範圍由實作負責人簽核。`reviewer_name` 與 `decision_date` 一律留空待人工填寫，程式不得預填。

**專案決議不等同官方函釋。** 標為 `resolved` 的項目仍應列入 VPN 測試案例；取得健保署書面回覆後，應保留該公文的日期與 SHA-256，再將依據升級為官方確認。

## VPN 驗收步驟

1. 在完全合成資料上通過 pytest、IG Publisher 與 mock receiver。
2. 以院內去識別測試資料完成雙人核對及 Big5 round-trip。
3. 確認正式 HOSPID、帳號權限、上傳月份與流水號規則。
4. 於健保 VPN 測試環境上傳三種 DIAG_TYPE 的 golden cases。
5. 保存原始 XML SHA-256、上傳時間、官方 receipt／錯誤碼及修正紀錄。
6. 全部測試案例被接受後，由院內權責人核准 release。

本機 mock receiver 只模擬已公開且已機器化的檢查，不冒充官方收件端。
