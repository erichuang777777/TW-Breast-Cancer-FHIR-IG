# QBC Review Workbench v0.1.0-alpha.1

將癌症診療計畫JSON、EligibleList及外部病歷文件轉成FHIR相容中介資料，經人工審核後產生QBC XML及稽核檔。

> Alpha／研究測試用途。未完成院內驗證、資安與VPN驗收前，不得直接用於正式申報。

## 功能

- JSON、EligibleList（Big5 TSV `.xls`）、PDF、DOCX、XLSX批次匯入
- 新輔助、直接手術、首次復發適用區段
- 病理規則擷取、TNM Stage規則計算
- AI／規則／結構化／人工來源標記
- Ollama JSON Schema擷取介面
- FHIR Bundle與Provenance
- Web人工審核及核准閘門
- Big5 QBC XML、檔名規則與audit.json
- 115欄機器可讀規格、值域／條件必填／日期／跨欄位 Validator
- Big5 XML round-trip 預驗證與本機模擬收件端

## 啟動

```powershell
python -m qbc_workbench.cli serve --host 127.0.0.1 --port 8765
```

開啟 `http://127.0.0.1:8765/`。

Ollama模型由`QBC_OLLAMA_MODEL`設定；開發環境預設為`qwen3.5:cloud`。Cloud模型不得傳送未獲院方授權的可識別病歷。

## CLI匯入

```powershell
python -m qbc_workbench.cli import D:\QBC_DATA --batch demo-001 --case CASE001
```

資料保存在 `runtime/batches/`；核准後輸出至 `runtime/exports/`。

## QBC XML預驗證

```powershell
python -m qbc_workbench.cli validate-xml .\QBC_3501200000_11508_001.xml
python -m qbc_workbench.cli mock-receive .\QBC_3501200000_11508_001.xml
```

機器可讀的115欄規格位於`qbc_workbench/data/qbc_fields.json`，可編輯表格位於`outputs/qbc_conformance/`。重新擷取官方Word主表：

```powershell
python scripts\build_qbc_conformance_spec.py
```

## 安全控制

- AI候選預設`pending_review`，未核准不能輸出。
- 來源衝突、必填缺漏、治療日期缺漏均阻擋XML。
- XML不加入自訂AI標籤；來源保存在FHIR Provenance及audit.json。
- `model-cloud`可能將資料送往外部服務，未完成院內法遵前只使用去識別化資料。

## 資料隔離

真實個案、名單與健保署官方規格原檔一律隔離於 `private/`，已由 `.gitignore` 整批排除：

| 目錄 | 內容 |
|---|---|
| `private/cases/` | 單一個案來源檔（JSON／Word／PDF／Excel） |
| `private/rosters/` | 方案申請與合格個案名單 |
| `private/spec-sources/` | 健保署官方規格文件原檔（第三方著作，不再散布） |

每次打包與發布前，`scripts/check_no_phi.py` 會以 git 可提交檔案為範圍掃描病歷號、
身分證號與個案檔名；合成識別碼必須在該腳本的 `SYNTHETIC_ALLOWLIST` 明確宣告。

```powershell
python scripts\check_no_phi.py     # 單獨執行個資閘門
.\scripts\check_release.ps1        # 完整發布前檢查（閘門 + 測試 + IG QA）
python scripts\build_release.py    # 從工作樹產生發布包
```

## 已知限制

- 各院外部病歷格式需要額外adapter與測試語料。
- 若合格名單沒有對應病例，基本主檔欄位會顯示缺漏並阻擋輸出。
- 表-1官方範例含錯誤XML標籤；本工具以表-2欄位規則產生正確結束標籤。
- FHIR層的非官方QBC IG草案（`ig/`）為 `draft`／`experimental`，QBC Patient與Bundle衍生自TW Core 1.0.0。這不代表mCODE conformant。
- 本機模擬收件成功不等同健保VPN正式收件成功；`clinical_review_template.csv`的115欄簽核目前全部為`pending`，須由具權責人員完成。
- `ig/input/pagecontent/` 的 `field-audit.md` 與 `source-traceability.md` 為腳本生成，請勿手動編輯；重新產生需要 `private/spec-sources/` 內的官方原檔。
