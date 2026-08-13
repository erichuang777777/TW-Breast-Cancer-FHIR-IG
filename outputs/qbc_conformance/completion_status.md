# QBC Conformance 完成狀態

## 本機已完成

- 官方 11507 定版 Word 主表 115 欄擷取與來源 SHA-256
- 欄位格式、長度、Big5、值域、條件必填與相依規則
- TNM／Stage、淋巴結、治療及追蹤驗證
- 結構化 rule ID 與 API／CLI 報告
- XML declaration、Big5 bytes、well-formedness、元素順序、未知／重複元素、HOSPID／檔名及 round-trip
- 三種 DIAG_TYPE 完全合成 golden cases 與負向案例
- FHIR R4／TW Core IG、Raw／Date／Integer／Tumor Size Profiles
- mCODE 4.0.0 逐欄 gap matrix
- clinical review 與 VPN acceptance templates

## 不需要人工審查

115 欄的規則是健保署公布的法定規格，依定義即為準據，不需要任何人核准。逐字轉錄由
來源 SHA-256 鎖定版本、`tests/test_conformance.py` 斷言 115 列逐字保留與值域完整；
XML 規格的 `TRACES` 官方範例亦已納入回歸測試，原封不動通過驗證。

## 尚待外部權責人完成

- `clinical_review_template.csv` 中尚待簽核的本地解讀項目（Word 未明示、由本專案補上的判定）
- 院內個資、資安、術語授權與正式主檔核准
- 正式 canonical、package ID 與 publisher 身分
- 健保 VPN 測試／正式環境 receipt 與錯誤碼驗收

上述待辦需要真實權限或具權責人員決議，程式不能代替簽核或冒充官方收件結果。
