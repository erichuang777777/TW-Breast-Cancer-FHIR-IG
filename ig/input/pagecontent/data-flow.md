# 資料來源與轉換流程

{% include disclaimer.md %}

## 資料層級

| 層級 | 例子 | FHIR 表示 | 是否為事實來源 |
|---|---|---|---|
| 來源證據 | 病理報告、檢驗報告、乳房超音波報告 | DiagnosticReport、Observation、Specimen、ImagingStudy、DocumentReference | 是；以簽章報告及來源系統為準 |
| Canonical facts | 診斷、分期、marker、腫瘤大小、治療、追蹤 | BreastCancer Primary Condition、Stage、Tumor Marker、Procedure、Medication | 是；保留來源 Provenance |
| 平行 Task／文件投影 | 癌症診療計畫書、QBC、治療計畫、MDT、TWPAS、癌登 | CarePlan、QuestionnaireResponse、Task-specific Bundle、Claim、XML 等 | 否；各自從 canonical facts 依業務規則產生 |

報告本身是來源證據容器；報告內的檢驗值、病理判讀與影像 findings 才是可跨 Task 重用的原子事實。無法結構化時，仍可先保存 `presentedForm`／DocumentReference，再逐步抽取 Observation。

## 唯一目標資料流

```text
原始臨床證據 → source mapping → Breast Cancer common FHIR facts + Provenance
  ├→ Cancer Care Plan Task
  ├→ QBC Task
  ├→ TWPAS Task（common facts + PAS-only fields → official Apply Bundle）
  ├→ 癌症登記 Task
  └→ 其他平行 Task
```

common FHIR facts 是 Task 間共用的唯一臨床介面。Task-specific 欄位仍留在各 Task，不得提升成共同臨床語意。

## 現階段過渡與核對

```text
同一份癌症診療計畫書 JSON secondary source
  ├→ Care Plan adapter → Care Plan check Bundle
  └→ QBC adapter       → QBC check Bundle
                  → alignment／reconciliation report only
```

這個雙輸出只用於確認兩個 Mapping 對相同欄位的解讀是否一致，不是 Care Plan → QBC，也不是 QBC → Care Plan。每個值仍須標記來源、版本、區段、抽取方式、審核者及是否缺原始佐證。

當原始資料可取得時，應由原始來源重新建立 common FHIR facts。若原始來源與過渡期 secondary source 不一致，系統不得靜默覆寫，必須產生 reconciliation issue 交由人工確認。

## Task isolation 規則

- Care Plan adapter 只能產生 Care Plan Task artifact。
- QBC adapter 只能產生 QBC Task artifact。
- TWPAS adapter 只能產生符合指定官方 TWPAS 版本的申請 artifact，不得建立替代官方 Profile。
- 三者都讀取 common FHIR facts；過渡期可讀取同一 secondary source，但必須各自留下 Provenance。
- Task-to-Task mapping 不得成為 production dependency；只可用於 migration、alignment check 與 regression test。

## TWPAS 投影邊界

TWPAS 申請同時需要 clinical facts 與 application facts。前者由 common layer 提供；後者必須由申請流程在當次案件中取得。若缺少申請品項、數量、案件類別、給付適應症或申請者等必要 Task-only 資料，adapter 必須拒絕產生正式送件 Bundle，不得從診療計畫或 QBC 猜測。
