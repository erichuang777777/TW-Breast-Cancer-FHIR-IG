# 癌症登記 Task

{% include disclaimer.md %}

## Task 定位

癌症登記（Taiwan Cancer Registry，TCR）長表申報是乳癌社群草稿下**與 QBC／P4P 平級**的第二個業務 Task。兩者的臨床事實來源相同——病理報告、門診與手術紀錄、放療與化療紀錄——只是申報對象、欄位集合與代碼系統不同。

本 Task **不從 QBC 轉出**，也不提供 QBC ↔ 癌登 的欄位轉換。兩個 Task 各自從乳癌 canonical facts 投影，理由見「[來源解析與摘錄原則](tcr-source-resolution.html)」。

## 輸入與輸出

| 項目 | 定義 |
|---|---|
| Trigger | 建立、更新或重新送出某一顆原發乳癌的癌登長表 |
| Current input | 病理報告、門診／手術／放療／化療紀錄，以及既有申報值（僅供對照） |
| Target input | 由上述來源建立的乳癌 canonical facts（含出處 span 與信心度） |
| FHIR representation | `TCRRegistryAbstractionTask`、長表 99 欄 `Questionnaire`／`QuestionnaireResponse`、癌登 `CodeSystem`／`ValueSet`、`Provenance` |
| Output | 癌登長表申報列與稽核紀錄 |
| Acceptance | 每個欄位值必須落在官方編碼範圍內且寬度正確；代碼可逆（decode→encode 逐字還原） |

## 邊界

- 癌登代碼是**申報語意**，不自動等同完整臨床語意；共同層概念與癌登代碼之間以 Mapping 對齊，並保留癌登原始值。
- 代碼表本身不屬於本 IG：由 [`tcr-decoder`](https://github.com/erichuang777777/TCRD_decoding) 套件從官方碼冊產生並逐碼驗證，本 IG 只負責「乳癌要怎麼用它」。
- 本 Task 目前覆蓋長表 99 欄中的 48 欄（已驗證碼表）；其餘欄位保留在 `Questionnaire` 中並標記 `tcr-codetable-pending`，不是可自由填寫。
- 癌登專用的 CodeSystem 與 Task profile 留在 Task 層，不提升為乳癌通用術語。
- 時間脈絡（治療前／前導性治療後）**不是來源差異**，而是不同事實：癌登有 `111`／`121`／`888` 等專屬代碼表達它。

## 與 QBC Task 的關係

同一批觀察、兩套規則、兩份申報：

```
乳癌 canonical facts（抽取一次、審核一次）
        ├── QBC 規則   → D014=1, D015=70 …
        └── 癌登規則   → SSF1=S70 …
```

不做 task-to-task 轉換的實測理由：ER 有 408 個癌登合法碼，其中只有 103 個能從 QBC 欄位推得出（QBC 沒有「染色強度」欄位）。詳見「[來源解析與摘錄原則](tcr-source-resolution.html)」。

## 相關頁面

- [癌登代碼表與 conformance](tcr-code-tables.html)
- [來源解析與摘錄原則](tcr-source-resolution.html)
- [Task 目錄](task-index.html)
