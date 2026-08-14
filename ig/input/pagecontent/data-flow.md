# 資料來源與轉換流程

{% include disclaimer.md %}

## 資料層級

| 層級 | 例子 | FHIR 表示 | 是否為事實來源 |
|---|---|---|---|
| 來源證據 | 病理報告、檢驗報告、乳房超音波報告 | DiagnosticReport、Observation、Specimen、ImagingStudy、DocumentReference | 是；以簽章報告及來源系統為準 |
| Canonical facts | 診斷、分期、marker、腫瘤大小、治療、追蹤 | BreastCancer Primary Condition、Stage、Tumor Marker、Procedure、Medication | 是；保留來源 Provenance |
| 衍生文件 | 癌症診療計畫書、治療計畫、MDT 紀錄 | Composition／document Bundle、CarePlan 等候選模型 | 否；是 canonical facts 的選取、摘要或決議 |
| Task 投影 | QBC、癌藥申請、癌登 | Task-specific Bundle、Claim、QuestionnaireResponse、XML 等 | 否；依業務規則轉換 |

報告本身是來源證據容器；報告內的檢驗值、病理判讀與影像 findings 才是可跨 Task 重用的原子事實。無法結構化時，仍可先保存 `presentedForm`／DocumentReference，再逐步抽取 Observation。

## 兩條允許的 QBC 路徑

### 過渡路徑

```text
癌症診療計畫書 → bridge mapping → canonical/QBC review model → QBC Task
```

每個值必須標記：來源文件、版本、頁面／區段、抽取方式、審核者及是否仍缺原始佐證。

### 目標路徑

```text
原始臨床證據 → source mapping → canonical facts → QBC projection
```

當原始資料可取得時，應以原始來源重新產生 canonical facts。若原始來源與癌症診療計畫書不一致，系統不得靜默覆寫，必須產生 reconciliation issue 交由人工確認。

## 直接申報與先產文件

canonical facts 可以：

1. 先產生癌症診療計畫書，再由人員確認後送 QBC；或
2. 直接產生 QBC 候選資料，同時產生供人閱讀的診療計畫書。

兩條路徑應使用同一套轉換規則、版本與 Provenance，因此結果可以比較、重算與稽核。
