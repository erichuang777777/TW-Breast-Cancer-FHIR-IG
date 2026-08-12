# 非官方 QBC 資料交換實作指引

這是採用 HL7® FHIR® R4、並以 TW Core IG 1.0.0 為 dependency 的非官方研究草案。

- Canonical：`https://ericeric777777.github.io/qbc-ig`
- Package ID：`io.github.ericeric777777.qbc`
- 版本：`0.1.0`（`draft` / `experimental`）

> Canonical URL 與 package ID 一經發布即不應變更。兩者採 reverse-DNS 對應，且刻意不使用 `tw.` 或 `tw.gov.` 開頭，以免佔用主管機關的命名空間。

`publication/package-list.json` 是版本目錄，需部署到 canonical 網站根目錄
（`https://ericeric777777.github.io/qbc-ig/package-list.json`）。它刻意不放在 IG source
root，以免被 Publisher 當成尚未執行的正式 publication request。

## 建置

需要 Java 17、Node.js、Jekyll 4.4.1 與 HL7 FHIR IG Publisher。SUSHI 版本固定於 `tools/package.json`。本工作區的 `jekyll.cmd` 可使用 `tools/ruby` 中的本地 runtime；該大型 runtime 不屬於發布原始碼。

```powershell
cd ig
npm.cmd install --prefix tools
sushi.cmd .
$env:Path=(Get-Location).Path + ";" + $env:Path
java "-Dfile.encoding=UTF-8" -jar publisher.jar -ig ig.ini
```

建置完成後檢查 `output/qa.html`。正式對外提供前必須為 0 errors、0 broken links；warnings 應逐項處理，或在 `input/ignoreWarnings.txt` 寫明抑制理由。

完整發布前檢查（含個資閘門）請用專案根目錄的 `scripts/check_release.ps1`。

## 生成頁面

以下頁面由腳本產生，**請勿手動編輯**，改動請改腳本後重跑：

| 頁面 | 生成腳本 |
|---|---|
| `input/pagecontent/field-audit.md` | `scripts/build_qbc_conformance_spec.py` |
| `input/pagecontent/source-traceability.md` | `scripts/build_source_traceability.py` |

兩者都需要健保署官方原始文件。該等文件屬第三方著作，不隨本專案散布；請自行取得後放入 `private/spec-sources/`，並以頁面上的 SHA-256 核對版本。

## 發布界線

- 本 IG 不是衛生福利部、健保署或 HL7 官方出版物。
- 本 IG 不取代健保署 QBC XML、VPN 上傳規格或驗收程序。
- 本版本是 `draft`／`experimental`，不得作為未經院內驗證的臨床申報依據。
- 範例必須完全合成或去識別。真實個案、名單與病歷來源檔一律隔離於專案根目錄的 `private/`，已由 `.gitignore` 排除，並由 `scripts/check_no_phi.py` 在每次發布前掃描把關。
- `field-audit.md` 逐字引用健保署 XML 上傳格式說明，權利屬原權利機關；本 IG 的 CC BY 4.0 僅及於原創內容。

HL7、FHIR 及 FHIR flame design 是 Health Level Seven International 的註冊商標；使用這些商標不表示 HL7 認可或背書本專案。
