# 非官方 QBC 資料交換實作指引

{% include disclaimer.md %}

本實作指引定義一個可驗證、可版本化的 FHIR R4 中介格式，用於保存乳癌照護品質提升方案（QBC）資料、人工審核狀態及資料來源。本 IG 以 TW Core IG 1.0.0 為 dependency；QBC Patient 與 Bundle 由對應的 TW Core Profiles 衍生。

## 規格狀態

- Package ID：`io.github.ericeric777777.qbc`
- Canonical：`https://ericeric777777.github.io/qbc-ig`
- 版本：0.1.0
- 狀態：Draft／Experimental
- FHIR：R4 4.0.1
- TW Core dependency：`tw.gov.mohw.twcore#1.0.0`
- 用途：研究、實作討論、轉換驗證
- 不適用：未經院內驗收的正式申報或臨床決策

Package ID 採 canonical 的 reverse-DNS 形式，刻意不使用 `tw.` 或 `tw.gov.` 開頭，避免佔用主管機關的命名空間。

## 尚未完成的事項

本版本**不是**正式版。下列項目需要外部權責人員完成，程式無法代替：

- `clinical_review_template.csv` 中尚待簽核的本地解讀項目（見「[人工審查與 VPN 驗收](governance.html)」）
- 「[已知歧義與待確認事項](known-ambiguities.html)」中標為專案決議者，取得健保署書面確認
- 院內個資、資安與術語授權核准
- 健保 VPN 測試／正式環境的收件 receipt 與錯誤碼驗收

115 欄的規則本身**不在**上列——它們是健保署公布的法定規格，不需要任何人核准；逐字轉錄由來源 SHA-256 鎖定、實作由自動化測試驗證。需要人簽核的只有本專案補上的解讀。

在上述完成前，所有 Profile 維持 `draft`／`experimental`，且不得宣稱 mCODE conformant。

## 設計原則

1. 保留 QBC 原始欄位代碼和值，確保能追溯及重新產生申報 XML。
2. 每個資料項目可附帶 Provenance，記錄結構化匯入、規則、AI 或人工審核來源。
3. 本版不把原始代碼冒充成 SNOMED CT、LOINC、mCODE 或其他臨床語意標準。
4. 正式 QBC XML 與健保 VPN 驗收仍以主管機關當期規範為準。

搭配的 conformance 工具另提供115欄機器可讀規格、結構化 rule ID、Big5 round-trip、模擬收件端及三種 `DIAG_TYPE` 的完全合成測試包；詳見「QBC 業務規則」與「驗證方法」。

本 IG 產生的 FHIR Bundle 是交換與稽核中介層，不是健保署 VPN 的 XML 上傳檔。
