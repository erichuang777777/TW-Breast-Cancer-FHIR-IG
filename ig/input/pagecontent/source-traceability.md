# 規格來源與逐行追溯

{% include disclaimer.md %}

本專案將工作區內 5 份 QBC PDF 與 1 份 XML 格式 Word 視為規格來源。PDF 逐頁擷取、Word 逐段及逐列擷取後，每一個非空白文字行都必須對應至下列 IG 說明頁；版面頁碼等標示為非規範內容，但仍保留在追溯表中。

目前來源共 **6** 份，已映射 **1436** 個非空白文字行，未映射 **0** 行。完整逐行文字、來源 SHA-256、頁碼及 IG 去向由 `scripts/build_source_traceability.py` 在本機產生於 `outputs/source_audit/source_line_traceability.csv`；該檔含官方文件全文，屬第三方著作，不進版本控制、不隨本 IG 散布。下表的 SHA-256 可用於核對你自行取得的官方原檔是否為同一版本。

| 來源 | 映射文字行 | 來源 SHA-256 | IG 去向 |
|---|---:|---|---|
| 1 全民健康保險乳癌照護品質提升方案_方案說明.pdf | 382 | `763e182c9775835cb3a1275a011343431bbddd0832b8fdfc04951b10f4559a5e` | [field-audit.html](field-audit.html), [program-rules.html](program-rules.html), [quality-indicators.html](quality-indicators.html) |
| 2 乳癌照護品質提升方案問答集(1150629修訂).pdf | 404 | `39dbcf066dd729431ebe80116903266438ed1ff0471c7c89f7676d8ee3be9539` | [faq-rules.html](faq-rules.html), [governance.html](governance.html), [program-rules.html](program-rules.html) |
| 3 乳癌VPN系統說明會.pdf | 180 | `6e4fcd89ddda307999c5cd32e1b547e54dedc6532d83eae5536c548f6dacf1e4` | [field-audit.html](field-audit.html), [governance.html](governance.html), [program-rules.html](program-rules.html), [vpn-workflow.html](vpn-workflow.html) |
| 4 乳癌照護品質提升方案VPN使用者手冊.pdf | 122 | `888dd7f655c857e159f27a6bd34d2625aae8359341d154f73db3b5c2443f9ac1` | [vpn-workflow.html](vpn-workflow.html) |
| 5 批次上傳使用手冊_QBC_UploadXML_UserGuide.pdf | 14 | `16a6c90e88f8266867aae95e62acedb4d85192b29e40316896efc8734951b99e` | [upload-workflow.html](upload-workflow.html) |
| 6 批次上傳格式說明_QBC_乳癌照護品質提升方案_XML上傳_11507(定版).docx | 334 | `f63be9eae07c552af4f03e9771e48bcda1c5b4eb14c36ae6291c1fc0fb4e069d` | [field-audit.html](field-audit.html) |

## 其他工作區檔案

| 檔案 | 分類 | 本輪處理 |
|---|---|---|
| `private/spec-sources/` | 健保署官方規格文件原檔（PDF／Word） | 第三方著作；僅在本機擷取供逐行追溯，不進版本控制、不隨本 IG 散布 |
| `private/rosters/` | 方案申請／合格個案名單 | 含個人資料；隔離於受控目錄，排除於公開規格稽核與版本控制 |
| `private/cases/` | 單一個案來源檔（JSON／Word／PDF／Excel） | 含病歷資料；隔離於受控目錄，排除於公開規格稽核與版本控制 |
| `ig/`、`scripts/`、`tests/`、`outputs/qbc_conformance/`、`qbc_workbench/` | 本專案程式與生成物 | 以測試及 Publisher QA 驗證，不作為官方規格來源 |

本表刻意不列出任何個案檔名、病歷號或名單檔名。所有含個人資料的來源一律以目錄層級描述，實際檔名不進入本 IG、版本控制或任何發布物。

## 閱讀原則

- 最新修訂的問答集用來補充方案與欄位表未明說的臨床及作業情境。
- Word 11507 定版主表是 XML Tag、長度、值域、條件必填及編碼的主要來源。
- VPN 手冊與說明會用來描述畫面狀態、權限、轉出／接收及刪除流程，不把畫面行為誤寫成 FHIR Profile 限制。
- 文件互相矛盾或無法由資料本身證明時，列入人工審核或待 VPN 驗收，不宣稱已自動驗證。
