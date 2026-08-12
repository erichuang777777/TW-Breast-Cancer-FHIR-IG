# v0.1.0-alpha.1

首個可執行的開發預覽版，包含批次匯入、FHIR canonical Bundle、QBC規則、Ollama結構化擷取、人工審核Web UI、核准閘門、Big5 XML與稽核輸出。

後續 conformance 更新加入115欄機器可讀規格、結構化錯誤碼、完整值域／條件規則、治療與追蹤驗證、Big5 XML round-trip、模擬收件端、三種DIAG_TYPE合成測試包、FHIR強型別Observation Profiles及mCODE 4.0.0 gap matrix。

逐版變更請見 [CHANGELOG.md](CHANGELOG.md)。Workbench 應用程式與 FHIR IG 是兩條獨立的版本線，該檔開頭有對照表。

## 驗證結果

- 單元測試：29項通過。
- 個資閘門：`scripts/check_no_phi.py` 通過，發布範圍內無病歷號或個案識別資訊。
- IG Publisher QA：0 errors、0 broken links；抑制的 warning 均在 `ig/input/ignoreWarnings.txt` 載明理由。
- 參考病例：JSON/PDF/DOCX/XLSX匯入成功，建立64個欄位狀態。
- 規則結果：cT2N0M0=StageⅡA、ypT2N2M0=StageⅢA、Non-pCR、腋下淋巴結7/13。
- 未核准AI／規則候選或缺少必填欄位時，病例核准及XML輸出均被阻擋。

## 限制

此版本是alpha，不得直接作正式臨床申報。

非官方QBC IG草案為 `draft`／`experimental`，尚未宣告mCODE相容。正式release前仍需完成：

- 115欄的臨床專家與QBC申報人員雙人簽核（目前全部為 `pending`）
- 已知歧義項目取得健保署書面確認
- 院內主檔、完整三類測試案例與資安審查
- 健保VPN測試／正式環境驗收
