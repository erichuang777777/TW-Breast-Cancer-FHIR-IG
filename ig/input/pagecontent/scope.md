# 乳癌社群草稿範圍

{% include disclaimer.md %}

## 本版涵蓋

- 乳癌病人與原發診斷的最小共用表示。
- 分期、腫瘤標記、治療處置、用藥要求與照護期間的候選 Profile 外殼。
- 共同層與 Task 層的邊界、命名及版本治理。
- QBC／P4P 申報 Task 的 115 欄技術 Mapping 與驗證資產；clinical review 與 VPN acceptance 尚未完成。
- TWPAS 1.2.5 平行 Task 的架構、共同臨床資料 crosswalk、Task-only 欄位邊界與版本隔離策略；尚未宣告官方送件 conformance。

## 本版不涵蓋

- 完整乳癌臨床路徑或醫療決策支援。
- 完整病理、影像、放療、基因體或病人報告結果規範。
- 健保支付資格、官方申報核准或正式 VPN 收件保證。
- AJCC 受授權內容的重製。
- 未經驗證的 mCODE、ICHOM 或 TWPAS conformance 聲明；本草稿不複製或修改健保署官方 TWPAS Profiles。

本版的共同 Profiles 是可運作的 draft shell，而不是已完成臨床共識的終局模型。新增限制前應先證明該限制跨至少兩個 Task 可重用；只服務單一流程的限制應留在該 Task。

## 各 Scope 可宣稱的程度

| Scope | 目前可宣稱 | 不可宣稱 |
|---|---|---|
| FHIR R4／TW Core | FHIR R4 技術草稿可重現建置；TW Core 1.0.0 是結構基準，只有具名衍生 Profile 可依 parent 宣稱 | 全部乳癌 Profiles 都符合 TW Core |
| mCODE／ICHOM | semantic reference／gap analysis | conformance、背書或完整實作 |
| Care Plan | 223-control 可執行部分草稿 | 314 controls 已全數治理或 production-ready |
| QBC／P4P | 115/115 欄技術驗證 | clinical review、官方解釋或 VPN acceptance 完成 |
| TWPAS | 1.2.5 projection mapping design | 已產生並通過官方 package 驗證的 Apply Bundle |
| 個管品管／季報 | 20/20 Measure 合成 CQL 行為通過 | 真實資料指標正確或院內正式可用 |
| TCR | 99 欄 Questionnaire；48 欄已驗證碼表、32 欄 pending、19 欄非 coded | 99 欄完整 conformance 或正式申報接受 |

每一項的權威來源、版本、允許／禁止宣稱與缺少證據，另由 repository 的 `IG_SCOPE_CONFORMANCE_AUDIT.md` 與 `mappings/publication/ig-scope-claim-register.csv` 管理。
