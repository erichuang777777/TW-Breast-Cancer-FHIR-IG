# 下載與驗證

{% include disclaimer.md %}

QBC Task Preview 1.0 Mapping 工作簿：`outputs/qbc_ig_mapping/QBC_FHIR_Mapping_TaskSpec_v1.0-preview.1.xlsx`。其中 `Architecture` 說明乳癌共同層與 QBC Task 的關係，`Formal_Mapping_115` 是技術規格，`Approval_Register` 則保留正式／官方使用時的治理與驗收閘門。

建置後可從網站下載本 IG 的 FHIR package，或使用套件識別碼載入驗證工具。

本草案 package ID：`io.github.erichuang777777.breast-cancer#1.0.0-preview.1`。

> 對外發布前必須把範例 package ID 與 canonical URL 換成發布者實際控制的值。

## 驗證要求

驗證時應同時載入：

1. `hl7.fhir.r4.core#4.0.1`
2. `tw.gov.mohw.twcore#1.0.0`
3. 本乳癌社群草稿 package

公開 release 的 `qa.html` 必須為 0 errors、0 broken links。Warnings 必須修正，或在 release notes 中記錄其原因與影響。QBC 業務規則、Big5 XML 與 VPN 驗收屬於 package 之外的獨立驗證層。

## Dependency 與智慧財產資訊

{% include dependency-table.xhtml %}

{% include ip-statements.xhtml %}

## 版本與全域設定分析

{% include cross-version-analysis.xhtml %}

{% include globals-table.xhtml %}
