# 乳癌 FHIR 實作指引－社群草稿

這是以 HL7 FHIR R4 與 TW Core 1.0.0 為基礎的非官方社群預覽版。

- Canonical：`https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG`
- Package ID：`io.github.erichuang777777.breast-cancer`
- Version：`1.0.0-preview.1`
- Status：`draft`／`experimental`
- Domain layer：可跨 Task 重用的 `BreastCancer*` Profiles
- First task：QBC／P4P 115 欄 Mapping、規則及驗證資產

## 建置

```powershell
cd ig
npm.cmd install --prefix tools
sushi.cmd .
$env:Path=(Get-Location).Path + ";" + $env:Path
java "-Dfile.encoding=UTF-8" -jar publisher.jar -ig ig.ini
```

發布前必須通過 `scripts/check_release.ps1`。本 package 不宣告主管機關、HL7、mCODE 或 ICHOM 官方認可；mCODE 與 ICHOM 僅為語意參考。
