# 驗證方法

{% include disclaimer.md %}

## 三層驗證

1. **FHIR conformance**：SUSHI 與 HL7 IG Publisher 驗證 Profiles、ValueSets、範例、參照及網頁連結。
2. **QBC 業務規則**：工作臺依 11507 定版主表，檢查 115 欄格式、值域、條件必填、相依欄位、TNM、治療、追蹤與人工審核狀態。
3. **QBC XML 預驗證**：檢查檔名、Big5 bytes、XML well-formedness、元素名稱／順序／重複、HOSPID 與檔名一致、資料 round-trip。

以上結果不能取代健保 VPN 測試環境或正式收件結果。

## IG 建置

```powershell
cd D:\P4P\ig
.\sushi.cmd .
$env:Path = (Get-Location).Path + ";" + $env:Path
java "-Dfile.encoding=UTF-8" -jar publisher.jar -ig ig.ini
```

正式候選版本必須達到 `qa.html` 的 Errors=0 與 Broken Links=0；所有 warning 需修正或留存具體理由。

## 個案與 XML

```powershell
cd D:\P4P
python -m pytest -q
python -m qbc_workbench.cli validate-xml .\QBC_3501200000_11508_001.xml
python -m qbc_workbench.cli mock-receive .\QBC_3501200000_11508_001.xml
```

API 可使用 `GET /api/batches/{batch_id}/cases/{case_id}/validation` 取得含 `severity`、`field`、`rule`、`location` 的結構化報告。

## 能證明與不能證明

本流程能證明資源符合本草案結構、已實作的 QBC 規則及本機 XML 閘門。它不能單獨證明臨床判讀正確、術語授權完整、mCODE conformance、院內法遵通過或健保 VPN 已接受。
