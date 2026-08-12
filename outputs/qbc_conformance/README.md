# QBC Conformance 套件

此目錄不含真實病人資料。

- `qbc_fields.csv`：由官方 11507 定版 Word 主表擷取的 115 欄規格。
- `source_manifest.json`：來源檔名、SHA-256、欄位數及生成檔清單。
- `rule_coverage.csv`：欄位、rule ID、實作位置與自動測試對照。
- `field_rule_audit.csv`：固定 115 列的逐欄稽核表，並列 Word 原始格式／規則、適用條件、值域、驗證內容、規則 ID、技術狀態與人工審核狀態。
- `clinical_review_template.csv`：臨床與 QBC 申報雙人簽核模板；請先複製再填寫，避免重跑 generator 時覆寫。

IG 的「115 欄逐欄規則稽核」頁也由相同資料自動產生，因此網頁、CSV 與本地驗證器共享同一份欄位來源。`technical_status=implemented` 僅表示已有機器檢查；`clinical_review_status=pending` 必須由臨床與申報人員實際簽核，兩者不可混用。

重新產生：

```powershell
python scripts\build_qbc_conformance_spec.py
```

這些檔案是非官方衍生草案，不能取代健保署原始規格。

跨文件稽核另位於 `outputs/source_audit/`：

- `source_inventory.json`：5 份 PDF 與 1 份 Word 的頁數／表格數及 SHA-256。
- `source_line_traceability.csv`：每個非空白擷取文字行的來源頁碼、主題、IG 去向與覆蓋狀態。
- `coverage_summary.json`：來源數、已映射文字行數及未映射數。

名單及單一個案檔案不屬於公開規格來源，且可能包含個資，因此不會把資料列複製到 IG 或 GitHub。
