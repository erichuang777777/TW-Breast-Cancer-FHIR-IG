# 乳癌 IG：癌症登記申報 Task 設計

> **目的**：把「從原始病歷產生癌症登記長表申報檔」做成乳癌 FHIR Implementation
> Guide 底下的一個 task。
>
> **產生方式**：`python -c "from tcr_workbench.ig_export import export_to_breast_ig;
> export_to_breast_ig('.', canonical='https://你的canonical/base')"`
>
> **產生器**：`tcr_workbench/ig_export.py`　**測試**：`tests/test_tcr_ig_export.py`
>
> 代碼表本身來自 [`tcr-decoder`](https://github.com/erichuang777777/TCRD_decoding)，
> 由官方碼冊逐碼驗證後提供。

---

## 一、整體架構：三層，中間那層不能給 LLM

```
病理報告 / 門診紀錄 / 手術紀錄 / 放療紀錄 / 化療紀錄 / 影像報告 / 死亡證明
        │
   ① 抽取層（LLM / NLP）
        │  輸出：臨床事實 JSON（含原文出處 span、信心度、來源文件 ID）
        │  例：{"er_percent": 70, "er_intensity": "strong",
        │       "context": "pre_treatment",
        │       "evidence": "ER: 70% positive, strong intensity",
        │       "source": "DiagnosticReport/path-2024-1234", "confidence": 0.94}
        │  ★ 這一層不可以輸出 TCR 代碼
        │
   ② 編碼層（確定性規則）  ← 本專案已完成並驗證
        │  臨床事實 → TCR 代碼，例：ER 70% strong → SSF1 = "S70"
        │  規則：coding_rules/breast_coding_spec.md
        │  程式：tcr_decoder/encoders.py、tcr_decoder.TCREncoder
        │  保證：輸出必為官方編碼範圍內、且寬度正確的合法碼
        │
   ③ 組檔與驗證層
        │  99 個欄位 → QuestionnaireResponse → 長表申報檔
        │  驗證：code_ranges 合法性、跨欄一致性、必填檢查
        │  低信心／衝突／非法碼 → 人工複核佇列
```

**為什麼第②層一定要獨立**

| 做法 | 後果 |
|---|---|
| LLM 直接輸出「SSF1=S70」 | 無法稽核：不知道它是從哪句話推出來的；也無法保證是合法碼；碼冊改版要重訓 prompt |
| LLM 只輸出「ER 70%、強染、治療前」，規則轉碼 | 每個代碼都能回推到原文；代碼永遠合法（21,158 碼已逐碼驗證）；碼冊改版只改規則表 |

FHIR 上的對應：① 的產物是 `Observation`（或直接是 QuestionnaireResponse 的
臨床事實部分），② 的產物是帶 `Coding`（system = 本 IG 的 CodeSystem）的答案，
③ 的產物是 `QuestionnaireResponse` 與申報檔。

---

## 二、Task 的形狀

`Task`（profile：`TCRRegistryAbstractionTask`）代表「為某一顆原發腫瘤完成癌登摘錄」：

| 元素 | 內容 |
|---|---|
| `Task.focus` | `Condition`（該次原發乳癌） |
| `Task.for` | `Patient` |
| `Task.input` | 來源文件：`DiagnosticReport`（病理報告）、`DocumentReference`（門診／手術／放療／化療紀錄） |
| `Task.output` | `QuestionnaireResponse`（已填的 99 欄位）＋ 產生的長表列 |
| `Task.status` | `requested` → `in-progress` → `completed`（人工複核完成才 completed） |

範例：`Task/tcr-breast-abstraction-example`、`QuestionnaireResponse/tcr-breast-example`
（範例資料全為合成資料，帶 `synthetic` tag）。

---

## 三、產生的 FHIR 資源

| 資源 | 數量 | 說明 |
|---|---|---|
| `CodeSystem` | 48 | 每個已驗證碼表一個。**display 用碼冊中文原文**，另附 `en` designation（本工具的英文臨床意義），`definition` 為中英合併——41 欄已轉錄；AJCC、附錄B 手術碼×2、淋巴結手術碼×2、EBRT、LNEXAM、LN_POSITI 共 7 欄尚未轉錄中文，暫以英文 display 呈現且不附 designation |
| `ValueSet` | 48 | 供 Questionnaire item 或 `Observation.valueCodeableConcept` 綁定 |
| 術語 mapping backlog | 2,169 列 | 每個 TCR 碼一列；target、relationship、reviewer、evidence 未完成前留白，且不發布為 FHIR `ConceptMap` |
| `Questionnaire` | 1 | 長表 99 欄位，分 8 個 group |
| `StructureDefinition` | 1 | `TCRRegistryAbstractionTask` |
| `Task` / `QuestionnaireResponse` | 2 | 範例（合成資料） |
| `ImplementationGuide` | 1 | 清單 |

**CodeSystem 概念總數 2,169**（乳癌 SSF1–10 共 1,187 碼；其餘 38 個
coded fields 共 982 碼）。

### 刻意的設計選擇

1. **未審查不等於 unmatched**。FHIR `ConceptMap.target.equivalence = unmatched`
   表示已評估且沒有對應，不是「尚未開始」；因此 2,169 個待審碼保存在
   `mappings/tcr/terminology-mapping-backlog.csv`，完成術語審查後才能產生 ConceptMap。
2. **EBRT 是加總碼**（1+2+4+8+16+32+64），所以 ValueSet 收的是「元件」，
   Questionnaire item 設 `repeats: true`，而不是列舉 128 種總和。
3. **`LNEXAM`／`LN_POSITI` 是 choice，不是 integer**。95-99 是 sentinel 碼，
   `95` 的意思是「淋巴結未移除」而不是九十五顆；設成數值欄位會讓表單填出
   語意錯誤的值。
4. **手術碼只收現行 3 碼**。附錄B 的碼表是**依部位**給定的，兩個手術欄位
   （他院／本院）共用同一張表。舊制 1-2 碼代碼仍可解碼（歷史檔案還在），
   但不進 CodeSystem——申報用的值域不該提供已淘汰的碼。

---

## 四、99 欄位的覆蓋現況

| 類別 | 欄位數 | 狀態 |
|---|---|---|
| 已有驗證碼表（SSF1–10、結構欄位、腫瘤特性五欄、治療十欄、放射治療七欄、微創手術、人口學與追蹤七欄） | 48 | ✅ 有 CodeSystem/ValueSet，Questionnaire 綁定 |
| 純數值／日期／識別碼 | 20 | ✅ 型別為 integer/date/string，不需碼表 |
| 尚未轉錄碼表 | 31 | ⚠️ Questionnaire 仍有該欄位，型別為 string 並帶 `tcr-codetable-pending` 擴充 |

**待補的 31 欄**分三群，長表碼冊都有定義：

1. **腫瘤特性**：TCODE1、MCODE（ICD-O-3，需外部字典）、MCODE6、MCODE6C
   （分級依部位，附錄D）
2. **分期**：CT/CN/CM/CSTG、PT/PN/PM/PSTG、SUMSTG、OSTG/OCSTG/OPSTG、META1–3
   （需 AJCC 8th 規則引擎，不只是碼表）
3. **治療**：S、MARG95、PREB/B（骨髓/幹細胞移植）、WATCHWAITING
4. **人口學與追蹤**：SMOKING、SEQ1、SEQ2、VSTA6、CSTA、RETYPE6、
   DIECAUSE/DIECAUSE6

補這 31 欄的工作方式與已完成的 SSF 相同：轉錄官方編碼範圍到
`code_ranges.py` → 寫 decoder/encoder → 通過 `test_codebook_conformance.py`
的四項性質 → FHIR 產生器會自動多出對應的 CodeSystem/ValueSet 並把
Questionnaire item 從 string 換成 choice。

---

## 五、抽取層要什麼（給 ① 的合約）

每個欄位的「臨床事實」schema 已在 `coding_rules/breast_coding_spec.md` 定義
（例如 SSF1 需要 `er_percent`、`er_staining_intensity`、`er_qualitative`、`context`）。
建議抽取層的輸出一律含：

```json
{
  "field": "SSF1",
  "facts": {"er_percent": 70, "er_intensity": "strong", "context": "pre_treatment"},
  "evidence": [{"document": "DiagnosticReport/path-2024-1234",
                "span": [1420, 1468],
                "text": "ER: 70% of tumor cells, strong intensity"}],
  "confidence": 0.94
}
```

有了 `evidence` 才能做人工複核；有了 `confidence` 才能設閾值決定哪些直接進檔、
哪些排進複核佇列。

`Questionnaire` 的每個 item 都帶兩個擴充，讓抽取層知道去哪裡找：

- `tcr-source-hint`：在 FHIR 原生 EMR 裡的來源路徑（例如 `Observation (ER)`）
- `tcr-source-document`：紙本／文字來源類型（例如 `病理報告`）

---

## 六、整合進 TW-Breast-Cancer-FHIR-IG

`--ig-layout` 直接產生 SUSHI + HL7 IG Publisher 的 repo 版面：

```
sushi-config.yaml          # canonical、pages、menu
ig.ini
input/fsh/                 # 手寫的 conformance（可編輯，重跑不會被蓋掉）
  extensions.fsh           #   4 個癌登擴充
  task-registry-abstraction.fsh   # Task profile
input/resources/           # 產生的資源（勿手改，碼冊改版就重跑）
  CodeSystem-*.json / ValueSet-*.json
  Questionnaire-tcr-breast-longform.json
  Task-… / QuestionnaireResponse-…（範例，合成資料）
input/pagecontent/
  index.md / cancer-registry-task.md / terminology.md
input/ignoreWarnings.txt
mappings/tcr/
  terminology-mapping-backlog.csv   # 非 FHIR、逐碼待審清冊
```

完整 IG 的 SUSHI 與 Publisher 結果以 repo 根目錄的發布驗收文件及 CI artifact 為準；
產生器的回歸測試會確認 48 個 TCR CodeSystem、48 個 ValueSet、2,169 個待審列，
且不會把未審查狀態輸出成 ConceptMap。

過程中 SUSHI 抓到兩個真問題，已修：

1. R4 的 `Task` **沒有 `subject` 元素**（病人掛在 `Task.for`），原本的 profile 會讓 SUSHI 報錯
2. IG Publisher **只讀 `input/resources/` 正下方的檔案**，放在 `terminology/`
   子資料夾會被靜默忽略——現在一律平放，用檔名前綴區分資源類型

重跑時 `input/fsh/` 與 `input/pagecontent/` 內既有的檔案不會被覆蓋，
只有 `input/resources/` 的產生物會更新。

## 七、使用方式

```bash
# 產生 IG repo 版面（SUSHI 可直接建置）— 整合進 TW-Breast-Cancer-FHIR-IG 用這個
python -m tcr_decoder --build-fhir <IG repo 路徑> --cancer breast --ig-layout \
    --fhir-base-url https://erichuang777777.github.io/TW-Breast-Cancer-FHIR-IG

# 只要一堆扁平的 FHIR 資源
python -m tcr_decoder --build-fhir fhir_ig_output --cancer breast \
    --fhir-base-url https://your.org/fhir/breast-ig

# 驗證碼表本身（每個碼雙向無損）
python -m tcr_decoder --build-validation validation_breast.xlsx --cancer breast

# 既有檔案的雙向檢查
python -m tcr_decoder registry.xlsx --roundtrip
```

> ⚠️ `--fhir-base-url` 預設是 `https://example.org/fhir/tcr` 佔位符。canonical URL
> 是身分宣告，發佈前一定要換成你們自己的網域。
